"""Funções de apoio dos testes que não são fixtures."""

from argparse import Namespace
from pathlib import Path

from alembic import command
from alembic.config import Config

RAIZ_API = Path(__file__).resolve().parent.parent


def rodar_alembic(url: str, acao: str, alvo: str, x: list[str] | None = None) -> None:
    """Roda `alembic upgrade|downgrade <alvo>` contra `url`, como o CLI faria.

    `x` repassa argumentos `-x chave=valor` para a migração.
    """
    cfg = Config(str(RAIZ_API / "alembic.ini"), cmd_opts=Namespace(x=x or []))
    cfg.set_main_option("script_location", str(RAIZ_API / "migracoes"))
    cfg.attributes["url"] = url
    getattr(command, acao)(cfg, alvo)
