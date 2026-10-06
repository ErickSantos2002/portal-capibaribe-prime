"""Épico B · Administração (H-07, H-08, H-09, H-11). Pertence ao épico B.

Contrato: `docs/superpowers/specs/m1-contrato.md`, seção 4.3, e o spec do épico
(`docs/superpowers/specs/m1-administracao.md`). O painel e a ficha são lidos pela gestão
(`Gestao` = `exige_gestao`: a Comissão vê os contatos das unidades, decisão do Erick em
06/10/2026); voltar para a senha inicial, papéis e histórico são só do administrador (`Admin`).
A regra de negócio mora em `app/servicos/administracao.py`.

`Cache-Control: no-store` vem do middleware comum (`app/sem_cache.py`).
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from psycopg import errors as erros_pg
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.erros_api import ErroApi
from app.esquemas.administracao import (
    ConfirmarReset,
    PaginaHistorico,
    PainelAtivacao,
    PapelGerenciavel,
    Situacao,
    UnidadeAdmin,
)
from app.seguranca.dependencias import Admin, Banco, Gestao, exige_cabecalho_portal
from app.servicos import administracao as servico

# Toda alteração exige `X-Portal: 1` (CSRF, ADR-0005).
rotas = APIRouter(prefix="/api/admin", dependencies=[Depends(exige_cabecalho_portal)])

_CONCORRENCIA = (erros_pg.DeadlockDetected, erros_pg.SerializationFailure)


@contextmanager
def _um_de_cada_vez(db: Session) -> Iterator[None]:
    """Revisão do M1, C5: dois admins mexendo nos papéis um do outro ao mesmo tempo podem se
    travar (o trigger do último admin trava as linhas de admin); o Postgres derruba um com
    40P01. Esse, e a falha de serialização (40001), viram 409 "tente de novo", não 500."""
    try:
        yield
    except DBAPIError as erro:
        if not isinstance(erro.orig, _CONCORRENCIA):
            raise
        db.rollback()
        raise ErroApi(
            409,
            "tente_de_novo",
            "Outra pessoa mexeu nesta unidade ao mesmo tempo. Tente de novo.",
        ) from erro


@rotas.get("/unidades")
def painel(_: Gestao, db: Banco, situacao: Situacao = Situacao.todas) -> PainelAtivacao:
    return servico.painel(db, situacao)


@rotas.get("/unidades/{login}")
def unidade(login: str, _: Gestao, db: Banco) -> UnidadeAdmin:
    return servico.ficha(db, login)


@rotas.post("/unidades/{login}/resetar")
def resetar(login: str, _confirmacao: ConfirmarReset, logado: Admin, db: Banco) -> UnidadeAdmin:
    with _um_de_cada_vez(db):
        servico.resetar(db, login, logado.unidade_id)
        db.commit()
    return servico.ficha(db, login)


@rotas.put("/unidades/{login}/papeis/{papel}")
def dar_papel(login: str, papel: PapelGerenciavel, logado: Admin, db: Banco) -> UnidadeAdmin:
    with _um_de_cada_vez(db):
        servico.dar_papel(db, login, papel, logado.unidade_id)
        db.commit()
    return servico.ficha(db, login)


@rotas.delete("/unidades/{login}/papeis/{papel}")
def retirar_papel(login: str, papel: PapelGerenciavel, logado: Admin, db: Banco) -> UnidadeAdmin:
    with _um_de_cada_vez(db):
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
