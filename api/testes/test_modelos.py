"""Os modelos SQLAlchemy batem com o que a migração criou.

A migração é escrita à mão; este teste pega o caso de alguém mudar uma das duas pontas e
esquecer a outra.
"""

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.modelos import Base


def test_modelos_iguais_ao_banco_migrado(engine_dono):
    with engine_dono.connect() as con:
        diferencas = compare_metadata(MigrationContext.configure(con), Base.metadata)
    assert diferencas == []
