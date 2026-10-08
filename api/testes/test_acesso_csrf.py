"""Épico A · Toda rota que altera dados recusa requisição sem `X-Portal: 1` (CSRF, ADR-0005).

A lista é escrita à mão e conferida contra `app.openapi()["paths"]` (no FastAPI 0.142,
`app.routes` não enxerga as rotas dos roteadores incluídos): rota nova do épico que altera
dados e não está aqui faz o primeiro teste falhar.
"""

import pytest

from app.main import app
from app.seguranca.sessoes import NOME_COOKIE
from testes.conftest import COMUM

ALTERAM = {
    ("POST", "/api/acesso/entrar"),
    ("POST", "/api/acesso/primeiro-acesso"),
    ("PUT", "/api/minha-unidade/dados"),
    ("PUT", "/api/minha-unidade/senha"),
    ("PUT", "/api/minha-unidade/avisos-por-email"),
    ("DELETE", "/api/minha-unidade/aparelhos/{sessao_id}"),
    ("POST", "/api/minha-unidade/apagar-dados"),
}
DO_EPICO = ("/api/acesso/entrar", "/api/acesso/primeiro-acesso", "/api/minha-unidade")


def test_lista_cobre_todas_as_rotas_do_epico_que_alteram_dados():
    encontradas = {
        (metodo.upper(), caminho)
        for caminho, metodos in app.openapi()["paths"].items()
        if caminho.startswith(DO_EPICO)
        for metodo in metodos
        if metodo.upper() not in {"GET", "HEAD", "OPTIONS"}
    }
    assert encontradas == ALTERAM


@pytest.mark.parametrize(("metodo", "caminho"), sorted(ALTERAM))
def test_sem_x_portal_e_recusado_mesmo_com_sessao(cliente, logar, predio, metodo, caminho):
    cliente.cookies.set(NOME_COOKIE, logar(COMUM).cookies[NOME_COOKIE])
    resposta = cliente.request(metodo, caminho.replace("{sessao_id}", "1"), json={})
    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "requisicao_recusada"
