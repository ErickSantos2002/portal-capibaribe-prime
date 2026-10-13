"""Regras dos avisos (épico C: H-12, H-14, H-15, H-16). Pertence ao épico C.

Spec: `docs/superpowers/specs/m1-avisos.md`. As rotas (`app/rotas/avisos.py`) só traduzem HTTP;
o que é regra mora aqui. O banco garante o resto (migração 0002): datas carimbadas, versões em
sequência, aviso completo no commit, nada apagado.

Visibilidade: a unidade comum vê os avisos para todos e os do bloco dela; fora disso, 404 igual
a aviso inexistente (não revela que existe). A gestão vê todos.
"""

import re
import unicodedata
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

import psycopg
from sqlalchemy import ColumnElement, exists, func, select, true
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.erros_api import ErroApi
from app.esquemas.arquivos import ArquivoEnviado, LinkDoArquivo
from app.esquemas.avisos import (
    AvisoCompleto,
    AvisoResumo,
    Categoria,
    ContagemLeitura,
    CorrigirAviso,
    DestinoBloco,
    DocumentoDoAviso,
    Evento,
    Leitura,
    NovoAviso,
    VersaoAviso,
)
from app.esquemas.comum import UnidadeRef
from app.modelos import Arquivo, Bloco, Documento, DocumentoVersao, Papel, Unidade
from app.modelos.avisos import (
    ANEXOS_POR_VERSAO,
    Aviso,
    AvisoAnexo,
    AvisoBloco,
    AvisoLeitura,
    AvisoVersao,
)
from app.seguranca.dependencias import Logado
from app.servicos import notificacoes
from app.servicos.armazenamento import Armazenamento
from app.servicos.arquivos import arquivo_utilizavel, como_enviado, link_do_arquivo
from app.servicos.historico import Acao, registrar
from app.servicos.visibilidade import niveis_que_ve

# Com que papel o aviso é assinado, quando a unidade tem mais de um (contrato, seção 4.4).
ORDEM_DA_ASSINATURA = (Papel.comissao, Papel.admin, Papel.sindico, Papel.conselho)
ASSINATURAS = {
    Papel.comissao: "Comissão",
    Papel.admin: "Administração do Portal",
    Papel.sindico: "Síndico",
    Papel.conselho: "Conselho",
}
LIMITE_RESUMO = 200
# Parágrafo = linha em branco (pode ter espaços), como na tela.
_PARAGRAFO = re.compile(r"\n[ \t]*\n")
# Marcas do Markdown restrito no começo da linha (spec dos avisos com formatação, seção 3.1),
# iguais às do renderizador da tela (`web/src/avisos/formatacao.ts`).
_MARCA_DA_LINHA = re.compile(r"^(?:## |- |[0-9]{1,3}\. |> )(?=\S)", re.M)
# O resumo tem 200 caracteres: tirar as marcas de mais que isto só gasta CPU (a regex do negrito
# é quadrática com muitos `**` abertos; revisão de código, achado 3).
_LIMITE_ANTES_DO_RESUMO = 2_000
# Negrito: `**trecho**`, sem espaço colado por dentro das marcas.
_NEGRITO = re.compile(r"\*\*(\S(?:.*?\S)??)\*\*")


# --- erros ------------------------------------------------------------------------------------


def nao_encontrado() -> ErroApi:
    return ErroApi(
        404,
        "aviso_nao_encontrado",
        "Não achamos este aviso. O link pode estar incompleto, ou ele é de outro bloco.",
    )


def _anexo_recusado(mensagem: str) -> ErroApi:
    """422 no campo `anexos`, no formato da validação (o front mostra embaixo do campo)."""
    return ErroApi(
        422, "dados_invalidos", mensagem, campos=[{"campo": "anexos", "mensagem": mensagem}]
    )


ENVIE_DE_NOVO = "Envie o arquivo de novo."


def _bloco_inexistente(numero: int) -> ErroApi:
    mensagem = f"O Bloco {numero} não existe."
    return ErroApi(
        422, "bloco_inexistente", mensagem, campos=[{"campo": "blocos", "mensagem": mensagem}]
    )


# --- texto ------------------------------------------------------------------------------------


def sem_acento(texto: str) -> str:
    """Tira acentos e maiúsculas, para a busca: "Fundação" → "fundacao"."""
    decomposto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in decomposto if unicodedata.category(c) != "Mn").casefold()


