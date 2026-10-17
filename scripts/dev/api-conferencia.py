"""A API do ambiente de conferência (scripts/dev/ambiente-conferencia.sh), com um bucket de
arquivos de mentira, em memória, para as telas de documento e de anexo aparecerem sem o R2.

É a mesma `app.main:app` de produção, com uma troca só, a mesma dos testes da API
(`api/testes/conftest.py`): a dependência `obter_armazenamento` passa a devolver um
`ArmazenamentoFalso`. Os links que ele assina apontam para um R2 fictício
(`https://conferencia.r2.cloudflarestorage.com`), um endereço que a CSP de produção libera,
então o navegador da conferência pede o arquivo como pediria ao R2 de verdade; o
`conferir-letra.mjs` intercepta esse endereço (rota do Playwright) e busca o conteúdo aqui, em
`/api/_conferencia/bucket/<caminho>` (GET lê, PUT faz o papel do envio do navegador).

Nunca vai para produção: mora em scripts/dev, e só roda com PORTAL_AMBIENTE=local. Uso, de
dentro de `api/` (o ambiente-conferencia.sh já faz isso):

    PORTAL_AMBIENTE=local uv run --frozen python ../scripts/dev/api-conferencia.py --port 8170
"""

import argparse
import os
import sys

import uvicorn
from fastapi import Request, Response

from app.main import app
from app.servicos.armazenamento import ArmazenamentoFalso, obter_armazenamento


class BucketDaConferencia(ArmazenamentoFalso):
    BASE = "https://conferencia.r2.cloudflarestorage.com/portal-arquivos"


def montar() -> BucketDaConferencia:
    if os.environ.get("PORTAL_AMBIENTE") != "local":
        sys.exit("api-conferencia: só com PORTAL_AMBIENTE=local (dados fictícios, nunca produção)")
    bucket = BucketDaConferencia()
    app.dependency_overrides[obter_armazenamento] = lambda: bucket

    # O "R2" de mentira: o caminho é o mesmo do link assinado, sem a consulta.
    @app.get("/api/_conferencia/bucket/{caminho:path}")
    def ler(caminho: str) -> Response:
        objeto = bucket.objetos.get(caminho)
        if objeto is None:
            return Response(status_code=404)
        conteudo, tipo = objeto
        return Response(content=conteudo, media_type=tipo)

    @app.put("/api/_conferencia/bucket/envios/{chave}")
    async def receber(chave: str, pedido: Request) -> Response:
        tipo = pedido.headers.get("content-type", "application/octet-stream")
        bucket.receber(chave, await pedido.body(), tipo)
        return Response(status_code=200)

    return bucket


def main() -> None:
    argumentos = argparse.ArgumentParser()
    argumentos.add_argument("--port", type=int, required=True)
    porta = argumentos.parse_args().port
    montar()
    uvicorn.run(app, host="127.0.0.1", port=porta, log_level="warning")


if __name__ == "__main__":
    main()
