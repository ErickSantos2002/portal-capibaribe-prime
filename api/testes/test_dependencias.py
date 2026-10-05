"""Dependências de permissão (RNF-13) e CSRF (ADR-0005), num app de teste com uma rota por regra."""

from datetime import timedelta

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.erros_api import instalar_tratadores
from app.modelos import Papel, Sessao, Unidade, UnidadePapel
from app.seguranca.dependencias import (
    Admin,
    Gestao,
    SessaoQualquer,
    UnidadeLogada,
    exige_cabecalho_portal,
)
from app.seguranca.sessoes import NOME_COOKIE, criar_sessao
from testes.conftest import ADMIN, BASE_URL, CABECALHO_PORTAL, COMISSAO, COMUM, NAO_ATIVADA


def _app() -> FastAPI:
    app = FastAPI()
    instalar_tratadores(app)
    rotas = APIRouter(dependencies=[Depends(exige_cabecalho_portal)])

    @rotas.get("/qualquer")
    def qualquer(logado: SessaoQualquer):
        return {"login": logado.login, "restrita": logado.precisa_trocar_senha}

    @rotas.get("/unidade")
    def unidade(logado: UnidadeLogada):
        return {
            "login": logado.login,
            "bloco": logado.bloco,
            "apartamento": logado.apartamento,
            "papeis": sorted(logado.papeis),
            "gestao": logado.gestao,
            "admin": logado.admin,
        }

    @rotas.get("/gestao")
    def gestao(logado: Gestao):
        return {"ok": True}

    @rotas.get("/admin")
    def admin(logado: Admin):
        return {"ok": True}

    @rotas.post("/altera")
    def altera():
        return {"ok": True}

    app.include_router(rotas)
    return app


@pytest.fixture
def entrar(cliente, engine_app, predio):
    """`entrar("1203")` → cliente do app de teste com a sessão da unidade."""
    app = _app()

    def _entrar(login: str | None, cabecalho: bool = True) -> TestClient:
        c = TestClient(
            app,
            base_url=BASE_URL,
            headers=CABECALHO_PORTAL if cabecalho else {},
            raise_server_exceptions=False,
        )
        if login:
            with Session(engine_app) as db:
                token = criar_sessao(db, predio[login], None)
                db.commit()
            c.cookies.set(NOME_COOKIE, token)
        return c

    return _entrar


def test_sem_cookie_e_401(entrar):
    resposta = entrar(None).get("/qualquer")
    assert resposta.status_code == 401
    assert resposta.json() == {
        "codigo": "sem_sessao",
        "mensagem": "Entre de novo com o bloco, o apartamento e a senha.",
    }


def test_cookie_inventado_e_401(entrar):
    c = entrar(None)
    c.cookies.set(NOME_COOKIE, "inventado")
    assert c.get("/qualquer").status_code == 401


def test_sessao_restrita_so_passa_em_sessao_qualquer(entrar):
    c = entrar(NAO_ATIVADA)
    assert c.get("/qualquer").json() == {"login": NAO_ATIVADA, "restrita": True}
    resposta = c.get("/unidade")
    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "primeiro_acesso_pendente"


def test_unidade_logada(entrar):
    assert entrar(COMUM).get("/unidade").json() == {
        "login": COMUM,
        "bloco": 1,
        "apartamento": "203",
        "papeis": [],
        "gestao": False,
        "admin": False,
    }


@pytest.mark.parametrize(
    ("login", "gestao", "admin"),
    [(COMUM, 403, 403), (COMISSAO, 200, 403), (ADMIN, 200, 200)],
)
def test_permissoes_por_papel(entrar, login, gestao, admin):
    c = entrar(login)
    assert c.get("/gestao").status_code == gestao
    assert c.get("/admin").status_code == admin
    if gestao == 403:
        assert c.get("/gestao").json()["codigo"] == "sem_permissao"


