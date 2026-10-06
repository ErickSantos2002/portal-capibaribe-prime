"""Categoria e evento do aviso no próprio banco (migração 0004).

Tudo como o usuário `app`, do jeito que a API conecta em produção. Spec:
`docs/superpowers/specs/2026-10-06-avisos-visual-design.md`, seção 3.2.
"""

import pytest
from psycopg.errors import InsufficientPrivilege
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from testes.apoio import criar_bloco, criar_unidade, restricao

pytestmark = pytest.mark.usefixtures("banco_limpo")


@pytest.fixture
def ids(engine_app) -> dict[str, int]:
    with engine_app.begin() as con:
        b = criar_bloco(con, 1)
        u = criar_unidade(con, b, "304")
        a = con.execute(
            text(
                "insert into aviso (publicado_por, publicado_como, para_todos)"
                " values (:u, 'comissao', true) returning id"
            ),
            {"u": u},
        ).scalar_one()
        con.execute(
            text(
                "insert into aviso_versao (aviso_id, versao, titulo, texto, criada_por)"
                " values (:a, 1, 'Título', 'Texto', :u)"
            ),
            {"a": a, "u": u},
        )
    return {"u": u, "a": a}


def _versao(con, ids: dict[str, int], **colunas) -> None:
    """Insere a versão 2 com as colunas novas pedidas."""
    nomes = "".join(f", {c}" for c in colunas)
    valores = "".join(f", :{c}" for c in colunas)
    con.execute(
        text(
            f"insert into aviso_versao (aviso_id, versao, titulo, texto, criada_por{nomes})"
            f" values (:a, 2, 'T', 'X', :u{valores})"
        ),
        {"a": ids["a"], "u": ids["u"], **colunas},
    )


def test_padrao_e_geral_sem_evento(engine_app, ids):
    with engine_app.connect() as con:
        linha = con.execute(
            text("select categoria, evento_quando, evento_onde from aviso_versao")
        ).one()
    assert tuple(linha) == ("geral", None, None)


@pytest.mark.parametrize("categoria", ["geral", "obra", "reuniao", "financeiro", "urgente"])
def test_categorias_aceitas(engine_app, ids, categoria):
    with engine_app.begin() as con:
        _versao(con, ids, categoria=categoria)


@pytest.mark.parametrize("categoria", ["festa", "Geral", "", "reunião"])
def test_categoria_desconhecida_recusada(engine_app, ids, categoria):
    with pytest.raises(IntegrityError) as erro, engine_app.begin() as con:
        _versao(con, ids, categoria=categoria)
    assert restricao(erro.value) == "aviso_versao_categoria"


def test_onde_sem_quando_recusado(engine_app, ids):
    with pytest.raises(IntegrityError) as erro, engine_app.begin() as con:
        _versao(con, ids, evento_onde="Stand de vendas")
    assert restricao(erro.value) == "aviso_versao_evento_completo"


def test_evento_sem_local_aceito(engine_app, ids):
    with engine_app.begin() as con:
        _versao(con, ids, evento_quando="2026-10-11 09:00-03")


def test_evento_com_local_aceito(engine_app, ids):
    with engine_app.begin() as con:
        _versao(con, ids, evento_quando="2026-10-11 09:00-03", evento_onde="Stand de vendas")


@pytest.mark.parametrize("onde", ["", "   ", "x" * 121])
def test_onde_com_limites(engine_app, ids, onde):
    with pytest.raises(IntegrityError) as erro, engine_app.begin() as con:
        _versao(con, ids, evento_quando="2026-10-11 09:00-03", evento_onde=onde)
    assert restricao(erro.value) == "aviso_versao_evento_onde_tamanho"


@pytest.mark.parametrize(
    "comando",
    [
        "update aviso_versao set categoria = 'urgente'",
        "update aviso_versao set evento_quando = now()",
        "update aviso_versao set evento_onde = 'outro lugar'",
    ],
)
def test_app_nao_reescreve_categoria_nem_evento(engine_app, ids, comando):
    # Correção é versão nova (spec, seção 3.2): o app continua sem UPDATE em aviso_versao.
    with pytest.raises(ProgrammingError) as erro, engine_app.begin() as con:
        con.execute(text(comando))
    assert isinstance(erro.value.orig, InsufficientPrivilege)
