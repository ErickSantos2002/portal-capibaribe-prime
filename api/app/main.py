"""Ponto de entrada da API (FastAPI). Na Vercel, `app.main:app` vira a função de `/api/*`."""

from fastapi import FastAPI

# Documentação interativa desligada: o contrato sai de `app.openapi()` quando for preciso
# gerar os tipos do front, sem expor /docs em produção.
app = FastAPI(
    title="Portal Capibaribe Prime",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
