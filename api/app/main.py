"""Ponto de entrada da API (FastAPI). Na Vercel, `app.main:app` atende `/api/*`.

As rotas já carregam o prefixo `/api`: a Vercel repassa o caminho original para o serviço, e o
`uvicorn` local responde nos mesmos endereços.
"""

from fastapi import FastAPI

from app.erros_api import instalar_tratadores
from app.rotas import (
    acesso,
    administracao,
    avisos,
    diagnostico,
    envios,
    push,
    recuperacao,
    saude,
    sessao,
)
from app.sem_cache import SemCache
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
# Por fora de tudo (adicionado depois): vale também para o 500 do registro de erros.
app.add_middleware(SemCache)
# Erros previstos (ErroApi) e de validação viram {"codigo", "mensagem"} (spec do M1, 3.4).
instalar_tratadores(app)
app.include_router(saude.rotas)
app.include_router(diagnostico.rotas)
app.include_router(sessao.rotas)
# Um roteador por épico do M1: cada agente edita só o seu (spec do M1, seção 7).
app.include_router(acesso.rotas)
app.include_router(administracao.rotas)
app.include_router(avisos.rotas)
# M2 (spec do M2, seção 4): envios é comum; push é do épico A e recuperação, do épico B.
app.include_router(envios.rotas)
app.include_router(push.rotas)
app.include_router(recuperacao.rotas)