def sem_marcas(texto: str) -> str:
    """O texto sem as marcas de formatação: o resumo do mural nunca mostra asterisco."""
    return _NEGRITO.sub(r"\1", _MARCA_DA_LINHA.sub("", texto))


def resumir(texto: str) -> str:
    """Primeiro parágrafo, sem marcas, numa linha só, até 200 caracteres (cortado com "…")."""
    primeiro = _PARAGRAFO.split(texto, maxsplit=1)[0][:_LIMITE_ANTES_DO_RESUMO]
    primeiro = sem_marcas(primeiro)
    linha = " ".join(primeiro.split())
    if len(linha) <= LIMITE_RESUMO:
        return linha
    return linha[: LIMITE_RESUMO - 1].rstrip() + "…"


def _combina(busca: str, versao: AvisoVersao) -> bool:
    """Cada palavra da busca aparece no título ou no texto, em qualquer ordem."""
    alvo = sem_acento(f"{versao.titulo}\n{versao.texto}")
    return all(palavra in alvo for palavra in sem_acento(busca).split())


# --- consultas --------------------------------------------------------------------------------


def _visivel(logado: Logado) -> ColumnElement[bool]:
    if logado.gestao:
        return true()
    do_bloco = exists(
        select(AvisoBloco.aviso_id)
        .join(Bloco, Bloco.id == AvisoBloco.bloco_id)
        .where(AvisoBloco.aviso_id == Aviso.id, Bloco.numero == logado.bloco)
    )
    return Aviso.para_todos | do_bloco


def _unidades_do_destino(aviso: Aviso):
    """Ids das unidades ativas que o aviso alcança (o "Y" de "Lido por X de Y")."""
    consulta = select(Unidade.id).where(Unidade.ativa)
    if not aviso.para_todos:
        consulta = consulta.where(
            Unidade.bloco_id.in_(select(AvisoBloco.bloco_id).where(AvisoBloco.aviso_id == aviso.id))
        )
    return consulta


def _ids_dos_blocos(db: Session, numeros: Sequence[int]) -> list[int]:
    """Ids dos blocos ativos pedidos; bloco desconhecido ou inativo: 422 `bloco_inexistente`."""
    ativos = dict(
        db.execute(
            select(Bloco.numero, Bloco.id).where(Bloco.ativo, Bloco.numero.in_(numeros))
        ).all()
    )
    for numero in numeros:
        if numero not in ativos:
            raise _bloco_inexistente(numero)
    return [ativos[n] for n in numeros]


@dataclass
class _Montado:
    aviso: Aviso
    # Da mais nova (em vigor) para a mais antiga.
    versoes: list[AvisoVersao]
    blocos: list[int]
    # Maior versão que a unidade abriu (None: nunca abriu).
    versao_lida: int | None
    # Quantos anexos cada versão tem (versão → quantidade; sem anexo, ausente).
    anexos_por_versao: dict[int, int]

    @property
    def lido(self) -> bool:
        return self.versao_lida is not None

    @property
    def corrigido_desde_a_leitura(self) -> bool:
        return self.versao_lida is not None and self.versao_lida < self.atual.versao

    @property
    def atual(self) -> AvisoVersao:
        return self.versoes[0]


def _montar(db: Session, logado: Logado, avisos: Sequence[Aviso]) -> list[_Montado]:
    """Junta versões, blocos e a leitura da unidade logada (3 consultas para a lista inteira)."""
    ids = [a.id for a in avisos]
    versoes: dict[int, list[AvisoVersao]] = defaultdict(list)
    for versao in db.scalars(
        select(AvisoVersao)
        .where(AvisoVersao.aviso_id.in_(ids))
        .order_by(AvisoVersao.aviso_id, AvisoVersao.versao.desc())
    ):
        versoes[versao.aviso_id].append(versao)
    blocos: dict[int, list[int]] = defaultdict(list)
    for aviso_id, numero in db.execute(
        select(AvisoBloco.aviso_id, Bloco.numero)
        .join(Bloco, Bloco.id == AvisoBloco.bloco_id)
        .where(AvisoBloco.aviso_id.in_(ids))
        .order_by(Bloco.numero)
    ):
        blocos[aviso_id].append(numero)
    lidas: dict[int, int] = {
        aviso_id: versao
        for aviso_id, versao in db.execute(
            select(AvisoLeitura.aviso_id, AvisoLeitura.versao_lida).where(
                AvisoLeitura.aviso_id.in_(ids), AvisoLeitura.unidade_id == logado.unidade_id
            )
        )
    }
    anexos: dict[int, dict[int, int]] = defaultdict(dict)
    for aviso_id, versao, quantidade in db.execute(
        select(AvisoAnexo.aviso_id, AvisoAnexo.versao, func.count())
        .where(AvisoAnexo.aviso_id.in_(ids))
        .group_by(AvisoAnexo.aviso_id, AvisoAnexo.versao)
    ):
        anexos[aviso_id][versao] = quantidade
    return [_Montado(a, versoes[a.id], blocos[a.id], lidas.get(a.id), anexos[a.id]) for a in avisos]


