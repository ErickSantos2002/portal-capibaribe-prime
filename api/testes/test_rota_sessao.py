"""Rotas comuns de sessão: `GET /api/acesso/eu` e `POST /api/acesso/sair` (spec do M1, 4.1)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modelos import Sessao
from app.seguranca.sessoes import NOME_COOKIE
from testes.conftest import ADMIN, CABECALHO_PORTAL, COMISSAO, COMUM, NAO_ATIVADA


def test_eu_sem_sessao(cliente):
    resposta = cliente.get("/api/acesso/eu")
    assert resposta.status_code == 401
    assert resposta.json()["codigo"] == "sem_sessao"


def test_eu_unidade_comum(logar, predio):
    resposta = logar(COMUM).get("/api/acesso/eu")
    assert resposta.status_code == 200
    assert resposta.headers["cache-control"] == "no-store"
    assert resposta.json() == {
        "unidade": {"login": COMUM, "bloco": 1, "apartamento": "203"},
        "papeis": [],
        "gestao": False,
        "admin": False,
        "precisa_trocar_senha": False,
    }


def test_eu_gestao_e_admin(logar, predio):
    assert logar(COMISSAO).get("/api/acesso/eu").json()["papeis"] == ["comissao"]
    eu = logar(ADMIN).get("/api/acesso/eu").json()
    assert (eu["papeis"], eu["gestao"], eu["admin"]) == (["admin"], True, True)


def test_eu_com_sessao_restrita(logar, predio):
    eu = logar(NAO_ATIVADA).get("/api/acesso/eu").json()
    assert eu["precisa_trocar_senha"] is True
    assert eu["unidade"] == {"login": NAO_ATIVADA, "bloco": 4, "apartamento": "203"}


def test_eu_nao_traz_dado_pessoal(logar, predio):
    texto = logar(COMUM).get("/api/acesso/eu").text
    assert "Responsável" not in texto and "81900" not in texto


def test_sair_encerra_a_sessao_e_apaga_o_cookie(logar, predio, engine_app):
    c = logar(COMUM)
    resposta = c.post("/api/acesso/sair")
    assert resposta.status_code == 204
    assert resposta.headers["set-cookie"].startswith(f"{NOME_COOKIE}=")
    assert "Max-Age=0" in resposta.headers["set-cookie"]
    with Session(engine_app) as db:
        assert db.scalars(select(Sessao.encerrada_em)).one() is not None
    assert c.get("/api/acesso/eu").status_code == 401


def test_sair_sem_sessao_tambem_e_204(cliente):
    assert cliente.post("/api/acesso/sair", headers=CABECALHO_PORTAL).status_code == 204


def test_sair_exige_o_cabecalho_do_portal(cliente):
    assert cliente.post("/api/acesso/sair").status_code == 403
