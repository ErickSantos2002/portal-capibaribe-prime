"""Rotas dos épicos do M4 que ainda respondem 501 `em_construcao` (spec do M4, seção 3).

Cada épico, ao implementar, troca o corpo das funções dele e **apaga a própria seção** deste
arquivo. O que vale antes e depois dos épicos (sessão, permissão, CSRF, validação) está em
`test_m4_rotas.py`.
"""

import pytest

from testes.conftest import ADMIN, COMISSAO
from testes.test_m4_rotas import EDITAR_ENQUETE, NOVA_ENQUETE

pytestmark = pytest.mark.usefixtures("predio")

EM_CONSTRUCAO = {
    "codigo": "em_construcao",
    "mensagem": "Esta parte do Portal ainda está sendo feita.",
}


def _501(resposta) -> None:
    assert resposta.status_code == 501, resposta.text
    assert resposta.json() == EM_CONSTRUCAO


# --- épico A · criar e gerir -------------------------------------------------------------------


def test_a_criar_enquete(logar):
    comissao = logar(COMISSAO)
    _501(comissao.post("/api/enquetes", json=NOVA_ENQUETE))
    _501(comissao.post("/api/enquetes", json={**NOVA_ENQUETE, "para_todos": False, "blocos": [1]}))


def test_a_editar_enquete(logar):
    _501(logar(ADMIN).put("/api/enquetes/1", json=EDITAR_ENQUETE))