def _resumo(m: _Montado) -> dict:
    a = m.aviso
    return {
        "id": a.id,
        "titulo": m.atual.titulo,
        "resumo": resumir(m.atual.texto),
        "publicado_em": a.publicado_em,
        "publicado_por": ASSINATURAS[a.publicado_como],
        "editado_em": m.atual.criada_em if len(m.versoes) > 1 else None,
        "fixado": a.fixado,
        "para_todos": a.para_todos,
        "blocos": m.blocos,
        "arquivado_em": a.arquivado_em,
        "lido": m.lido,
        "corrigido_desde_a_leitura": m.corrigido_desde_a_leitura,
        "categoria": m.atual.categoria,
        "evento_quando": m.atual.evento_quando,
        # M3 (épico B): o clipe no mural conta os anexos da versão em vigor.
        "quantidade_anexos": m.anexos_por_versao.get(m.atual.versao, 0),
    }


def _evento(versao: AvisoVersao) -> Evento | None:
    if versao.evento_quando is None:
        return None
    return Evento(quando=versao.evento_quando, onde=versao.evento_onde)


def _buscar(db: Session, logado: Logado, aviso_id: int, *, travar: bool = False) -> Aviso:
    consulta = select(Aviso).where(Aviso.id == aviso_id, _visivel(logado))
    if travar:
        consulta = consulta.with_for_update()
    aviso = db.scalars(consulta).one_or_none()
    if aviso is None:
        raise nao_encontrado()
    return aviso


# --- leitura ----------------------------------------------------------------------------------


def listar(db: Session, logado: Logado, *, busca: str = "", arquivados: bool = False):
    """O mural (fixados primeiro, depois do mais novo) ou os arquivados (do mais novo)."""
    filtro = Aviso.arquivado_em.is_not(None) if arquivados else Aviso.arquivado_em.is_(None)
    ordem = [Aviso.publicado_em.desc(), Aviso.id.desc()]
    if not arquivados:
        ordem.insert(0, Aviso.fixado.desc())
    avisos = db.scalars(select(Aviso).where(filtro, _visivel(logado)).order_by(*ordem)).all()
    montados = _montar(db, logado, avisos)
    if busca.strip():
        montados = [m for m in montados if _combina(busca, m.atual)]
    return [AvisoResumo(**_resumo(m)) for m in montados]


def contar_nao_lidos(db: Session, logado: Logado) -> int:
    lido = exists(
        select(AvisoLeitura.aviso_id).where(
            AvisoLeitura.aviso_id == Aviso.id, AvisoLeitura.unidade_id == logado.unidade_id
        )
    )
    return (
        db.scalar(
            select(func.count())
            .select_from(Aviso)
            .where(Aviso.arquivado_em.is_(None), _visivel(logado), ~lido)
        )
        or 0
    )


def _contagem(db: Session, aviso: Aviso) -> ContagemLeitura:
    destino = _unidades_do_destino(aviso).subquery()
    total = db.scalar(select(func.count()).select_from(destino)) or 0
    lidos = (
        db.scalar(
            select(func.count())
            .select_from(AvisoLeitura)
            .where(AvisoLeitura.aviso_id == aviso.id, AvisoLeitura.unidade_id.in_(select(destino)))
        )
        or 0
    )
    return ContagemLeitura(lidos=lidos, total=total)


def _anexos_por_versao(db: Session, aviso_id: int) -> dict[int, list[ArquivoEnviado]]:
    """Os anexos de cada versão do aviso, na ordem (uma consulta)."""
    anexos: dict[int, list[ArquivoEnviado]] = defaultdict(list)
    for versao, arquivo in db.execute(
        select(AvisoAnexo.versao, Arquivo)
        .join(Arquivo, Arquivo.id == AvisoAnexo.arquivo_id)
        .where(AvisoAnexo.aviso_id == aviso_id)
        .order_by(AvisoAnexo.versao, AvisoAnexo.ordem)
    ):
        anexos[versao].append(como_enviado(arquivo))
    return anexos


