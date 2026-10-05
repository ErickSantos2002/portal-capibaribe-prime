"""Épico A · Acesso (H-01, H-02, H-03, H-06). Pertence ao épico A.

Contrato: `docs/superpowers/specs/m1-contrato.md`, seção 4.2; spec do épico:
`docs/superpowers/specs/m1-acesso.md`. As rotas são finas: chamam `app.servicos.acesso`, fazem
o commit e gravam ou apagam o cookie.

`GET /api/acesso/eu` e `POST /api/acesso/sair` são comuns e estão em `app/rotas/sessao.py`.
"""

from fastapi import APIRouter, Depends, Request, Response

from app.esquemas.acesso import Entrar
from app.esquemas.comum import Eu
from app.seguranca.dependencias import Banco, exige_cabecalho_portal
from app.seguranca.sessoes import gravar_cookie
from app.servicos import acesso

# Toda alteração exige `X-Portal: 1` (CSRF, ADR-0005).
rotas = APIRouter(dependencies=[Depends(exige_cabecalho_portal)])


def _sem_cache(resposta: Response) -> None:
    resposta.headers["Cache-Control"] = "no-store"


@rotas.post("/api/acesso/entrar")
def entrar(dados: Entrar, request: Request, resposta: Response, db: Banco) -> Eu:
    try:
        eu, token = acesso.entrar(db, dados.login, dados.senha, request.headers.get("user-agent"))
    except acesso.ErroEntrar:
        # A tentativa errada e o bloqueio valem mesmo com a resposta de erro (H-03).
        db.commit()
        raise
    db.commit()
    gravar_cookie(resposta, token)
    _sem_cache(resposta)
    return eu
