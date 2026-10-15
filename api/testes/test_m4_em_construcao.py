"""Rotas dos épicos do M4 que ainda respondem 501 `em_construcao` (spec do M4, seção 3).

Cada épico, ao implementar, troca o corpo das funções dele e **apaga a própria seção** deste
arquivo. O que vale antes e depois dos épicos (sessão, permissão, CSRF, validação) está em
`test_m4_rotas.py`.
"""

import pytest

from testes.conftest import COMISSAO, COMUM

pytestmark = pytest.mark.usefixtures("predio")

EM_CONSTRUCAO = {
    "codigo": "em_construcao",
    "mensagem": "Esta parte do Portal ainda está sendo feita.",
}


def _501(resposta) -> None:
    assert resposta.status_code == 501, resposta.text
    assert resposta.json() == EM_CONSTRUCAO


# --- épico B · votar e resultado ---------------------------------------------------------------


@pytest.mark.parametrize("caminho", ["/api/enquetes", "/api/enquetes/1"])
def test_b_lista_e_enquete(logar, caminho):
    _501(logar(COMUM).get(caminho))


def test_b_votar(logar):
    _501(logar(COMUM).put("/api/enquetes/1/voto", json={"opcoes": [1]}))
    _501(logar(COMISSAO).put("/api/enquetes/1/voto", json={"opcoes": [1, 2]}))


def test_b_votantes(logar):
    _501(logar(COMISSAO).get("/api/enquetes/1/votantes"))