def test_papel_retirado_vale_na_hora(entrar, engine_app, predio):
    c = entrar(COMISSAO)
    assert c.get("/gestao").status_code == 200
    with Session(engine_app) as db:
        db.execute(
            update(UnidadePapel)
            .where(UnidadePapel.unidade_id == predio[COMISSAO])
            .values(retirado_em=func.now())
        )
        db.commit()
    assert c.get("/gestao").status_code == 403


def test_papel_concedido_vale_na_hora(entrar, engine_app, predio):
    c = entrar(COMUM)
    assert c.get("/gestao").status_code == 403
    with Session(engine_app) as db:
        db.add(UnidadePapel(unidade_id=predio[COMUM], papel=Papel.comissao))
        db.commit()
    assert c.get("/unidade").json()["papeis"] == ["comissao"]
    assert c.get("/gestao").status_code == 200


def test_unidade_desativada_perde_a_sessao(entrar, engine_app, predio):
    c = entrar(COMUM)
    with Session(engine_app) as db:
        db.execute(update(Unidade).where(Unidade.id == predio[COMUM]).values(ativa=False))
        db.commit()
    assert c.get("/qualquer").status_code == 401


def test_sessao_de_terceiro_nao_vira_completa_no_primeiro_acesso(entrar, engine_app, predio):
    # Alguém entra com mudar123 antes do morador e guarda o cookie (sessão restrita).
    terceiro = entrar(NAO_ATIVADA)
    assert terceiro.get("/qualquer").status_code == 200
    # O morador conclui o primeiro acesso (senha nova), mesmo sem a rota encerrar nada.
    with Session(engine_app) as db:
        db.execute(
            update(Unidade)
            .where(Unidade.id == predio[NAO_ATIVADA])
            .values(
                senha_hash="hash-da-senha-nova",
                precisa_trocar_senha=False,
                ativada_em=func.now(),
                responsavel_nome="Morador (fictício)",
                celular="81900000009",
            )
        )
        db.commit()
    # O cookie antigo não vale mais nada: nem restrito, nem completo.
    assert terceiro.get("/qualquer").status_code == 401
    assert terceiro.get("/unidade").status_code == 401


def test_sessao_vencida_e_401(entrar, engine_app):
    c = entrar(COMUM)
    with Session(engine_app) as db:
        db.execute(update(Sessao).values(ultimo_uso_em=func.now() - timedelta(days=181)))
        db.commit()
    assert c.get("/qualquer").status_code == 401


def test_renovar_regrava_o_cookie(entrar, engine_app):
    c = entrar(COMUM)
    assert "set-cookie" not in c.get("/qualquer").headers
    with Session(engine_app) as db:
        db.execute(update(Sessao).values(ultimo_uso_em=func.now() - timedelta(hours=2)))
        db.commit()
    resposta = c.get("/qualquer")
    assert resposta.headers["set-cookie"].startswith(f"{NOME_COOKIE}=")
    with Session(engine_app) as db:
        uso = db.scalars(select(Sessao.ultimo_uso_em)).one()
        assert db.scalars(select(func.now())).one() - uso < timedelta(minutes=1)


# --- CSRF ------------------------------------------------------------------------------------


@pytest.mark.parametrize("cabecalho", [None, "0", "sim", ""])
def test_alteracao_sem_cabecalho_do_portal_e_recusada(entrar, cabecalho):
    c = entrar(COMUM, cabecalho=False)
    headers = {} if cabecalho is None else {"X-Portal": cabecalho}
    resposta = c.post("/altera", headers=headers)
    assert resposta.status_code == 403
    assert resposta.json() == {
        "codigo": "requisicao_recusada",
        "mensagem": "Requisição recusada. Recarregue a página e tente de novo.",
    }


def test_alteracao_com_cabecalho_passa(entrar):
    assert entrar(COMUM).post("/altera").status_code == 200


def test_leitura_nao_exige_cabecalho(entrar):
    assert entrar(COMUM, cabecalho=False).get("/unidade").status_code == 200
