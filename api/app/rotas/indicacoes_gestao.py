"""Indicações de serviços: a moderação (spec de 18/10/2026, seções 3.2, 4 e 8). Mesmo prefixo
do roteador do morador (`indicacoes.py`); os caminhos não se cruzam.

- `POST /api/indicacoes/{id}/esconder`            → 204 (`Gestao`)
- `POST /api/indicacoes/opinioes/{id}/esconder`   → 204 (`Gestao`)
- `POST /api/indicacoes/avisos/{id}/resolver`     → 204 (`Gestao`)
- `POST /api/indicacoes/categorias`               → 201 `CategoriaServico` (`Admin`)
- `PUT  /api/indicacoes/categorias/{id}`          → `CategoriaServico` (`Admin`)
"""

from fastapi import APIRouter, Depends, Response

from app.esquemas.comum import IdBanco
from app.esquemas.indicacoes import CategoriaServico, NovaCategoria, RenomearCategoria
from app.seguranca.dependencias import Admin, Banco, Gestao, exige_cabecalho_portal
from app.servicos import indicacoes_gestao as servico

rotas = APIRouter(prefix="/api/indicacoes", dependencies=[Depends(exige_cabecalho_portal)])


@rotas.post("/categorias", status_code=201)
def criar_categoria(dados: NovaCategoria, logado: Admin, db: Banco) -> CategoriaServico:
    return servico.criar_categoria(db, logado, dados.nome)


@rotas.put("/categorias/{categoria_id}")
def renomear_categoria(
    categoria_id: IdBanco, dados: RenomearCategoria, logado: Admin, db: Banco
) -> CategoriaServico:
    return servico.renomear_categoria(db, logado, categoria_id, dados.nome)


@rotas.post("/opinioes/{opiniao_id}/esconder", status_code=204)
def esconder_opiniao(opiniao_id: IdBanco, logado: Gestao, db: Banco) -> Response:
    servico.esconder_opiniao(db, logado, opiniao_id)
    return Response(status_code=204)


@rotas.post("/avisos/{aviso_id}/resolver", status_code=204)
def resolver_aviso(aviso_id: IdBanco, logado: Gestao, db: Banco) -> Response:
    servico.resolver_aviso(db, logado, aviso_id)
    return Response(status_code=204)


@rotas.post("/{prestador_id}/esconder", status_code=204)
def esconder_prestador(prestador_id: IdBanco, logado: Gestao, db: Banco) -> Response:
    servico.esconder_prestador(db, logado, prestador_id)
    return Response(status_code=204)
