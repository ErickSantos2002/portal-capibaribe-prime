"""Moderação das indicações (spec de 18/10/2026, seções 3.2, 4 e 8): esconder o prestador ou
uma opinião e resolver aviso (a gestão), e as categorias (só a administração).

Ninguém precisa abrir as indicações para moderar: só quando alguém avisa. Esconder é definitivo
(não há "mostrar de novo") e vai para o histórico, sem o nome do prestador.
"""

from sqlalchemy import func, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.erros_api import ErroApi
from app.esquemas.indicacoes import CategoriaServico
from app.modelos.indicacoes import ORDEM_OUTROS, AvisoServico, OpiniaoServico
from app.modelos.indicacoes import CategoriaServico as CategoriaModelo
from app.modelos.indicacoes import Prestador as PrestadorModelo
from app.seguranca.dependencias import Logado
from app.servicos import indicacoes_banco
from app.servicos.historico import Acao, registrar
from app.servicos.indicacoes import nao_encontrada

PASSO_DA_ORDEM = 10


def _repassar(db: Session, erro: DBAPIError) -> ErroApi:
    db.rollback()
    traduzido = indicacoes_banco.traduzir(erro)
    if traduzido is None:
        raise erro
    return traduzido


def _gravar(db: Session) -> None:
    try:
        db.commit()
    except DBAPIError as erro:
        raise _repassar(db, erro) from erro


def esconder_prestador(db: Session, logado: Logado, prestador_id: int) -> None:
    """Sai da lista e não volta; o telefone continua ocupado. Os avisos abertos dele são
    resolvidos na mesma transação. Já escondido: nada muda."""
    prestador = db.scalars(
        select(PrestadorModelo).where(PrestadorModelo.id == prestador_id).with_for_update()
    ).one_or_none()
    if prestador is None:
        raise nao_encontrada()
    if prestador.escondido_em is not None:
        db.rollback()
        return
    try:
        db.execute(
            update(AvisoServico)
            .where(AvisoServico.prestador_id == prestador_id, AvisoServico.resolvido_em.is_(None))
            .values(resolvido_em=func.now(), resolvido_por=logado.unidade_id)
        )
        prestador.escondido_em = func.now()
        prestador.escondido_por = logado.unidade_id
        db.flush()
        registrar(
            db,
            Acao.indicacao_escondida,
            unidade_id=logado.unidade_id,
            entidade="prestador",
            entidade_id=prestador_id,
        )
    except DBAPIError as erro:
        raise _repassar(db, erro) from erro
    _gravar(db)


def esconder_opiniao(db: Session, logado: Logado, opiniao_id: int) -> None:
    """Ninguém mais a vê, menos a própria unidade, que não a muda nem apaga. Já escondida: nada
    muda."""
    opiniao = db.scalars(
        select(OpiniaoServico).where(OpiniaoServico.id == opiniao_id).with_for_update()
    ).one_or_none()
    if opiniao is None:
        raise ErroApi(404, "opiniao_nao_encontrada", "Opinião não encontrada.")
    if opiniao.escondida_em is not None:
        db.rollback()
        return
    try:
        opiniao.escondida_em = func.now()
        opiniao.escondida_por = logado.unidade_id
        db.flush()
        registrar(
            db,
            Acao.indicacao_opiniao_escondida,
            unidade_id=logado.unidade_id,
            entidade="prestador",
            entidade_id=opiniao.prestador_id,
            detalhes={"opiniao": opiniao_id},
        )
    except DBAPIError as erro:
        raise _repassar(db, erro) from erro
    _gravar(db)


def resolver_aviso(db: Session, logado: Logado, aviso_id: int) -> None:
    """Tira o aviso da seção da gestão. Já resolvido: nada muda."""
    aviso = db.scalars(
        select(AvisoServico).where(AvisoServico.id == aviso_id).with_for_update()
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
            Acao.indicacao_aviso_resolvido,
            unidade_id=logado.unidade_id,
            entidade="prestador",
            entidade_id=aviso.prestador_id,
        )
    except DBAPIError as erro:
        raise _repassar(db, erro) from erro
    _gravar(db)


def _ja_existe(db: Session, nome: str, *, menos: int | None = None) -> bool:
    consulta = select(CategoriaModelo.id).where(func.lower(CategoriaModelo.nome) == nome.lower())
    if menos is not None:
        consulta = consulta.where(CategoriaModelo.id != menos)
    return db.scalar(consulta) is not None


def _categoria_existe() -> ErroApi:
    return ErroApi(*indicacoes_banco.RESTRICOES["categoria_servico_nome_unico"])


def criar_categoria(db: Session, logado: Logado, nome: str) -> CategoriaServico:
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
            Acao.categoria_criada,
            unidade_id=logado.unidade_id,
            entidade="categoria_servico",
            entidade_id=categoria.id,
            detalhes={"categoria": nome},
        )
        resposta = CategoriaServico(id=categoria.id, nome=categoria.nome)
    except DBAPIError as erro:
        raise _repassar(db, erro) from erro
    _gravar(db)
    return resposta


def renomear_categoria(
    db: Session, logado: Logado, categoria_id: int, nome: str
) -> CategoriaServico:
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
            Acao.categoria_renomeada,
            unidade_id=logado.unidade_id,
            entidade="categoria_servico",
            entidade_id=categoria_id,
            detalhes={"categoria": nome},
        )
    except DBAPIError as erro:
        raise _repassar(db, erro) from erro
    _gravar(db)
    return CategoriaServico(id=categoria_id, nome=nome)
