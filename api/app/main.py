"""Ponto de entrada da API (FastAPI). Na Vercel, `app.main:app` atende `/api/*`.

As rotas já carregam o prefixo `/api`: a Vercel repassa o caminho original para o serviço, e o
`uvicorn` local responde nos mesmos endereços.
"""

from fastapi import FastAPI

from app.erros_api import instalar_tratadores
from app.rotas import diagnostico, saude, sessao
from app.servicos.erros import RegistroDeErros

# Documentação interativa desligada: o contrato sai de `app.openapi()` quando for preciso
# gerar os tipos do front, sem expor /docs em produção.
app = FastAPI(
    title="Portal Capibaribe Prime",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
# Exceção não tratada: grava em `erro`, loga sem dado pessoal e responde 500 sem relançar.
app.add_middleware(RegistroDeErros)
# Erros previstos (ErroApi) e de validação viram {"codigo", "mensagem"} (spec do M1, 3.4).
instalar_tratadores(app)
app.include_router(saude.rotas)
app.include_router(diagnostico.rotas)
app.include_router(sessao.rotas)
