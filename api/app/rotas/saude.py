from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.banco import obter_sessao
from app.modelos import Unidade

rotas = APIRouter()


@rotas.get("/api/saude")
def saude(sessao: Annotated[Session, Depends(obter_sessao)]) -> dict:
    """Prova de vida de ponta a ponta: a API responde e o banco também (320 após a carga)."""
    unidades = sessao.scalar(select(func.count()).select_from(Unidade))
    return {"status": "ok", "unidades": unidades}