def abrir(db: Session, logado: Logado, aviso_id: int) -> AvisoCompleto:
    """O aviso inteiro. Só lê: quem grava a leitura é `marcar_lido`."""
    aviso = _buscar(db, logado, aviso_id)
    [m] = _montar(db, logado, [aviso])
    anexos = _anexos_por_versao(db, aviso.id)
    return AvisoCompleto(
        **_resumo(m),
        texto=m.atual.texto,
        evento=_evento(m.atual),
        versoes_anteriores=[
            VersaoAviso(
                versao=v.versao,
                titulo=v.titulo,
                texto=v.texto,
                criada_em=v.criada_em,
                categoria=Categoria(v.categoria),
                evento=_evento(v),
                # M3 (épico B): o "ver como era antes" mostra os anexos daquela versão.
                anexos=anexos[v.versao],
            )
            for v in m.versoes[1:]
        ],
        leitura=_contagem(db, aviso) if logado.gestao else None,
        anexos=anexos[m.atual.versao],
        documento=_documento_do_aviso(db, logado, aviso.id),
    )


def link_do_anexo(
    db: Session,
    logado: Logado,
    aviso_id: int,
    arquivo_id: int,
    armazenamento: Armazenamento | None,
    *,
    baixar: bool,
) -> LinkDoArquivo:
    """O link de um anexo de **qualquer** versão do aviso (o "ver como era antes" também abre).
    Aviso que a unidade não vê, ou arquivo que não é anexo dele: 404 igual a aviso inexistente,
    conferido antes do 503 (sem bucket), para não revelar nada a quem não vê."""
    aviso = _buscar(db, logado, aviso_id)
    arquivo = db.scalars(
        select(Arquivo).where(
            Arquivo.id == arquivo_id,
            exists().where(AvisoAnexo.aviso_id == aviso.id, AvisoAnexo.arquivo_id == Arquivo.id),
        )
    ).one_or_none()
    if arquivo is None:
        raise nao_encontrado()
    return link_do_arquivo(armazenamento, arquivo, baixar=baixar)


def _documento_do_aviso(db: Session, logado: Logado, aviso_id: int) -> DocumentoDoAviso | None:
    """O documento que gerou este aviso (RF-33; spec do M3, seção 5.3), se a unidade pode vê-lo
    e ele não está arquivado. Senão o aviso aparece sem o botão."""
    linha = db.execute(
        select(Documento.id, Documento.titulo).where(
            Documento.aviso_id == aviso_id,
            Documento.arquivado_em.is_(None),
            Documento.acesso.in_(niveis_que_ve(logado)),
        )
    ).one_or_none()
    return None if linha is None else DocumentoDoAviso(id=linha.id, titulo=linha.titulo)


def _gravar_leitura(db: Session, aviso_id: int, unidade_id: int) -> None:
    """Primeira leitura: grava (o banco carimba `lido_em` e a versão atual). Leituras seguintes
    só sobem `versao_lida` para a atual (U1); `lido_em` continua o da primeira (trigger)."""
    atual = (
        select(func.max(AvisoVersao.versao))
        .where(AvisoVersao.aviso_id == aviso_id)
        .scalar_subquery()
    )
    comando = insert(AvisoLeitura).values(
        aviso_id=aviso_id, unidade_id=unidade_id, versao_lida=atual
    )
    db.execute(
        comando.on_conflict_do_update(
            index_elements=["aviso_id", "unidade_id"],
            set_={"versao_lida": comando.excluded.versao_lida},
        )
    )


def marcar_lido(db: Session, logado: Logado, aviso_id: int) -> None:
    """A unidade abriu o aviso (H-16). Só a primeira vez conta."""
    _buscar(db, logado, aviso_id)
    _gravar_leitura(db, aviso_id, logado.unidade_id)
    db.commit()


