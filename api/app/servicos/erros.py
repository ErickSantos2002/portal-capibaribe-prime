"""Registro de exceções não tratadas na tabela `erro`.

Os logs grátis da Vercel duram 1 hora (arquitetura, seção 8), então o erro precisa ficar no
banco. A regra do modelo de dados é: **sem dado pessoal e sem corpo da requisição**. Por isso a
mensagem passa por `mensagem_segura`, que nunca copia valores de erros do banco ou de validação.
"""

import logging

import psycopg
from pydantic import ValidationError
from sqlalchemy.exc import DBAPIError
from starlette.requests import Request

from app.banco import fabrica_de_sessoes
from app.modelos import Erro

logger = logging.getLogger("portal.erros")

LIMITE_MENSAGEM = 500


def mensagem_segura(exc: BaseException) -> str:
    """Descrição curta da exceção que não carrega dado de quem usou o sistema.

    - Erro do banco: só a classe, o SQLSTATE e o nome da restrição/tabela. A mensagem do
      Postgres pode trazer valores (`DETAIL: Key (email)=(...)`, `invalid input: "..."`) e a do
      SQLAlchemy traz os parâmetros da consulta.
    - Erro de validação (pydantic): só o campo e o tipo do problema, nunca o valor recebido.
    - Qualquer outra: a primeira linha da mensagem. Quem levanta exceção no código do Portal não
      põe dado pessoal na mensagem.
    """
    original = exc.orig if isinstance(exc, DBAPIError) else exc
    if isinstance(original, psycopg.Error):
        partes = [type(original).__name__]
        if original.sqlstate:
            partes.append(f"SQLSTATE {original.sqlstate}")
        diag = original.diag
        for rotulo, valor in (
            ("restrição", diag.constraint_name),
            ("tabela", diag.table_name),
            ("coluna", diag.column_name),
        ):
            if valor:
                partes.append(f"{rotulo} {valor}")
        texto = " · ".join(partes)
    elif isinstance(exc, ValidationError):
        problemas = ", ".join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['type']}" for e in exc.errors()
        )
        texto = f"{exc.error_count()} erro(s) de validação em {exc.title}: {problemas}"
    else:
        linhas = str(exc).splitlines()
        texto = linhas[0] if linhas else ""
    return texto[:LIMITE_MENSAGEM]


def descrever_rota(request: Request) -> str:
    """`MÉTODO /molde/da/rota` (ex.: `GET /api/avisos/{aviso_id}`), sem os valores da URL."""
    rota = request.scope.get("route")
    caminho = getattr(rota, "path", None) or request.url.path
    return f"{request.method} {caminho}"


def registrar_erro(request: Request, exc: BaseException) -> None:
    """Grava a exceção em `erro`. Nunca levanta: se o banco falhar, fica só no log."""
    try:
        with fabrica_de_sessoes()() as sessao:
            sessao.add(
                Erro(
                    rota=descrever_rota(request),
                    tipo=type(exc).__name__,
                    mensagem=mensagem_segura(exc),
                    unidade_id=getattr(request.state, "unidade_id", None),
                )
            )
            sessao.commit()
    except Exception as falha:  # noqa: BLE001 - registrar o erro não pode gerar outro erro
        logger.error("Não foi possível gravar o erro no banco: %s", mensagem_segura(falha))
