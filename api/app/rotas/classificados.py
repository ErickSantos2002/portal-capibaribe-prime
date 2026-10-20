"""Classificados entre vizinhos: o que o morador faz (spec de 20/10/2026, seções 3 e 8).

Esquemas em `app/esquemas/classificados.py`; regras em `app/servicos/classificados.py` e
`classificados_fotos.py`. A moderação e a faxina estão em `classificados_gestao.py`, com o mesmo
prefixo; os caminhos não se cruzam. As rotas fixas vêm antes de `/{anuncio_id}`.

- `POST /api/classificados/fotos`                 → 201 `FotoAutorizada`
- `POST /api/classificados/fotos/{id}/confirmar`  → `FotoEnviada`

Só unidade logada e com o primeiro acesso concluído (`UnidadeLogada`).
"""

from fastapi import APIRouter, Depends

from app.esquemas.classificados import FotoAutorizada, FotoEnviada, PedirFoto
from app.esquemas.comum import IdBanco
from app.seguranca.dependencias import Banco, UnidadeLogada, exige_cabecalho_portal
from app.servicos import classificados_fotos as fotos
from app.servicos.armazenamento import Armazenado

# Toda alteração exige `X-Portal: 1` (CSRF, ADR-0005).
rotas = APIRouter(prefix="/api/classificados", dependencies=[Depends(exige_cabecalho_portal)])


@rotas.post("/fotos", status_code=201)
def pedir_foto(
    dados: PedirFoto, logado: UnidadeLogada, db: Banco, bucket: Armazenado
) -> FotoAutorizada:
    return fotos.pedir(db, logado, dados, bucket)


@rotas.post("/fotos/{foto_id}/confirmar")
def confirmar_foto(
    foto_id: IdBanco, logado: UnidadeLogada, db: Banco, bucket: Armazenado
) -> FotoEnviada:
    return fotos.confirmar(db, logado, foto_id, bucket)
