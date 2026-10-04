"""Ambiente do Alembic. Só modo online: as migrações sempre rodam contra um banco real.

A URL vem de `config.attributes["url"]` (testes) ou da variável `DATABASE_URL_DONO`. As
migrações rodam como `dono`, o dono das tabelas; a API usa outro usuário (`app`).
"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from app.banco import url_sqlalchemy
from app.modelos import Base

config = context.config

if config.config_file_name is not None and not config.attributes.get("url"):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _url() -> str:
    url = config.attributes.get("url") or os.environ.get("DATABASE_URL_DONO", "")
    if not url:
        raise RuntimeError(
            "Defina DATABASE_URL_DONO com a URL do usuário dono das tabelas "
            "(conexão direta, sem o pooler)."
        )
    return url_sqlalchemy(url)


def run_migrations_online() -> None:
    engine = create_engine(_url(), poolclass=NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Tudo numa transação só: se algo falhar, nada fica pela metade.
            transaction_per_migration=False,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError("Modo offline não é usado neste projeto.")
run_migrations_online()
