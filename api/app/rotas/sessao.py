"""Rotas comuns de sessão (spec do M1, seção 4.1): quem sou eu e sair.

Ficam fora do épico A porque a casca do front depende delas para escolher rotas e menu. Entrar
e primeiro acesso são do épico A (`app/rotas/acesso.py`).
"""

from fastapi import APIRouter, Depends, Request, Response

from app.esquemas.comum import Eu, UnidadeRef
from app.seguranca.dependencias import Banco, SessaoQualquer, exige_cabecalho_portal
from app.seguranca.sessoes import NOME_COOKIE, apagar_cookie, buscar_sessao, encerrar_sessao

rotas = APIRouter(dependencies=[Depends(exige_cabecalho_portal)])


@rotas.get("/api/acesso/eu")
def eu(logado: SessaoQualquer) -> Eu:
    return Eu(
        unidade=UnidadeRef.de_login(logado.login),
        papeis=sorted(logado.papeis),
        gestao=logado.gestao,
        admin=logado.admin,
        precisa_trocar_senha=logado.precisa_trocar_senha,
    )


@rotas.post("/api/acesso/sair", status_code=204)
def sair(request: Request, resposta: Response, db: Banco) -> None:
    """Encerra a sessão deste aparelho. Sem sessão válida também responde 204."""
    sessao = buscar_sessao(db, request.cookies.get(NOME_COOKIE))
    if sessao is not None:
        encerrar_sessao(db, sessao.id)
        db.commit()
    apagar_cookie(resposta)
