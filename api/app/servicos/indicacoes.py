"""Indicações de serviços: ler, indicar, opinar, corrigir, avisar a gestão e apagar o que é da
unidade (spec de 18/10/2026, seções 3, 4 e 6). A moderação fica em `indicacoes_gestao.py`.

As rotas (`app/rotas/indicacoes.py`) só traduzem HTTP. O banco garante o resto (migração 0010):
unidade ativa, uma opinião por unidade e prestador, telefone único, limites do dia, prestador e
opinião escondidos travados. Quando ele recusa, `indicacoes_banco.traduzir` dá o 4xx.

A busca e a normalização são em Python (nada de `unaccent` nem `pg_trgm`, que pediriam extensão
no Neon): são poucas centenas de prestadores, sem paginação, então nada é agregado depois de
paginar.
"""

import unicodedata
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Row, delete, select, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.erros_api import ErroApi
from app.esquemas.comum import UnidadeRef
from app.esquemas.indicacoes import (
    AvisarGestao,
    AvisoRecebido,
    CategoriaServico,
    CorrigirPrestador,
    DarOpiniao,
    ListaIndicacoes,
    MinhaOpiniao,
    NovaIndicacao,
    Opiniao,
    OpiniaoTrecho,
    Prestador,
    PrestadorRef,
    PrestadorResumo,
)
from app.modelos.indicacoes import AvisoServico, OpiniaoServico
from app.modelos.indicacoes import CategoriaServico as CategoriaModelo
from app.modelos.indicacoes import Prestador as PrestadorModelo
from app.seguranca.dependencias import Logado
from app.servicos import indicacoes_banco
from app.servicos.historico import Acao, registrar

MAX_PARECIDOS = 3
MIN_LETRAS_PARECIDOS = 3


# --- texto -------------------------------------------------------------------------------------


def normalizar(texto: str) -> str:
    """Sem acento, sem diferença de maiúscula e com os espaços juntos: "  JOÃO  da Silva" →
    "joao da silva". É o `prestador.nome_busca` e a base da busca."""
    decomposto = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c))
    return " ".join(sem_acento.casefold().split())


# --- erros -------------------------------------------------------------------------------------


def nao_encontrada() -> ErroApi:
    return ErroApi(*indicacoes_banco.NAO_ENCONTRADA)


def _categoria_inexistente() -> ErroApi:
    return ErroApi(*indicacoes_banco.RESTRICOES["prestador_categoria_id_fkey"])


def _sem_permissao() -> ErroApi:
    return ErroApi(
        403,
        "sem_permissao",
        "Só quem indicou este prestador, ou a gestão, pode corrigir os dados dele.",
    )


def _repassar(db: Session, erro: DBAPIError) -> ErroApi:
    """Desfaz a transação e devolve o 4xx do banco (ou levanta o erro, que vira 500)."""
    db.rollback()
    traduzido = indicacoes_banco.traduzir(erro)
    if traduzido is None:
        raise erro
    return traduzido


def erro_de_telefone(db: Session, telefone: str, *, menos: int | None = None) -> ErroApi | None:
    """O telefone já é de outro prestador? 409 com o `id` dele, ou, se ele está escondido, 409
    sem link (esconder não libera o número, e quem pediu para sair não volta)."""
    consulta = select(PrestadorModelo.id, PrestadorModelo.escondido_em).where(
        PrestadorModelo.telefone == telefone
    )
    if menos is not None:
        consulta = consulta.where(PrestadorModelo.id != menos)
    outro = db.execute(consulta).one_or_none()
    if outro is None:
        return None
    if outro.escondido_em is not None:
        return ErroApi(
            409, "prestador_indisponivel", "Esse prestador não está disponível no Portal."
        )
    status, codigo, mensagem = indicacoes_banco.RESTRICOES["prestador_telefone_unico"]
    return ErroApi(status, codigo, mensagem, id=outro.id)


# --- leitura -----------------------------------------------------------------------------------


def listar_categorias(db: Session) -> list[CategoriaServico]:
    return [
        CategoriaServico(id=c.id, nome=c.nome)
        for c in db.scalars(
            select(CategoriaModelo).order_by(CategoriaModelo.ordem, CategoriaModelo.id)
        )
    ]


