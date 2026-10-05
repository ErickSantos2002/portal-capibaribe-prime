"""Portão do M1 (issue #18, RNF-13): toda rota `/api/admin/**` recusa quem não é administrador.

As rotas são descobertas na própria aplicação (`app.openapi()`, que lista toda rota publicada,
de qualquer roteador), não numa lista escrita à mão: uma rota nova de administração entra no
teste sozinha. (A partir do FastAPI 0.142, `app.routes` guarda os roteadores incluídos como
objetos internos, sem o caminho de cada rota.) Cada uma é chamada como unidade comum,
Comissão, sessão restrita de primeiro acesso e sem sessão, e nada pode mudar no banco.
"""

import re

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.main import app
from app.rotas import administracao
from testes.conftest import BASE_URL
from testes.test_administracao_apoio import (
    ADMIN,
    COMISSAO,
    COMUM,
    NAO_ATIVADA,
    fotografia,
)

# As rotas do contrato (spec do M1, seção 4.3). O teste exige que existam todas.
ESPERADAS = {
    ("GET", "/api/admin/unidades"),
    ("GET", "/api/admin/unidades/{login}"),
    ("POST", "/api/admin/unidades/{login}/resetar"),
    ("PUT", "/api/admin/unidades/{login}/papeis/{papel}"),
    ("DELETE", "/api/admin/unidades/{login}/papeis/{papel}"),
    ("GET", "/api/admin/historico"),
}
# Valores dos parâmetros de caminho: o alvo é uma unidade comum ativada (a rota faria efeito se
# a permissão falhasse) e o papel mais sensível.
VALORES = {"login": COMUM, "papel": "admin"}
CORPOS = {"resetar": {"confirmo": True}}


def _rotas_admin() -> list[tuple[str, str]]:
    return sorted(
        (metodo.upper(), caminho)
        for caminho, operacoes in app.openapi()["paths"].items()
        if caminho.startswith("/api/admin")
        for metodo in operacoes
    )


ROTAS = _rotas_admin()


def _chamar(cliente: TestClient, metodo: str, caminho: str):
    url = re.sub(r"\{(\w+)\}", lambda m: VALORES[m.group(1)], caminho)
    corpo = CORPOS.get(caminho.rsplit("/", 1)[-1])
    return cliente.request(metodo, url, json=corpo)


def test_todas_as_rotas_do_contrato_existem():
    assert set(ROTAS) == ESPERADAS


def test_nenhuma_rota_admin_fica_fora_da_lista():
    """Rota com `include_in_schema=False` escaparia do `openapi()`: o roteador do épico não tem
    nenhuma, e toda rota dele está em `/api/admin`."""
    for rota in administracao.rotas.routes:
        assert isinstance(rota, APIRoute)
        assert rota.include_in_schema
        assert rota.path.startswith("/api/admin/")


@pytest.mark.parametrize(("metodo", "caminho"), ROTAS)
@pytest.mark.parametrize(
    ("perfil", "status", "codigo"),
    [
        (COMUM, 403, "sem_permissao"),
        (COMISSAO, 403, "sem_permissao"),
        (NAO_ATIVADA, 403, "primeiro_acesso_pendente"),
    ],
    ids=["unidade-comum", "comissao", "sessao-restrita"],
)
def test_toda_rota_admin_recusa(predio, logar, engine_app, metodo, caminho, perfil, status, codigo):
    cliente = logar(perfil)
    antes = fotografia(engine_app)

    resposta = _chamar(cliente, metodo, caminho)

    assert resposta.status_code == status, resposta.text
    assert resposta.json()["codigo"] == codigo
    assert fotografia(engine_app) == antes


@pytest.mark.parametrize(("metodo", "caminho"), ROTAS)
def test_toda_rota_admin_recusa_sem_sessao(predio, cliente, engine_app, metodo, caminho):
    antes = fotografia(engine_app)
    cliente.headers["X-Portal"] = "1"

    resposta = _chamar(cliente, metodo, caminho)

    assert resposta.status_code == 401
    assert resposta.json()["codigo"] == "sem_sessao"
    assert fotografia(engine_app) == antes


@pytest.mark.parametrize(
    ("metodo", "caminho"), [r for r in ROTAS if r[0] != "GET"], ids=lambda v: str(v)
)
def test_alteracao_sem_cabecalho_portal_recusa_ate_o_admin(
    predio, logar, engine_app, metodo, caminho
):
    """CSRF (ADR-0005): mesmo com a sessão do admin, sem `X-Portal: 1` nada muda."""
    admin = logar(ADMIN)
    sem_cabecalho = TestClient(app, base_url=BASE_URL, raise_server_exceptions=False)
    sem_cabecalho.cookies = admin.cookies
    antes = fotografia(engine_app)

    resposta = _chamar(sem_cabecalho, metodo, caminho)

    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "requisicao_recusada"
    assert fotografia(engine_app) == antes


def test_comissao_perde_o_acesso_e_admin_entra(predio, logar):
    """Controle positivo: a mesma rota que recusa a Comissão atende o admin."""
    assert logar(COMISSAO).get("/api/admin/unidades").status_code == 403
    assert logar(ADMIN).get("/api/admin/unidades").status_code == 200
