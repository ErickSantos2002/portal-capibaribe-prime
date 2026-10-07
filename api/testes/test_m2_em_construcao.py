"""Rotas do M2 ainda sem implementação: respondem 501 `em_construcao` (spec do M2, seção 4).

**Temporário.** Cada épico apaga a própria seção quando implementar as rotas dela (e o épico A
tira `/api/notificacoes` de `EM_CONSTRUCAO` em `test_cache.py`). O que precisa continuar valendo
depois (sessão, CSRF, validação, rota pública) está em `test_m2_rotas.py`.
"""

import pytest

from testes.conftest import COMUM
from testes.test_m2_rotas import ROTAS_PUSH

pytestmark = pytest.mark.usefixtures("predio")


def _codigo(resposta) -> tuple[int, str]:
    return resposta.status_code, resposta.json().get("codigo")


# --- épico A · push: apagar ao implementar ----------------------------------------------------


@pytest.mark.parametrize(("metodo", "caminho", "corpo"), ROTAS_PUSH)
def test_push_em_construcao(logar, metodo, caminho, corpo):
    assert _codigo(logar(COMUM).request(metodo, caminho, json=corpo)) == (501, "em_construcao")
