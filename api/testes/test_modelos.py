"""Os modelos SQLAlchemy batem com o que a migração criou.

A migração é escrita à mão; este teste pega o caso de alguém mudar uma das duas pontas e
esquecer a outra.
"""

import psycopg
import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from app.modelos import Base
from testes.conftest import BANCO, apagar_banco, garantir_papeis, recriar_banco, url_para

BANCO_DOS_MODELOS = f"{BANCO}_modelos"

_CHECKS = """
select c.conrelid::regclass::text, c.conname, pg_get_constraintdef(c.oid)
  from pg_constraint c join pg_namespace n on n.oid = c.connamespace
 where c.contype = 'c' and n.nspname = 'public'
"""


def test_modelos_iguais_ao_banco_migrado(engine_dono):
    with engine_dono.connect() as con:
        diferencas = compare_metadata(MigrationContext.configure(con), Base.metadata)
    assert diferencas == []


@pytest.fixture
def banco_dos_modelos():
    """Banco criado só a partir dos modelos (`create_all`), para comparar com o migrado."""
    garantir_papeis()
    recriar_banco(BANCO_DOS_MODELOS)
    url = url_para("dono", BANCO_DOS_MODELOS)
    motor = create_engine(url.replace("postgresql://", "postgresql+psycopg://"), poolclass=NullPool)
    Base.metadata.create_all(motor)
    motor.dispose()
    yield url
    apagar_banco(BANCO_DOS_MODELOS)


def _checks(url: str) -> dict[tuple[str, str], str]:
    with psycopg.connect(url) as con:
        return {(t, nome): definicao for t, nome, definicao in con.execute(_CHECKS).fetchall()}


def test_checks_dos_modelos_iguais_aos_da_migracao(url_dono, banco_dos_modelos):
    # O autogenerate do Alembic não compara CHECK; aqui o próprio Postgres normaliza os dois
    # lados (pg_get_constraintdef), então diferença de texto que não muda a regra não conta.
    assert _checks(banco_dos_modelos) == _checks(url_dono)