def leitura(db: Session, logado: Logado, aviso_id: int) -> Leitura:
    aviso = _buscar(db, logado, aviso_id)
    contagem = _contagem(db, aviso)
    leram = select(AvisoLeitura.unidade_id).where(AvisoLeitura.aviso_id == aviso.id)
    linhas = db.execute(
        select(Unidade.login, Unidade.ativada_em.is_not(None))
        .where(Unidade.id.in_(_unidades_do_destino(aviso)), Unidade.id.not_in(leram))
        .order_by(Unidade.login)
    ).all()
    return Leitura(
        lidos=contagem.lidos,
        total=contagem.total,
        nao_entraram=[UnidadeRef.de_login(login) for login, entrou in linhas if not entrou],
        entraram_sem_ler=[UnidadeRef.de_login(login) for login, entrou in linhas if entrou],
    )


def alcance(db: Session, numeros: Sequence[int]) -> int:
    """Quantas unidades ativas um aviso para esses blocos alcança (sem blocos: todos)."""
    consulta = select(func.count()).select_from(Unidade).where(Unidade.ativa)
    if numeros:
        consulta = consulta.where(Unidade.bloco_id.in_(_ids_dos_blocos(db, numeros)))
    return db.scalar(consulta) or 0


def destinos(db: Session) -> list[DestinoBloco]:
    blocos = db.execute(select(Bloco.numero, Bloco.nome).where(Bloco.ativo).order_by(Bloco.numero))
    return [DestinoBloco(numero=numero, nome=nome) for numero, nome in blocos]


# --- gestão -----------------------------------------------------------------------------------


def _categoria_e_evento(dados: CorrigirAviso) -> dict:
    """As colunas da 0004 a partir do corpo da requisição."""
    return {
        "categoria": dados.categoria.value,
        "evento_quando": dados.evento.quando if dados.evento else None,
        "evento_onde": dados.evento.onde if dados.evento else None,
    }


def publicar(db: Session, logado: Logado, dados: NovoAviso) -> int:
    """Publica (H-12) e devolve o id. Quem publica já conta como quem leu."""
    aviso_id = gravar_publicacao(db, logado, dados)
    db.commit()
    return aviso_id


def gravar_publicacao(db: Session, logado: Logado, dados: NovoAviso) -> int:
    """Tudo do `publicar`, menos o commit: quem chama fecha a transação. O épico A do M3 usa
    para o aviso automático nascer junto com o documento (RF-33), ou nenhum dos dois. Quem chama
    agenda as notificações depois do commit (`notificacoes.agendar`)."""
    blocos = [] if dados.para_todos else _ids_dos_blocos(db, dados.blocos)
    anexos = _anexos_conferidos(db, logado, dados.anexos or [])
    assinatura = next(p for p in ORDEM_DA_ASSINATURA if p in logado.papeis)
    aviso = Aviso(
        publicado_por=logado.unidade_id,
        publicado_como=assinatura,
        para_todos=dados.para_todos,
        fixado=dados.fixado,
    )
    db.add(aviso)
    db.flush()
    db.add(
        AvisoVersao(
            aviso_id=aviso.id,
            versao=1,
            titulo=dados.titulo,
            texto=dados.texto,
            criada_por=logado.unidade_id,
            **_categoria_e_evento(dados),
        )
    )
    db.add_all(AvisoBloco(aviso_id=aviso.id, bloco_id=b) for b in blocos)
    db.flush()
    _gravar_anexos(db, aviso.id, 1, anexos)
    _gravar_leitura(db, aviso.id, logado.unidade_id)
    detalhes: dict = {
        "titulo": dados.titulo,
        "para_todos": dados.para_todos,
        "blocos": [] if dados.para_todos else dados.blocos,
        "fixado": dados.fixado,
    }
    # Só quando há anexo: o aviso sem anexo registra o mesmo que antes (dúvida 1 do épico B).
    if anexos:
        detalhes["anexos"] = len(anexos)
    registrar(
        db,
        Acao.aviso_publicado,
        unidade_id=logado.unidade_id,
        entidade="aviso",
        entidade_id=aviso.id,
        detalhes=detalhes,
    )
    # H-13 (M2): o pedido de notificar entra na mesma transação; a rota agenda o envio.
    notificacoes.registrar_publicacao(db, aviso.id)
    db.flush()
    return aviso.id


def _em_uso_fora_do_aviso(db: Session, arquivo_id: int, aviso_id: int | None) -> bool:
    """O arquivo já está num documento ou em outro aviso (a regra `arquivo_em_uso` do banco,
    conferida antes para responder com a frase certa)."""
    em_outro_aviso = select(AvisoAnexo.arquivo_id).where(AvisoAnexo.arquivo_id == arquivo_id)
    if aviso_id is not None:
        em_outro_aviso = em_outro_aviso.where(AvisoAnexo.aviso_id != aviso_id)
    em_documento = select(DocumentoVersao.arquivo_id).where(
        DocumentoVersao.arquivo_id == arquivo_id
    )
    return bool(db.scalar(select(exists(em_outro_aviso) | exists(em_documento))))