# A lista numa consulta: contagens só das opiniões visíveis, a mais recente (`ultima`), os
# comentários visíveis (para a busca), os avisos abertos e, por `lateral`, a opinião visível
# mais recente com comentário (o trecho do cartão). Escondidos ficam de fora.
_LISTA = text(
    """
with visiveis as (
    select o.prestador_id,
           count(*) filter (where o.recomenda) as recomendam,
           count(*) filter (where not o.recomenda) as nao_recomendam,
           max(coalesce(o.editada_em, o.criada_em)) as ultima,
           string_agg(o.comentario, ' ') as comentarios
      from opiniao_servico o
     where o.escondida_em is null
     group by o.prestador_id
), abertos as (
    select a.prestador_id, count(*) as avisos
      from aviso_servico a
     where a.resolvido_em is null
     group by a.prestador_id
)
select p.id, p.nome, c.id as categoria_id, c.nome as categoria_nome,
       coalesce(v.recomendam, 0) as recomendam, coalesce(v.nao_recomendam, 0) as nao_recomendam,
       v.prestador_id is not null as tem_opiniao, coalesce(v.comentarios, '') as comentarios,
       coalesce(a.avisos, 0) as avisos, t.login as trecho_login,
       t.comentario as trecho_comentario, t.em as trecho_em
  from prestador p
  join categoria_servico c on c.id = p.categoria_id
  left join visiveis v on v.prestador_id = p.id
  left join abertos a on a.prestador_id = p.id
  left join lateral (
      select u.login, o.comentario, coalesce(o.editada_em, o.criada_em) as em
        from opiniao_servico o join unidade u on u.id = o.unidade_id
       where o.prestador_id = p.id and o.escondida_em is null and o.comentario is not null
       order by coalesce(o.editada_em, o.criada_em) desc, o.id desc
       limit 1
  ) t on true
 where p.escondido_em is null
 order by coalesce(v.recomendam, 0) desc, v.ultima desc nulls last, p.id desc
"""
)


def _bate(linha: Row, termo: str) -> bool:
    return termo in normalizar(f"{linha.nome} {linha.categoria_nome} {linha.comentarios}")


def listar(
    db: Session,
    logado: Logado,
    *,
    categoria: int | None,
    busca: str | None,
    com_aviso: bool,
) -> ListaIndicacoes:
    """Mais recomendados primeiro; no empate, a opinião mais recente. Sem nenhuma opinião
    visível, o prestador sai da lista comum. `com_aviso` (só a gestão) mostra os que têm aviso
    aberto, com ou sem opinião visível."""
    com_aviso = com_aviso and logado.gestao
    termo = normalizar(busca or "")
    linhas = db.execute(_LISTA).all()
    contagem = sum(1 for linha in linhas if linha.avisos > 0)
    itens = []
    for linha in linhas:
        if (com_aviso and linha.avisos == 0) or (not com_aviso and not linha.tem_opiniao):
            continue
        if categoria is not None and linha.categoria_id != categoria:
            continue
        if termo and not _bate(linha, termo):
            continue
        trecho = None
        if linha.trecho_login is not None:
            trecho = OpiniaoTrecho(
                unidade=UnidadeRef.de_login(linha.trecho_login),
                comentario=linha.trecho_comentario,
                em=linha.trecho_em,
            )
        itens.append(
            PrestadorResumo(
                id=linha.id,
                categoria=CategoriaServico(id=linha.categoria_id, nome=linha.categoria_nome),
                nome=linha.nome,
                recomendam=linha.recomendam,
                nao_recomendam=linha.nao_recomendam,
                trecho=trecho,
                avisos_abertos=linha.avisos if logado.gestao else None,
            )
        )
    return ListaIndicacoes(itens=itens, com_aviso=contagem if logado.gestao else None)


