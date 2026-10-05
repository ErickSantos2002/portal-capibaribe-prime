"""Funções de apoio dos testes que não são fixtures."""

from argparse import Namespace
from pathlib import Path

import psycopg
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError

RAIZ_API = Path(__file__).resolve().parent.parent


def rodar_alembic(url: str, acao: str, alvo: str, x: list[str] | None = None) -> None:
    """Roda `alembic upgrade|downgrade <alvo>` contra `url`, como o CLI faria.

    `x` repassa argumentos `-x chave=valor` para a migração.
    """
    cfg = Config(str(RAIZ_API / "alembic.ini"), cmd_opts=Namespace(x=x or []))
    cfg.set_main_option("script_location", str(RAIZ_API / "migracoes"))
    cfg.attributes["url"] = url
    getattr(command, acao)(cfg, alvo)


def criar_bloco(con: Connection, numero: int) -> int:
    """Insere um bloco (SQL cru) e devolve o id."""
    return con.execute(
        text("insert into bloco (numero, nome) values (:n, :nome) returning id"),
        {"n": numero, "nome": f"Bloco {numero}"},
    ).scalar_one()


def criar_unidade(con: Connection, bloco_id: int, numero: str, **extra) -> int:
    """Insere uma unidade com senha de mentira e devolve o id. `extra` sobrescreve colunas."""
    colunas = {"bloco_id": bloco_id, "numero": numero, "andar": int(numero[0]), "senha_hash": "h"}
    colunas.update(extra)
    nomes = ", ".join(colunas)
    valores = ", ".join(f":{c}" for c in colunas)
    return con.execute(
        text(f"insert into unidade ({nomes}) values ({valores}) returning id"), colunas
    ).scalar_one()


def restricao(erro: BaseException) -> str | None:
    """Nome da restrição (CHECK, trigger com `constraint =`) que o Postgres recusou."""
    assert isinstance(erro, DBAPIError) and isinstance(erro.orig, psycopg.Error), erro
    return erro.orig.diag.constraint_name
