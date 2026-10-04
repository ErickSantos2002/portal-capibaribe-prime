"""Infra dos testes: um Postgres de verdade, com os mesmos papéis da produção.

Produção (ADR-0003) tem dois usuários de banco: `dono` (dono das tabelas, roda as migrações) e
`app` (o que a API usa, sem DELETE no que é oficial). Aqui os dois são criados num Postgres
local ou no service container do CI, e o banco de teste nasce pela migração, como em produção.

Variável: `PORTAL_TESTE_ADMIN_URL` (superusuário do Postgres de teste). Padrão: o container
local `portal-pg-m0` na porta 55432.
"""

import os
from collections.abc import Iterator
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from sqlalchemy import Engine, create_engine
from sqlalchemy.pool import NullPool

from testes.apoio import rodar_alembic

ADMIN_URL = os.environ.get(
    "PORTAL_TESTE_ADMIN_URL", "postgresql://postgres:teste@127.0.0.1:55432/postgres"
)
# Senhas só de teste, num banco descartável que escuta apenas em 127.0.0.1.
PAPEIS = {"dono": "dono-teste", "app": "app-teste"}
BANCO = "portal_teste"
TABELAS = ["erro", "historico", "sessao", "unidade_papel", "unidade", "bloco"]


def url_para(usuario: str, banco: str) -> str:
    """URL do Postgres de teste para outro usuário e banco (mesmo host e porta)."""
    partes = urlsplit(ADMIN_URL)
    netloc = f"{usuario}:{PAPEIS[usuario]}@{partes.hostname}:{partes.port or 5432}"
    return urlunsplit(("postgresql", netloc, f"/{banco}", "", ""))


def garantir_papeis() -> None:
    """Cria `dono` e `app` se ainda não existirem (papéis valem para o servidor inteiro)."""
    with psycopg.connect(ADMIN_URL, autocommit=True) as con:
        for nome, senha in PAPEIS.items():
            existe = con.execute("select 1 from pg_roles where rolname = %s", [nome]).fetchone()
            if not existe:
                con.execute(
                    sql.SQL("create role {} login password {}").format(
                        sql.Identifier(nome), sql.Literal(senha)
                    )
                )


def recriar_banco(nome: str) -> None:
    """Banco vazio, de propriedade do `dono` (como o banco do Neon)."""
    with psycopg.connect(ADMIN_URL, autocommit=True) as con:
        con.execute(sql.SQL("drop database if exists {} with (force)").format(sql.Identifier(nome)))
        con.execute(sql.SQL("create database {} owner dono").format(sql.Identifier(nome)))


def apagar_banco(nome: str) -> None:
    with psycopg.connect(ADMIN_URL, autocommit=True) as con:
        con.execute(sql.SQL("drop database if exists {} with (force)").format(sql.Identifier(nome)))


@pytest.fixture(scope="session")
def url_dono() -> Iterator[str]:
    garantir_papeis()
    recriar_banco(BANCO)
    url = url_para("dono", BANCO)
    rodar_alembic(url, "upgrade", "head")
    yield url
    apagar_banco(BANCO)


@pytest.fixture(scope="session")
def url_app(url_dono: str) -> str:
    return url_para("app", BANCO)


def _engine(url: str) -> Engine:
    return create_engine(url.replace("postgresql://", "postgresql+psycopg://"), poolclass=NullPool)


@pytest.fixture(scope="session")
def engine_dono(url_dono: str) -> Engine:
    return _engine(url_dono)


@pytest.fixture(scope="session")
def engine_app(url_app: str) -> Engine:
    return _engine(url_app)


@pytest.fixture(scope="session")
def engine_superusuario(url_dono: str) -> Engine:
    """Superusuário no banco de teste: só para simular ataques que pulam as regras do app."""
    partes = urlsplit(ADMIN_URL)
    return _engine(urlunsplit((partes.scheme, partes.netloc, f"/{BANCO}", "", "")))


@pytest.fixture
def cliente(url_app: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """A API como em produção: conectada como `app`. Erro 500 vira resposta, não exceção."""
    from app import banco
    from app.main import app

    monkeypatch.setenv("DATABASE_URL", url_app)
    banco.obter_engine.cache_clear()
    yield TestClient(app, raise_server_exceptions=False)
    banco.obter_engine.cache_clear()


@pytest.fixture
def banco_limpo(url_dono: str) -> None:
    """Esvazia as tabelas (como `dono`) antes do teste. O `app` não poderia fazer isso."""
    with psycopg.connect(url_dono, autocommit=True) as con:
        con.execute(f"truncate {', '.join(TABELAS)} restart identity cascade")