def _ja_anexo_do_aviso(db: Session, arquivo_id: int, aviso_id: int | None) -> bool:
    if aviso_id is None:
        return False
    return bool(
        db.scalar(
            select(
                exists().where(AvisoAnexo.aviso_id == aviso_id, AvisoAnexo.arquivo_id == arquivo_id)
            )
        )
    )


def _anexos_conferidos(
    db: Session, logado: Logado, ids: Sequence[int], aviso_id: int | None = None
) -> list[int]:
    """Os anexos pedidos, na ordem, depois das regras do épico B (spec `m3-anexos.md`, 2.1):
    até 5, sem repetir; cada um enviado por esta unidade (confirmado, para aviso, sem uso fora
    deste aviso) **ou**, na correção, já anexo de uma versão deste aviso (a correção feita por
    outro membro da gestão repete os anexos). Qualquer outro caso: "Envie o arquivo de novo.",
    sem dizer se o arquivo existe."""
    if len(ids) > ANEXOS_POR_VERSAO:
        raise _anexo_recusado("Até 5 anexos por aviso.")
    if len(set(ids)) != len(ids):
        raise _anexo_recusado("O mesmo arquivo foi escolhido duas vezes.")
    for arquivo_id in ids:
        if _ja_anexo_do_aviso(db, arquivo_id, aviso_id):
            continue
        utilizavel = arquivo_utilizavel(db, logado, arquivo_id, "aviso")
        if utilizavel is None or _em_uso_fora_do_aviso(db, arquivo_id, aviso_id):
            raise _anexo_recusado(ENVIE_DE_NOVO)
    return list(ids)


def _gravar_anexos(db: Session, aviso_id: int, versao: int, anexos: Sequence[int]) -> None:
    """Os anexos entram na mesma transação da versão (o banco recusa depois). A corrida com
    outro aviso usando o mesmo arquivo para no banco (`arquivo_em_uso`): mesma frase."""
    if not anexos:
        return
    try:
        # Trava os arquivos em ordem de id, com a mesma trava do gatilho (`for no key update`):
        # dois pedidos com os mesmos arquivos em ordem diferente esperam um pelo outro em vez de
        # travarem em cruz (deadlock; revisão do épico B, C1). O segundo vê `arquivo_em_uso`.
        db.execute(
            select(Arquivo.id)
            .where(Arquivo.id.in_(anexos))
            .order_by(Arquivo.id)
            .with_for_update(key_share=True)
        )
        db.add_all(
            AvisoAnexo(aviso_id=aviso_id, versao=versao, arquivo_id=arquivo_id, ordem=ordem)
            for ordem, arquivo_id in enumerate(anexos, start=1)
        )
        db.flush()
    except IntegrityError as erro:
        if _restricao(erro) != "arquivo_em_uso":
            raise
        db.rollback()
        raise _anexo_recusado(ENVIE_DE_NOVO) from erro
    except OperationalError as erro:
        # Deadlock que sobrar (com outra transação que trave em outra ordem): a mesma frase.
        if not isinstance(erro.orig, psycopg.errors.DeadlockDetected):
            raise
        db.rollback()
        raise _anexo_recusado(ENVIE_DE_NOVO) from erro


def _corrigido_agora() -> ErroApi:
    return ErroApi(
        409,
        "aviso_corrigido_agora",
        "Outra pessoa corrigiu este aviso agora há pouco. Abra de novo e confira.",
    )


def _recusar_arquivado(aviso: Aviso, mensagem: str) -> None:
    if aviso.arquivado_em is not None:
        raise ErroApi(409, "aviso_arquivado", mensagem)


def _restricao(erro: IntegrityError) -> str | None:
    causa = erro.orig
    return causa.diag.constraint_name if isinstance(causa, psycopg.Error) else None


