"""Moderação e faxina dos classificados (spec de 20/10/2026, seções 3.2, 6 e 9).

- Esconder o anúncio e resolver aviso: a gestão. Esconder é definitivo, resolve os avisos abertos
  na mesma transação e vai para o histórico, sem o título nem a placa.
- Categorias: só a administração, como nas indicações.
- Faxina diária (Vercel Cron, ADR-0012): apaga o anúncio vencido há mais de 30 dias e o encerrado
  ou escondido há mais de 7 (com os avisos e as fotos), e as fotos esquecidas (enviadas há mais de
  1 dia e nunca postas num anúncio). Falhar só atrasa: a lista já filtra o vencido pela data.
"""

import logging

from sqlalchemy import delete, func, literal_column, or_, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.erros_api import ErroApi
from app.esquemas.classificados import CategoriaClassificado, ResultadoDaFaxina
from app.modelos.classificados import (
    FAXINA_ENCERRADO_DIAS,
    FAXINA_VENCIDO_DIAS,
    ORDEM_OUTROS,
    Anuncio,
    AnuncioFoto,
    AvisoAnuncio,
    SituacaoAnuncio,
)
from app.modelos.classificados import CategoriaClassificado as CategoriaModelo
from app.seguranca.dependencias import Logado
from app.servicos import classificados_banco, classificados_fotos
from app.servicos.armazenamento import Armazenamento
from app.servicos.classificados import indisponivel
from app.servicos.historico import Acao, registrar

log = logging.getLogger(__name__)

PASSO_DA_ORDEM = 10


def _repassar(db: Session, erro: DBAPIError) -> ErroApi:
    db.rollback()
    traduzido = classificados_banco.traduzir(erro)
    if traduzido is None:
        raise erro
    return traduzido


def _gravar(db: Session) -> None:
    try:
        db.commit()
    except DBAPIError as erro:
        raise _repassar(db, erro) from erro


def esconder(db: Session, logado: Logado, anuncio_id: int) -> None:
    """Sai da lista e não volta; o dono só encerra. Os avisos abertos dele são resolvidos na
    mesma transação. Já escondido: nada muda."""
    anuncio = db.scalars(
        select(Anuncio).where(Anuncio.id == anuncio_id).with_for_update()
    ).one_or_none()
    if anuncio is None:
        raise indisponivel()
    if anuncio.escondido_em is not None:
        db.rollback()
        return
    try:
        db.execute(
            update(AvisoAnuncio)
            .where(AvisoAnuncio.anuncio_id == anuncio_id, AvisoAnuncio.resolvido_em.is_(None))
            .values(resolvido_em=func.now(), resolvido_por=logado.unidade_id)
        )
        anuncio.escondido_em = func.now()
        anuncio.escondido_por = logado.unidade_id
        db.flush()
        registrar(
            db,
            Acao.classificado_escondido,
            unidade_id=logado.unidade_id,
            entidade="anuncio",
            entidade_id=anuncio_id,
        )
    except DBAPIError as erro:
        raise _repassar(db, erro) from erro
    _gravar(db)


def resolver_aviso(db: Session, logado: Logado, aviso_id: int) -> None:
    """Tira o aviso da seção da gestão. Já resolvido: nada muda."""
    aviso = db.scalars(
        select(AvisoAnuncio).where(AvisoAnuncio.id == aviso_id).with_for_update()
    ).one_or_none()
    if aviso is None:
        raise ErroApi(404, "aviso_nao_encontrado", "Aviso não encontrado.")
    if aviso.resolvido_em is not None:
        db.rollback()
        return
    try:
        aviso.resolvido_em = func.now()
        aviso.resolvido_por = logado.unidade_id
        db.flush()
        registrar(
            db,
            Acao.classificado_aviso_resolvido,
            unidade_id=logado.unidade_id,
            entidade="anuncio",
            entidade_id=aviso.anuncio_id,
        )
    except DBAPIError as erro:
        raise _repassar(db, erro) from erro
    _gravar(db)


# --- categorias --------------------------------------------------------------------------------


def _ja_existe(db: Session, nome: str, *, menos: int | None = None) -> bool:
    consulta = select(CategoriaModelo.id).where(func.lower(CategoriaModelo.nome) == nome.lower())
    if menos is not None:
        consulta = consulta.where(CategoriaModelo.id != menos)
    return db.scalar(consulta) is not None


