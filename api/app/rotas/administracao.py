"""Épico B · Administração (H-07, H-08, H-09, H-11). Pertence ao épico B.

Contrato: `docs/superpowers/specs/m1-contrato.md`, seção 4.3, e o spec do épico
(`docs/superpowers/specs/m1-administracao.md`). Todas as rotas só para o administrador
(`Admin` = `exige_admin`, dúvida 9 do M1); a regra de negócio mora em
`app/servicos/administracao.py`.

`Cache-Control: no-store` vem do middleware comum (`app/sem_cache.py`).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.esquemas.administracao import (
    ConfirmarReset,
    PaginaHistorico,
    PainelAtivacao,
    PapelGerenciavel,
    Situacao,
    UnidadeAdmin,
)
from app.seguranca.dependencias import Admin, Banco, exige_cabecalho_portal
from app.servicos import administracao as servico

# Toda alteração exige `X-Portal: 1` (CSRF, ADR-0005).
rotas = APIRouter(prefix="/api/admin", dependencies=[Depends(exige_cabecalho_portal)])


@rotas.get("/unidades")
def painel(_: Admin, db: Banco, situacao: Situacao = Situacao.todas) -> PainelAtivacao:
    return servico.painel(db, situacao)


@rotas.get("/unidades/{login}")
def unidade(login: str, _: Admin, db: Banco) -> UnidadeAdmin:
    return servico.ficha(db, login)


@rotas.post("/unidades/{login}/resetar")
def resetar(login: str, _confirmacao: ConfirmarReset, logado: Admin, db: Banco) -> UnidadeAdmin:
    servico.resetar(db, login, logado.unidade_id)
    db.commit()
    return servico.ficha(db, login)


@rotas.put("/unidades/{login}/papeis/{papel}")
def dar_papel(login: str, papel: PapelGerenciavel, logado: Admin, db: Banco) -> UnidadeAdmin:
    servico.dar_papel(db, login, papel, logado.unidade_id)
    db.commit()
    return servico.ficha(db, login)


@rotas.delete("/unidades/{login}/papeis/{papel}")
def retirar_papel(login: str, papel: PapelGerenciavel, logado: Admin, db: Banco) -> UnidadeAdmin:
    servico.retirar_papel(db, login, papel, logado.unidade_id)
    db.commit()
    return servico.ficha(db, login)


@rotas.get("/historico")
def historico(
    _: Admin,
    db: Banco,
    antes_de: Annotated[int | None, Query(ge=1)] = None,
    limite: Annotated[int, Query(ge=1, le=100)] = 50,
) -> PaginaHistorico:
    return servico.historico(db, antes_de, limite)
