"""O usuário `app` não apaga o que é oficial nem altera o histórico (modelo, seção 4; ADR-0003).

Cada teste conecta como `app`, do mesmo jeito que a API em produção.
"""

import pytest
from psycopg.errors import InsufficientPrivilege
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

pytestmark = pytest.mark.usefixtures("banco_limpo")


@pytest.fixture
def unidade_1101(engine_app) -> int:
    with engine_app.begin() as con:
        bloco_id = con.execute(
            text("insert into bloco (numero, nome) values (1, 'Bloco 1') returning id")
        ).scalar_one()
        return con.execute(
            text(
                "insert into unidade (bloco_id, numero, andar, senha_hash)"
                " values (:b, '101', 1, 'hash') returning id"
            ),
            {"b": bloco_id},
        ).scalar_one()


def _negado(engine, comando: str, **parametros) -> None:
    with pytest.raises(ProgrammingError) as erro, engine.begin() as con:
        con.execute(text(comando), parametros)
    assert isinstance(erro.value.orig, InsufficientPrivilege)


@pytest.mark.parametrize("tabela", ["bloco", "unidade", "unidade_papel", "historico"])
def test_app_nao_apaga_tabela_oficial(engine_app, unidade_1101, tabela):
    _negado(engine_app, f"delete from {tabela}")


def test_app_nao_altera_historico(engine_app, unidade_1101):
    with engine_app.begin() as con:
        con.execute(text("insert into historico (acao) values ('teste')"))
    _negado(engine_app, "update historico set acao = 'adulterado'")


def test_app_insere_no_historico(engine_app, unidade_1101):
    with engine_app.begin() as con:
        con.execute(
            text(
                "insert into historico (unidade_id, acao, entidade, entidade_id, detalhes)"
                " values (:u, 'reset', 'unidade', :u, '{\"motivo\": \"teste\"}')"
            ),
            {"u": unidade_1101},
        )
        assert con.execute(text("select count(*) from historico")).scalar_one() == 1


def test_app_altera_unidade_e_papel(engine_app, unidade_1101):
    with engine_app.begin() as con:
        con.execute(text("update unidade set ativa = false where id = :u"), {"u": unidade_1101})
        con.execute(
            text("insert into unidade_papel (unidade_id, papel) values (:u, 'comissao')"),
            {"u": unidade_1101},
        )
        con.execute(text("update unidade_papel set retirado_em = now()"))


def test_app_grava_e_apaga_erro_e_sessao(engine_app, unidade_1101):
    with engine_app.begin() as con:
        con.execute(
            text("insert into erro (rota, tipo, mensagem) values ('GET /api/x', 'Erro', 'm')")
        )
        con.execute(
            text("insert into sessao (unidade_id, token_hash, aparelho) values (:u, 'h', 'a')"),
            {"u": unidade_1101},
        )
        con.execute(text("update sessao set encerrada_em = now()"))
        con.execute(text("delete from erro"))
        con.execute(text("delete from sessao"))


def test_app_nao_le_versao_das_migracoes(engine_app):
    _negado(engine_app, "select * from alembic_version")
