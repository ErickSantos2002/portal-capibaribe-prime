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
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.erros_api import ErroApi
from app.esquemas.avisos import (
    AvisoCompleto,
    AvisoResumo,
    ContagemLeitura,
    CorrigirAviso,
    DestinoBloco,
    Leitura,
    NovoAviso,
    VersaoAviso,
)
from app.esquemas.comum import UnidadeRef
from app.modelos import Bloco, Papel, Unidade
from app.modelos.avisos import Aviso, AvisoBloco, AvisoLeitura, AvisoVersao
from app.seguranca.dependencias import Logado
from app.servicos.historico import Acao, registrar

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


# --- erros ------------------------------------------------------------------------------------


def nao_encontrado() -> ErroApi:
    return ErroApi(
        404,
        "aviso_nao_encontrado",
        "Não achamos este aviso. O link pode estar incompleto, ou ele é de outro bloco.",
    )


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


def resumir(texto: str) -> str:
    """Primeiro parágrafo numa linha só, até 200 caracteres (cortado com "…")."""
    primeiro = _PARAGRAFO.split(texto, maxsplit=1)[0]
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
    lido: bool

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
    lidos = set(
        db.scalars(
            select(AvisoLeitura.aviso_id).where(
                AvisoLeitura.aviso_id.in_(ids), AvisoLeitura.unidade_id == logado.unidade_id
            )
        )
    )
    return [_Montado(a, versoes[a.id], blocos[a.id], a.id in lidos) for a in avisos]


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
    }


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


def abrir(db: Session, logado: Logado, aviso_id: int) -> AvisoCompleto:
    """O aviso inteiro. Só lê: quem grava a leitura é `marcar_lido`."""
    aviso = _buscar(db, logado, aviso_id)
    [m] = _montar(db, logado, [aviso])
    return AvisoCompleto(
        **_resumo(m),
        texto=m.atual.texto,
        versoes_anteriores=[
            VersaoAviso(versao=v.versao, titulo=v.titulo, texto=v.texto, criada_em=v.criada_em)
            for v in m.versoes[1:]
        ],
        leitura=_contagem(db, aviso) if logado.gestao else None,
    )


def _gravar_leitura(db: Session, aviso_id: int, unidade_id: int) -> None:
    db.execute(
        insert(AvisoLeitura)
        .values(aviso_id=aviso_id, unidade_id=unidade_id)
        .on_conflict_do_nothing(index_elements=["aviso_id", "unidade_id"])
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
    logins = db.scalars(
        select(Unidade.login)
        .where(Unidade.id.in_(_unidades_do_destino(aviso)), Unidade.id.not_in(leram))
        .order_by(Unidade.login)
    )
    return Leitura(
        lidos=contagem.lidos,
        total=contagem.total,
        nao_leram=[UnidadeRef.de_login(login) for login in logins],
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


def publicar(db: Session, logado: Logado, dados: NovoAviso) -> int:
    """Publica (H-12) e devolve o id. Quem publica já conta como quem leu."""
    blocos = [] if dados.para_todos else _ids_dos_blocos(db, dados.blocos)
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
        )
    )
    db.add_all(AvisoBloco(aviso_id=aviso.id, bloco_id=b) for b in blocos)
    db.flush()
    _gravar_leitura(db, aviso.id, logado.unidade_id)
    registrar(
        db,
        Acao.aviso_publicado,
        unidade_id=logado.unidade_id,
        entidade="aviso",
        entidade_id=aviso.id,
        detalhes={
            "titulo": dados.titulo,
            "para_todos": dados.para_todos,
            "blocos": [] if dados.para_todos else dados.blocos,
            "fixado": dados.fixado,
        },
    )
    db.commit()
    return aviso.id


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
    if (atual.titulo, atual.texto) == (dados.titulo, dados.texto):
        raise ErroApi(409, "sem_mudanca", "Nada mudou no aviso.")
    versao = atual.versao + 1
    db.add(
        AvisoVersao(
            aviso_id=aviso.id,
            versao=versao,
            titulo=dados.titulo,
            texto=dados.texto,
            criada_por=logado.unidade_id,
        )
    )
    try:
        db.flush()
    except IntegrityError as erro:
        db.rollback()
        if _restricao(erro) in ("aviso_versao_pkey", "aviso_versao_sequencia"):
            raise ErroApi(
                409,
                "aviso_corrigido_agora",
                "Outra pessoa corrigiu este aviso agora há pouco. Abra de novo e confira.",
            ) from erro
        raise
    registrar(
        db,
        Acao.aviso_corrigido,
        unidade_id=logado.unidade_id,
        entidade="aviso",
        entidade_id=aviso.id,
        detalhes={"versao": versao, "titulo": dados.titulo},
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
