"""Classificados: a moderação e a faxina (spec de 20/10/2026, seções 3.2, 6 e 9). Mesmo prefixo
do roteador do morador (`classificados.py`); os caminhos não se cruzam. Incluído **antes** dele
no `main.py`, para `/faxina` e `/categorias` não caírem em `/{anuncio_id}`.

- `GET  /api/classificados/faxina`              → `ResultadoDaFaxina` (Vercel Cron, segredo)
- `POST /api/classificados/{id}/esconder`       → 204 (`Gestao`)
- `POST /api/classificados/avisos/{id}/resolver` → 204 (`Gestao`)
- `POST /api/classificados/categorias`          → 201 `CategoriaClassificado` (`Admin`)
- `PUT  /api/classificados/categorias/{id}`     → `CategoriaClassificado` (`Admin`)

A faxina roda pelo Vercel Cron uma vez por dia (`vercel.json`, ADR-0012). A Vercel manda
`Authorization: Bearer <CRON_SECRET>`; sem a variável `CRON_SECRET`, a rota responde 503 e não
faz nada; com outro segredo, 401. A comparação é em tempo constante.
"""

import hmac
import os
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response

from app.erros_api import ErroApi
from app.esquemas.classificados import CategoriaClassificado, ResultadoDaFaxina
from app.esquemas.comum import IdBanco
from app.esquemas.indicacoes import NovaCategoria, RenomearCategoria
from app.seguranca.dependencias import Admin, Banco, Gestao, exige_cabecalho_portal
from app.servicos import classificados_gestao as servico
from app.servicos.armazenamento import Armazenado

rotas = APIRouter(prefix="/api/classificados", dependencies=[Depends(exige_cabecalho_portal)])


def _conferir_cron(autorizacao: str | None) -> None:
    esperado = os.environ.get("CRON_SECRET", "").strip()
    if not esperado:
        raise ErroApi(503, "faxina_desligada", "A faxina dos classificados não está ligada.")
    recebido = (autorizacao or "").encode()
    if not hmac.compare_digest(recebido, f"Bearer {esperado}".encode()):
        raise ErroApi(401, "sem_permissao", "Só o agendador da Vercel roda a faxina.")


@rotas.get("/faxina", include_in_schema=False)
def faxina(
    db: Banco,
    bucket: Armazenado,
    authorization: Annotated[str | None, Header()] = None,
) -> ResultadoDaFaxina:
    _conferir_cron(authorization)
    return servico.faxinar(db, bucket)


@rotas.post("/categorias", status_code=201)
def criar_categoria(dados: NovaCategoria, logado: Admin, db: Banco) -> CategoriaClassificado:
    return servico.criar_categoria(db, logado, dados.nome)


@rotas.put("/categorias/{categoria_id}")
def renomear_categoria(
    categoria_id: IdBanco, dados: RenomearCategoria, logado: Admin, db: Banco
) -> CategoriaClassificado:
    return servico.renomear_categoria(db, logado, categoria_id, dados.nome)


@rotas.post("/avisos/{aviso_id}/resolver", status_code=204)
def resolver_aviso(aviso_id: IdBanco, logado: Gestao, db: Banco) -> Response:
    servico.resolver_aviso(db, logado, aviso_id)
    return Response(status_code=204)


@rotas.post("/{anuncio_id}/esconder", status_code=204)
def esconder(anuncio_id: IdBanco, logado: Gestao, db: Banco) -> Response:
    servico.esconder(db, logado, anuncio_id)
    return Response(status_code=204)