def corrigir(db: Session, logado: Logado, aviso_id: int, dados: CorrigirAviso) -> None:
    """Versão nova (H-15); a anterior fica como estava.

    Sem trava de propósito: se duas pessoas corrigem ao mesmo tempo, a segunda bate na chave
    (aviso, versão) e recebe 409, em vez de sobrescrever a outra sem ver o que ela fez.
    """
    aviso = _buscar(db, logado, aviso_id)
    _recusar_arquivado(aviso, "Aviso arquivado não pode ser corrigido.")
    atual = db.scalars(
        select(AvisoVersao)
        .where(AvisoVersao.aviso_id == aviso.id)
        .order_by(AvisoVersao.versao.desc())
        .limit(1)
    ).one()
    if dados.versao_base is not None and dados.versao_base != atual.versao:
        raise _corrigido_agora()
    novas = _categoria_e_evento(dados)
    em_vigor = list(
        db.scalars(
            select(AvisoAnexo.arquivo_id)
            .where(AvisoAnexo.aviso_id == aviso.id, AvisoAnexo.versao == atual.versao)
            .order_by(AvisoAnexo.ordem)
        )
    )
    # M3 (épico B): omitido ou nulo repete os anexos da versão em vigor; `[]` tira todos.
    anexos = (
        em_vigor if dados.anexos is None else _anexos_conferidos(db, logado, dados.anexos, aviso.id)
    )
    # Omitidos, categoria e evento ficam os da versão em vigor (revisão de código, achado 2).
    if "categoria" not in dados.model_fields_set:
        novas["categoria"] = atual.categoria
    if "evento" not in dados.model_fields_set:
        novas["evento_quando"] = atual.evento_quando
        novas["evento_onde"] = atual.evento_onde
    # Datas comparadas como instante (o mesmo horário em outro fuso não é mudança).
    # Trocar só os anexos (ou só a ordem deles) também é mudança.
    if (
        atual.titulo,
        atual.texto,
        atual.categoria,
        atual.evento_quando,
        atual.evento_onde,
        em_vigor,
    ) == (
        dados.titulo,
        dados.texto,
        novas["categoria"],
        novas["evento_quando"],
        novas["evento_onde"],
        anexos,
    ):
        raise ErroApi(409, "sem_mudanca", "Nada mudou no aviso.")
    versao = atual.versao + 1
    db.add(
        AvisoVersao(
            aviso_id=aviso.id,
            versao=versao,
            titulo=dados.titulo,
            texto=dados.texto,
            criada_por=logado.unidade_id,
            **novas,
        )
    )
    try:
        db.flush()
    except IntegrityError as erro:
        db.rollback()
        restricao = _restricao(erro)
        if restricao == "aviso_versao_arquivado":
            # C4 (revisão do M1): arquivaram entre a conferência acima e a gravação; o banco
            # recusou (trigger da 0003).
            raise ErroApi(
                409, "aviso_arquivado", "Aviso arquivado não pode ser corrigido."
            ) from erro
        if restricao in ("aviso_versao_pkey", "aviso_versao_sequencia"):
            raise _corrigido_agora() from erro
        raise
    _gravar_anexos(db, aviso.id, versao, anexos)
    detalhes: dict = {"versao": versao, "titulo": dados.titulo}
    if anexos:
        detalhes["anexos"] = len(anexos)
    registrar(
        db,
        Acao.aviso_corrigido,
        unidade_id=logado.unidade_id,
        entidade="aviso",
        entidade_id=aviso.id,
        detalhes=detalhes,
    )
    db.commit()


def arquivar(db: Session, logado: Logado, aviso_id: int) -> None:
    """Tira do mural (H-15); continua em "Avisos arquivados". Desafixa junto."""
    aviso = _buscar(db, logado, aviso_id, travar=True)
    _recusar_arquivado(aviso, "Este aviso já está arquivado.")
    aviso.arquivado_em = func.now()
    aviso.fixado = False
    registrar(
        db,
        Acao.aviso_arquivado,
        unidade_id=logado.unidade_id,
        entidade="aviso",
        entidade_id=aviso.id,
    )
    db.commit()


def mudar_fixado(db: Session, logado: Logado, aviso_id: int, fixado: bool) -> None:
    aviso = _buscar(db, logado, aviso_id, travar=True)
    _recusar_arquivado(aviso, "Aviso arquivado não pode ser fixado.")
    if aviso.fixado == fixado:
        return
    aviso.fixado = fixado
    registrar(
        db,
        Acao.aviso_fixado if fixado else Acao.aviso_desafixado,
        unidade_id=logado.unidade_id,
        entidade="aviso",
        entidade_id=aviso.id,
    )
    db.commit()
