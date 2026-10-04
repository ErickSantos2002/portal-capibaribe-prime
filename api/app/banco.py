"""Conexão com o Postgres.

Em produção a API é uma função serverless (ADR-0002): cada instância pode morrer a qualquer
momento e várias rodam em paralelo. Por isso:

- `NullPool`: a API não guarda conexões abertas; quem faz o pool é o pooler do Neon (ADR-0003).
- `prepare_threshold=None`: o pooler do Neon trabalha em modo transação, e o psycopg 3 não deve
  criar prepared statements que podem cair em outra conexão do servidor.
"""

import os
from collections.abc import Iterator
from functools import cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

_PREFIXOS = ("postgresql+psycopg://", "postgresql://", "postgres://")


def url_sqlalchemy(url: str) -> str:
    """Converte a URL do Postgres (como o Neon entrega) para o driver psycopg 3."""
    url = url.strip()
    for prefixo in _PREFIXOS:
        if url.startswith(prefixo):
            return "postgresql+psycopg://" + url.removeprefix(prefixo)
    raise RuntimeError(
        "DATABASE_URL precisa ser uma URL do Postgres (postgresql://usuario:senha@host/banco)."
    )


@cache
def obter_engine() -> Engine:
    url = os.environ.get("DATABASE_URL", "")
    if not url.strip():
        raise RuntimeError("Defina DATABASE_URL com a URL do usuário app (pooler do Neon).")
    return create_engine(
        url_sqlalchemy(url),
        poolclass=NullPool,
        connect_args={"prepare_threshold": None},
    )


def fabrica_de_sessoes() -> sessionmaker[Session]:
    return sessionmaker(obter_engine(), expire_on_commit=False)


def obter_sessao() -> Iterator[Session]:
    """Dependência do FastAPI: uma sessão por requisição, fechada no fim."""
    with fabrica_de_sessoes()() as sessao:
        yield sessao
