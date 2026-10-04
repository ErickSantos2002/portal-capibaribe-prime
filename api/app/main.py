"""Ponto de entrada da API (FastAPI). Na Vercel, `app.main:app` atende `/api/*`.

As rotas já carregam o prefixo `/api`: a Vercel repassa o caminho original para o serviço, e o
`uvicorn` local responde nos mesmos endereços.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.rotas import diagnostico, saude
from app.servicos.erros import mensagem_segura, registrar_erro

logger = logging.getLogger("portal")

# Documentação interativa desligada: o contrato sai de `app.openapi()` quando for preciso
# gerar os tipos do front, sem expor /docs em produção.
app = FastAPI(
    title="Portal Capibaribe Prime",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.include_router(saude.rotas)
app.include_router(diagnostico.rotas)


@app.exception_handler(Exception)
async def erro_nao_tratado(request: Request, exc: Exception) -> JSONResponse:
    """Toda exceção não tratada vira uma linha em `erro` e um 500 sem detalhes."""
    logger.error(
        "Erro não tratado em %s %s: %s", request.method, request.url.path, mensagem_segura(exc)
    )
    await run_in_threadpool(registrar_erro, request, exc)
    return JSONResponse(status_code=500, content={"detail": "Erro interno"})
