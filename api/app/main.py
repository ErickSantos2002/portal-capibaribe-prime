"""Ponto de entrada da API (FastAPI). Na Vercel, `app.main:app` atende `/api/*`.

As rotas já carregam o prefixo `/api`: a Vercel repassa o caminho original para o serviço, e o
`uvicorn` local responde nos mesmos endereços.
"""

from fastapi import FastAPI

from app.erros_api import instalar_tratadores
from app.rotas import (
    acesso,
    administracao,
    arquivos,
    avisos,
    classificados,
    classificados_gestao,
    diagnostico,
    documentos,
    enquetes,
    enquetes_gestao,
    envios,
    indicacoes,
    indicacoes_gestao,
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
# M3 (spec do M3, seção 5): o envio de arquivo é comum; documentos é do épico A (os anexos, do
# épico B, ficam no roteador de avisos).
app.include_router(arquivos.rotas)
app.include_router(documentos.rotas)
# M4 (spec do M4, seção 3): um roteador por épico, com o mesmo prefixo: votar e resultado (B) e
# criar e gerir (A).
app.include_router(enquetes.rotas)
app.include_router(enquetes_gestao.rotas)
# Indicações de serviços (spec de 18/10/2026): o morador e, depois, a moderação.
app.include_router(indicacoes.rotas)
app.include_router(indicacoes_gestao.rotas)
# Classificados entre vizinhos (spec de 20/10/2026): a moderação e a faxina antes do morador, para
# `/faxina` e `/categorias` não caírem em `/{anuncio_id}`.
app.include_router(classificados_gestao.rotas)
app.include_router(classificados.rotas)
