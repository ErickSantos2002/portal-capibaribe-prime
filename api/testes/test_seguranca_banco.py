"""Ataques ao banco que o usuário `app` (ou quem roubar a senha dele) poderia tentar."""

from datetime import UTC, datetime

import pytest
from psycopg.errors import CheckViolation, InsufficientPrivilege
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, ProgrammingError

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
                " values (:b, '101', 1, 'h') returning id"
            ),
            {"b": bloco_id},
        ).scalar_one()


# --- login forjado por tabela temporária (search_path) -------------------------------------


def test_app_nao_cria_tabela_temporaria(engine_app, unidade_1101):
    with pytest.raises(ProgrammingError) as erro, engine_app.begin() as con:
        con.execute(text("create temp table bloco (id bigint, numero text)"))
    assert isinstance(erro.value.orig, InsufficientPrivilege)


def test_app_nao_cria_tabela_no_schema_public(engine_app):
    with pytest.raises(ProgrammingError) as erro, engine_app.begin() as con:
        con.execute(text("create table public.intrusa (id int)"))
    assert isinstance(erro.value.orig, InsufficientPrivilege)


def test_tabela_temporaria_homonima_nao_forja_o_login(engine_dono, unidade_1101):
    # O dono (que pode criar tabela temporária) tenta o ataque: o trigger tem que ler
    # public.bloco, nunca pg_temp.bloco.
    with engine_dono.begin() as con:
        con.execute(text("create temp table bloco (id bigint, numero text)"))
        con.execute(text("insert into pg_temp.bloco values (1, 'admin')"))
        login = con.execute(
            text("update unidade set numero = numero where id = :u returning login"),
            {"u": unidade_1101},
        ).scalar_one()
    assert login == "1101"


@pytest.mark.parametrize("login", ["admin101", "101", "0101", "11011", "1a01"])
def test_login_fora_do_padrao_e_recusado_mesmo_sem_trigger(
    engine_superusuario, unidade_1101, login
):
    # Com os triggers desligados (só superusuário consegue), o CHECK ainda segura.
    with pytest.raises(IntegrityError) as erro, engine_superusuario.begin() as con:
        con.execute(text("set local session_replication_role = replica"))
        con.execute(
            text("update unidade set login = :l where id = :u"), {"l": login, "u": unidade_1101}
        )
    assert isinstance(erro.value.orig, CheckViolation)


# --- data do histórico forjada ---------------------------------------------------------------


def test_historico_ignora_data_mandada_pelo_app(engine_app, unidade_1101):
    antes = datetime.now(UTC)
    with engine_app.begin() as con:
        ocorrido = con.execute(
            text(
                "insert into historico (acao, ocorrido_em)"
                " values ('reset', '2001-01-01 00:00+00') returning ocorrido_em"
            )
        ).scalar_one()
    assert ocorrido.year != 2001
    assert abs((ocorrido - antes).total_seconds()) < 60
