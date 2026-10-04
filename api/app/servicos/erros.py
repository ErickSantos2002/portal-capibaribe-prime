"""Registro de exceções não tratadas na tabela `erro` e no log, sem dado pessoal.

Os logs grátis da Vercel duram 1 hora (arquitetura, seção 8), então o erro precisa ficar no
banco. A regra do modelo de dados é: **sem dado pessoal e sem corpo da requisição**, e ela vale
também para o log do servidor. Por isso:

- a mensagem sempre passa por `mensagem_segura`, que só copia texto de exceções do próprio
  Portal (`ErroDoPortal`);
- a captura é um middleware ASGI (`RegistroDeErros`), que responde o 500 e **não relança** a
  exceção. Um `exception_handler(Exception)` do FastAPI não serve: o `ServerErrorMiddleware` do
  Starlette relança depois do handler, e o servidor imprime o traceback com `str(exc)`.
"""

import logging
import traceback
from pathlib import PurePath

import psycopg
from pydantic import ValidationError
from sqlalchemy.exc import DBAPIError
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.banco import fabrica_de_sessoes
from app.modelos import Erro

logger = logging.getLogger("portal.erros")

LIMITE_MENSAGEM = 500


class ErroDoPortal(Exception):
    """Exceção do código do Portal. A mensagem dela vai para o registro, então nunca leva dado
    pessoal (nome, celular, e-mail, o que a pessoa digitou)."""


def _onde(exc: BaseException) -> str | None:
    """`arquivo.py:linha` de onde a exceção foi levantada (o fim do traceback)."""
    quadros = traceback.extract_tb(exc.__traceback__)
    if not quadros:
        return None
    ultimo = quadros[-1]
    caminho = PurePath(ultimo.filename)
    partes = caminho.parts
    # Encurta para o que importa: "app/rotas/x.py" ou "pacote/modulo.py" (sem a pasta da venv).
    for marco in ("app", "site-packages"):
        if marco in partes:
            inicio = len(partes) - partes[::-1].index(marco)
            if marco == "app":
                inicio -= 1
            caminho = PurePath(*partes[inicio:])
            break
    else:
        caminho = PurePath(caminho.name)
    return f"{caminho.as_posix()}:{ultimo.lineno}"


def mensagem_segura(exc: BaseException) -> str:
    """Descrição curta da exceção que não carrega dado de quem usou o sistema.

    - Erro do banco: classe, SQLSTATE e nome da restrição/tabela/coluna. A mensagem do Postgres
      traz valores (`DETAIL: Key (email)=(...)`) e a do SQLAlchemy traz os parâmetros.
    - Erro de validação (pydantic): campo e tipo do problema, nunca o valor recebido.
    - `ErroDoPortal`: a primeira linha da mensagem, escrita por nós.
    - Qualquer outra (`ValueError`, `KeyError`...): só o tipo e onde aconteceu. A mensagem dessas
      costuma repetir o valor que causou o erro (`invalid literal for int(): '81 9...'`).
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
        # Só o primeiro nível do caminho (o nome do campo do modelo): níveis abaixo podem ser
        # chaves de dicionário vindas de quem digitou.
        problemas = ", ".join(
            f"{e['loc'][0] if e['loc'] else '?'}: {e['type']}" for e in exc.errors()
        )
        texto = f"{exc.error_count()} erro(s) de validação em {exc.title}: {problemas}"
    elif isinstance(exc, ErroDoPortal):
        linhas = str(exc).splitlines()
        texto = linhas[0] if linhas else ""
    else:
        onde = _onde(exc)
        texto = type(exc).__name__ + (f" em {onde}" if onde else "")
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


class RegistroDeErros:
    """Middleware ASGI: exceção não tratada vira linha em `erro`, log seguro e um 500 limpo.

    Fica por dentro do `ServerErrorMiddleware` do Starlette e por fora das rotas; HTTPException
    e erros de validação do FastAPI já viraram resposta antes de chegar aqui.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        resposta_iniciada = False

        async def enviar(mensagem: Message) -> None:
            nonlocal resposta_iniciada
            if mensagem["type"] == "http.response.start":
                resposta_iniciada = True
            await send(mensagem)

        try:
            await self.app(scope, receive, enviar)
        except Exception as exc:  # noqa: BLE001 - é exatamente o papel deste middleware
            request = Request(scope)
            logger.error(
                "Erro não tratado em %s: %s", descrever_rota(request), mensagem_segura(exc)
            )
            await run_in_threadpool(registrar_erro, request, exc)
            if not resposta_iniciada:
                resposta = JSONResponse(status_code=500, content={"detail": "Erro interno"})
                await resposta(scope, receive, send)