def parecidos(db: Session, nome: str) -> list[PrestadorRef]:
    """Até 3 prestadores visíveis com nome parecido, para o aviso de duplicado: o nome contém o
    que foi digitado (a partir de 3 letras) ou começa pela mesma palavra (de 3 letras ou mais).
    Mais recomendados primeiro."""
    termo = normalizar(nome)
    if len(termo) < MIN_LETRAS_PARECIDOS:
        return []
    primeira = termo.split()[0]
    linhas = db.execute(
        text(
            """
select p.id, p.nome, p.nome_busca, c.id as categoria_id, c.nome as categoria_nome,
       (select count(*) from opiniao_servico o
         where o.prestador_id = p.id and o.escondida_em is null and o.recomenda) as recomendam
  from prestador p join categoria_servico c on c.id = p.categoria_id
 where p.escondido_em is null
 order by recomendam desc, p.id
"""
        )
    ).all()
    achados = []
    for linha in linhas:
        palavras = linha.nome_busca.split()
        mesma_primeira = len(primeira) >= MIN_LETRAS_PARECIDOS and palavras[:1] == [primeira]
        if termo in linha.nome_busca or mesma_primeira:
            achados.append(
                PrestadorRef(
                    id=linha.id,
                    nome=linha.nome,
                    categoria=CategoriaServico(id=linha.categoria_id, nome=linha.categoria_nome),
                )
            )
        if len(achados) == MAX_PARECIDOS:
            break
    return achados


def _buscar(db: Session, logado: Logado, prestador_id: int, *, travar: bool = False):
    """O prestador, ou 404. Escondido: 404 para o morador (a gestão ainda o vê)."""
    consulta = select(PrestadorModelo).where(PrestadorModelo.id == prestador_id)
    if travar:
        consulta = consulta.with_for_update(key_share=True)
    prestador = db.scalars(consulta).one_or_none()
    if prestador is None or (prestador.escondido_em is not None and not logado.gestao):
        raise nao_encontrada()
    return prestador


@dataclass(frozen=True)
class _LinhaOpiniao:
    id: int
    login: str
    unidade_id: int
    recomenda: bool
    comentario: str | None
    em: datetime
    escondida: bool


def _opinioes(db: Session, prestador_id: int) -> list[_LinhaOpiniao]:
    linhas = db.execute(
        text(
            """
select o.id, u.login, o.unidade_id, o.recomenda, o.comentario,
       coalesce(o.editada_em, o.criada_em) as em, o.escondida_em is not null as escondida
  from opiniao_servico o join unidade u on u.id = o.unidade_id
 where o.prestador_id = :p
 order by coalesce(o.editada_em, o.criada_em) desc, o.id desc
"""
        ),
        {"p": prestador_id},
    ).all()
    return [_LinhaOpiniao(**linha._mapping) for linha in linhas]


def abrir(db: Session, logado: Logado, prestador_id: int) -> Prestador:
    """O prestador com as opiniões visíveis (da mais recente para a mais antiga) e a da unidade
    logada. A opinião escondida não aparece para ninguém, menos para a própria unidade (em
    `minha_opiniao`, com o recado). Os avisos abertos, só para a gestão."""
    prestador = _buscar(db, logado, prestador_id)
    categoria = db.get_one(CategoriaModelo, prestador.categoria_id)
    todas = _opinioes(db, prestador.id)
    visiveis = [o for o in todas if not o.escondida]
    minha = next((o for o in todas if o.unidade_id == logado.unidade_id), None)
    ja_avisei = (
        db.scalar(
            select(AvisoServico.id).where(
                AvisoServico.prestador_id == prestador.id,
                AvisoServico.unidade_id == logado.unidade_id,
                AvisoServico.resolvido_em.is_(None),
            )
        )
        is not None
    )
    avisos = None
    if logado.gestao:
        avisos = [
            AvisoRecebido(id=a.id, motivo=a.motivo, em=a.criado_em)
            for a in db.scalars(
                select(AvisoServico)
                .where(
                    AvisoServico.prestador_id == prestador.id,
                    AvisoServico.resolvido_em.is_(None),
                )
                .order_by(AvisoServico.criado_em.desc(), AvisoServico.id.desc())
            )
        ]
    return Prestador(
        id=prestador.id,
        categoria=CategoriaServico(id=categoria.id, nome=categoria.nome),
        nome=prestador.nome,
        telefone=prestador.telefone,
        celular=len(prestador.telefone) == 11,
        instagram=prestador.instagram,
        recomendam=sum(1 for o in visiveis if o.recomenda),
        nao_recomendam=sum(1 for o in visiveis if not o.recomenda),
        opinioes=[
            Opiniao(
                id=o.id,
                unidade=UnidadeRef.de_login(o.login),
                recomenda=o.recomenda,
                comentario=o.comentario,
                em=o.em,
                minha=o.unidade_id == logado.unidade_id,
            )
            for o in visiveis
        ],
        minha_opiniao=None
        if minha is None
        else MinhaOpiniao(
            recomenda=minha.recomenda, comentario=minha.comentario, escondida=minha.escondida
        ),
        pode_corrigir=logado.gestao or prestador.criado_por == logado.unidade_id,
        ja_avisei=ja_avisei,
        escondido=prestador.escondido_em is not None,
        avisos=avisos,
    )


