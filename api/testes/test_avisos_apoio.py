"""Apoio dos testes do épico C (não tem testes; o nome segue a posse de arquivos do épico).

Personagens do prédio de teste (`predio`, em `conftest.py`): 1101 admin (Bloco 1), 2304
Comissão (Bloco 2), 1203 comum (Bloco 1), 4203 não ativada (Bloco 4). `ativar("2101")` cria um
morador comum do Bloco 2.
"""

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session

from testes.conftest import ADMIN, COMISSAO, COMUM, NAO_ATIVADA

__all__ = ["ADMIN", "COMISSAO", "COMUM", "NAO_ATIVADA", "ativar", "historico", "publicar"]


def publicar(
    cliente: TestClient,
    *,
    titulo: str = "Vistoria da obra",
    texto: str = "A construtora liberou uma visita.",
    para_todos: bool = True,
    blocos: list[int] | None = None,
    fixado: bool = False,
) -> dict[str, Any]:
    """Publica pela API e devolve o `AvisoCompleto`."""
    corpo: dict[str, Any] = {"titulo": titulo, "texto": texto, "para_todos": para_todos}
    if blocos is not None:
        corpo["blocos"] = blocos
    if fixado:
        corpo["fixado"] = True
    resposta = cliente.post("/api/avisos", json=corpo)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def ativar(engine: Engine, login: str) -> int:
    """Faz o "primeiro acesso" de uma unidade direto no banco (sem a rota do épico A)."""
    from app.modelos import Unidade

    with Session(engine) as db:
        unidade = db.scalars(select(Unidade).where(Unidade.login == login)).one()
        unidade.precisa_trocar_senha = False
        unidade.ativada_em = func.now()
        unidade.responsavel_nome = f"Responsável {login} (fictício)"
        unidade.celular = "81900009999"
        db.commit()
        return unidade.id


def historico(engine: Engine, acao: str) -> list[dict[str, Any]]:
    with engine.connect() as con:
        linhas = con.execute(
            text(
                "select unidade_id, entidade, entidade_id, detalhes from historico"
                " where acao = :a order by id"
            ),
            {"a": acao},
        ).mappings()
        return [dict(linha) for linha in linhas]
