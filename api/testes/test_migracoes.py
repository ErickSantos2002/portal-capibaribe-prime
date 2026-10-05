"""As migrações aplicam do zero, voltam e aplicam de novo (critério do M0)."""

import psycopg
import pytest

from testes.apoio import rodar_alembic
from testes.conftest import BANCO, apagar_banco, garantir_papeis, recriar_banco, url_para

BANCO_VAZIO = f"{BANCO}_migracoes"


@pytest.fixture
def banco_vazio():
    garantir_papeis()
    recriar_banco(BANCO_VAZIO)
    yield url_para("dono", BANCO_VAZIO)
    apagar_banco(BANCO_VAZIO)


def _tabelas(url: str) -> set[str]:
    with psycopg.connect(url) as con:
        linhas = con.execute(
            "select tablename from pg_tables where schemaname = 'public'"
        ).fetchall()
    return {t for (t,) in linhas}


def test_upgrade_downgrade_upgrade(banco_vazio):
    esperadas = {
        "bloco",
        "unidade",
        "unidade_papel",
        "sessao",
        "historico",
        "erro",
        "aviso",
        "aviso_versao",
        "aviso_bloco",
        "aviso_leitura",
    }

    rodar_alembic(banco_vazio, "upgrade", "head")
    assert esperadas <= _tabelas(banco_vazio)

    rodar_alembic(banco_vazio, "downgrade", "base")
    assert _tabelas(banco_vazio) == {"alembic_version"}

    rodar_alembic(banco_vazio, "upgrade", "head")
    assert esperadas <= _tabelas(banco_vazio)


def test_migracao_falha_com_mensagem_clara_sem_papel_app(banco_vazio):
    with pytest.raises(RuntimeError, match=r"papel .*papel_que_nao_existe.* não existe"):
        rodar_alembic(banco_vazio, "upgrade", "head", x=["papel_app=papel_que_nao_existe"])
    # Nada ficou pela metade: a migração roda numa transação só.
    assert _tabelas(banco_vazio) <= {"alembic_version"}


def test_downgrade_da_0002_volta_ao_m0(banco_vazio):
    rodar_alembic(banco_vazio, "upgrade", "head")
    rodar_alembic(banco_vazio, "downgrade", "0001")
    assert _tabelas(banco_vazio) == {
        "alembic_version",
        "bloco",
        "unidade",
        "unidade_papel",
        "sessao",
        "historico",
        "erro",
    }
    rodar_alembic(banco_vazio, "upgrade", "head")
    assert "aviso" in _tabelas(banco_vazio)