# --- indicar -----------------------------------------------------------------------------------


def _conferir_categoria(db: Session, categoria_id: int) -> None:
    if db.get(CategoriaModelo, categoria_id) is None:
        raise _categoria_inexistente()


def criar(db: Session, logado: Logado, dados: NovaIndicacao) -> int:
    """O prestador e a primeira opinião, numa transação. Telefone repetido: 409 com o id do
    outro (ou sem, se ele está escondido), também na corrida entre duas indicações."""
    _conferir_categoria(db, dados.categoria_id)
    erro = erro_de_telefone(db, dados.telefone)
    if erro is not None:
        raise erro
    try:
        prestador = PrestadorModelo(
            categoria_id=dados.categoria_id,
            nome=dados.nome,
            nome_busca=normalizar(dados.nome),
            telefone=dados.telefone,
            instagram=dados.instagram,
            criado_por=logado.unidade_id,
        )
        db.add(prestador)
        db.flush()
        db.add(
            OpiniaoServico(
                prestador_id=prestador.id,
                unidade_id=logado.unidade_id,
                recomenda=dados.recomenda,
                comentario=dados.comentario,
            )
        )
        db.flush()
        prestador_id = prestador.id
        db.commit()
    except IntegrityError as falha:
        if indicacoes_banco.restricao(falha) == "prestador_telefone_unico":
            db.rollback()
            raise erro_de_telefone(db, dados.telefone) or _repassar(db, falha) from falha
        raise _repassar(db, falha) from falha
    except DBAPIError as falha:
        raise _repassar(db, falha) from falha
    return prestador_id


# --- a minha opinião ---------------------------------------------------------------------------


def _gravar_opiniao(db: Session, logado: Logado, prestador_id: int, dados: DarOpiniao) -> None:
    """`select … for update` e depois `UPDATE` ou `INSERT`, nunca `insert … on conflict`: o
    `BEFORE INSERT` contaria a mudança no limite do dia."""
    atual = db.scalars(
        select(OpiniaoServico)
        .where(
            OpiniaoServico.prestador_id == prestador_id,
            OpiniaoServico.unidade_id == logado.unidade_id,
        )
        .with_for_update()
    ).one_or_none()
    if atual is None:
        db.add(
            OpiniaoServico(
                prestador_id=prestador_id,
                unidade_id=logado.unidade_id,
                recomenda=dados.recomenda,
                comentario=dados.comentario,
            )
        )
    elif atual.escondida_em is not None:
        raise ErroApi(*indicacoes_banco.OPINIAO_ESCONDIDA)
    else:
        atual.recomenda = dados.recomenda
        atual.comentario = dados.comentario
    db.flush()


def opinar(db: Session, logado: Logado, prestador_id: int, dados: DarOpiniao) -> None:
    """Dar e mudar a opinião são a mesma coisa. Dois aparelhos da mesma unidade ao mesmo tempo:
    o segundo `INSERT` esbarra na `opiniao_servico_unica` e tenta **uma vez** como `UPDATE`."""
    _buscar(db, logado, prestador_id)
    for tentativa in range(2):
        try:
            _gravar_opiniao(db, logado, prestador_id, dados)
            db.commit()
            return
        except ErroApi:
            db.rollback()
            raise
        except IntegrityError as falha:
            if tentativa == 0 and indicacoes_banco.restricao(falha) == "opiniao_servico_unica":
                db.rollback()
                continue
            raise _repassar(db, falha) from falha
        except DBAPIError as falha:
            raise _repassar(db, falha) from falha