def _categoria_existe() -> ErroApi:
    return ErroApi(*classificados_banco.RESTRICOES["categoria_classificado_nome_unico"])


def criar_categoria(db: Session, logado: Logado, nome: str) -> CategoriaClassificado:
    """Entra no fim, antes de "Outros"."""
    if _ja_existe(db, nome):
        raise _categoria_existe()
    maior = db.scalar(
        select(func.max(CategoriaModelo.ordem)).where(CategoriaModelo.ordem < ORDEM_OUTROS)
    )
    categoria = CategoriaModelo(
        nome=nome, ordem=min((maior or 0) + PASSO_DA_ORDEM, ORDEM_OUTROS - 1)
    )
    try:
        db.add(categoria)
        db.flush()
        registrar(
            db,
            Acao.categoria_classificado_criada,
            unidade_id=logado.unidade_id,
            entidade="categoria_classificado",
            entidade_id=categoria.id,
            detalhes={"categoria": nome},
        )
        resposta = CategoriaClassificado(id=categoria.id, nome=categoria.nome)
    except DBAPIError as erro:
        raise _repassar(db, erro) from erro
    _gravar(db)
    return resposta


def renomear_categoria(
    db: Session, logado: Logado, categoria_id: int, nome: str
) -> CategoriaClassificado:
    categoria = db.get(CategoriaModelo, categoria_id, with_for_update=True)
    if categoria is None:
        raise ErroApi(404, "categoria_nao_encontrada", "Categoria não encontrada.")
    if _ja_existe(db, nome, menos=categoria_id):
        db.rollback()
        raise _categoria_existe()
    try:
        categoria.nome = nome
        db.flush()
        registrar(
            db,
            Acao.categoria_classificado_renomeada,
            unidade_id=logado.unidade_id,
            entidade="categoria_classificado",
            entidade_id=categoria_id,
            detalhes={"categoria": nome},
        )
    except DBAPIError as erro:
        raise _repassar(db, erro) from erro
    _gravar(db)
    return CategoriaClassificado(id=categoria_id, nome=nome)


# --- faxina ------------------------------------------------------------------------------------


def _dias(n: int):
    return literal_column(f"interval '{n} days'")


def faxinar(db: Session, armazenamento: Armazenamento | None) -> ResultadoDaFaxina:
    """Uma rodada da faxina. Idempotente: rodar duas vezes no mesmo dia não apaga nada a mais.

    1. Na mesma transação: descarta as fotos dos anúncios que vão sair e as esquecidas, e apaga os
       anúncios (os avisos vão juntos, pela chave estrangeira).
    2. Depois do commit: apaga do bucket todas as fotos descartadas (inclusive as que uma
       rodada anterior não conseguiu) e as linhas com mais de 1 dia.
    3. Registra no histórico quando apagou alguma coisa (só as contagens).
    """
    vao_sair = select(Anuncio.id).where(
        or_(
            Anuncio.vence_em < func.now() - _dias(FAXINA_VENCIDO_DIAS),
            (Anuncio.situacao == SituacaoAnuncio.encerrado.value)
            & (Anuncio.encerrado_em < func.now() - _dias(FAXINA_ENCERRADO_DIAS)),
            # O escondido pela gestão sai como o encerrado (revisão M3, decisão do coordenador).
            Anuncio.escondido_em < func.now() - _dias(FAXINA_ENCERRADO_DIAS),
        )
    )
    ids = list(db.scalars(vao_sair.with_for_update()))
    classificados_fotos.descartar(
        db,
        or_(
            AnuncioFoto.anuncio_id.in_(ids),
            AnuncioFoto.anuncio_id.is_(None)
            & (AnuncioFoto.enviada_em < func.now() - classificados_fotos.GUARDA_DA_LINHA),
        ),
    )
    if ids:
        db.execute(delete(Anuncio).where(Anuncio.id.in_(ids)))
    db.commit()
    fotos = classificados_fotos.varrer(db, armazenamento)
    if ids or fotos:
        registrar(
            db,
            Acao.classificados_faxina,
            unidade_id=None,
            detalhes={"anuncios": len(ids), "fotos": fotos},
        )
        db.commit()
        log.info("faxina dos classificados: %d anúncio(s), %d foto(s)", len(ids), fotos)
    return ResultadoDaFaxina(anuncios=len(ids), fotos=fotos)