def apagar_opiniao(db: Session, logado: Logado, prestador_id: int) -> None:
    """Apagar de verdade. A escondida pela gestão fica (409); a apagada conta no limite do dia
    (histórico `indicacao_opiniao_apagada`, lido pela trigger)."""
    _buscar(db, logado, prestador_id)
    atual = db.scalars(
        select(OpiniaoServico)
        .where(
            OpiniaoServico.prestador_id == prestador_id,
            OpiniaoServico.unidade_id == logado.unidade_id,
        )
        .with_for_update()
    ).one_or_none()
    if atual is None:
        db.rollback()
        raise ErroApi(404, "opiniao_nao_encontrada", "Você ainda não deu opinião aqui.")
    if atual.escondida_em is not None:
        db.rollback()
        raise ErroApi(*indicacoes_banco.OPINIAO_ESCONDIDA)
    db.delete(atual)
    registrar(
        db,
        Acao.indicacao_opiniao_apagada,
        unidade_id=logado.unidade_id,
        entidade="prestador",
        entidade_id=prestador_id,
    )
    db.commit()


# --- corrigir e avisar -------------------------------------------------------------------------


def corrigir(db: Session, logado: Logado, prestador_id: int, dados: CorrigirPrestador) -> None:
    """Quem indicou ou a gestão corrige nome, categoria e contatos. O telefone de outro
    prestador dá o mesmo 409 de indicar."""
    prestador = _buscar(db, logado, prestador_id)
    if not (logado.gestao or prestador.criado_por == logado.unidade_id):
        raise _sem_permissao()
    _conferir_categoria(db, dados.categoria_id)
    erro = erro_de_telefone(db, dados.telefone, menos=prestador_id)
    if erro is not None:
        raise erro
    try:
        db.execute(
            update(PrestadorModelo)
            .where(PrestadorModelo.id == prestador_id)
            .values(
                categoria_id=dados.categoria_id,
                nome=dados.nome,
                nome_busca=normalizar(dados.nome),
                telefone=dados.telefone,
                instagram=dados.instagram,
            )
        )
        db.commit()
    except IntegrityError as falha:
        if indicacoes_banco.restricao(falha) == "prestador_telefone_unico":
            db.rollback()
            raise (
                erro_de_telefone(db, dados.telefone, menos=prestador_id) or _repassar(db, falha)
            ) from falha
        raise _repassar(db, falha) from falha
    except DBAPIError as falha:
        raise _repassar(db, falha) from falha
    db.expire_all()


def avisar(db: Session, logado: Logado, prestador_id: int, dados: AvisarGestao) -> int | None:
    """ "Tem algo errado aqui?". Repetir é idempotente (nada muda). Devolve o id do aviso quando
    ele é o **primeiro aberto** do prestador (a rota manda o e-mail para a administração), ou
    `None`."""
    _buscar(db, logado, prestador_id, travar=True)
    abertos = list(
        db.scalars(
            select(AvisoServico.unidade_id).where(
                AvisoServico.prestador_id == prestador_id, AvisoServico.resolvido_em.is_(None)
            )
        )
    )
    if logado.unidade_id in abertos:
        db.rollback()
        return None
    aviso = AvisoServico(
        prestador_id=prestador_id, unidade_id=logado.unidade_id, motivo=dados.motivo
    )
    try:
        db.add(aviso)
        db.flush()
        aviso_id = aviso.id
        db.commit()
    except IntegrityError as falha:
        if indicacoes_banco.restricao(falha) == "aviso_servico_aberto":
            db.rollback()
            return None
        raise _repassar(db, falha) from falha
    except DBAPIError as falha:
        raise _repassar(db, falha) from falha
    return aviso_id if not abertos else None


# --- "apagar meus dados" e reset ---------------------------------------------------------------


def apagar_da_unidade(db: Session, unidade_id: int) -> None:
    """Apaga as opiniões (as escondidas também) e os avisos da unidade, e tira dela a autoria
    dos prestadores que indicou (o próximo morador não herda o direito de corrigir). O prestador
    fica: sem opinião visível, só sai da lista. Sem commit (quem chama decide)."""
    db.execute(delete(OpiniaoServico).where(OpiniaoServico.unidade_id == unidade_id))
    db.execute(delete(AvisoServico).where(AvisoServico.unidade_id == unidade_id))
    db.execute(
        update(PrestadorModelo)
        .where(PrestadorModelo.criado_por == unidade_id)
        .values(criado_por=None)
    )
