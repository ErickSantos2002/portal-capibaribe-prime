"""Toda resposta da API sai com `Cache-Control: no-store` (revisão do M1, C6).

Mural, aviso e contagem de não lidos mostram o que a unidade logada pode ver; um cache (do
navegador ou de um proxy) não pode guardar isso. Antes, só acesso e administração marcavam.
"""

import pytest

from testes.conftest import ADMIN, COMUM
from testes.test_avisos_apoio import publicar

pytestmark = pytest.mark.usefixtures("predio")


def _caminhos_get() -> list[str]:
    from app.main import app

    return sorted(
        caminho
        for caminho, operacoes in app.openapi()["paths"].items()
        if caminho.startswith("/api/") and "get" in operacoes
    )


def test_todo_get_da_api_sai_sem_cache(logar):
    admin = logar(ADMIN)
    aviso = publicar(admin)
    substituir = {"{aviso_id}": str(aviso["id"]), "{login}": COMUM}
    caminhos = _caminhos_get()
    assert "/api/avisos" in caminhos and "/api/avisos/{aviso_id}" in caminhos
    for caminho in caminhos:
        for marcador, valor in substituir.items():
            caminho = caminho.replace(marcador, valor)
        resposta = admin.get(caminho)
        assert resposta.status_code == 200, (caminho, resposta.text)
        assert resposta.headers.get("cache-control") == "no-store", caminho


@pytest.mark.parametrize(
    ("metodo", "caminho"),
    [
        ("get", "/api/avisos"),  # 401 sem sessão
        ("get", "/api/avisos/999999"),  # 401
        ("post", "/api/acesso/entrar"),  # 403 sem X-Portal
        ("get", "/api/nao-existe"),  # 404 do Starlette
    ],
)
def test_erro_tambem_sai_sem_cache(cliente, metodo, caminho):
    resposta = cliente.request(metodo.upper(), caminho)
    assert resposta.status_code >= 400
    assert resposta.headers.get("cache-control") == "no-store"


def test_aviso_aberto_e_contagem_sem_cache(logar):
    aviso = publicar(logar(ADMIN))
    comum = logar(COMUM)
    for caminho in ("/api/avisos", f"/api/avisos/{aviso['id']}", "/api/avisos/nao-lidos"):
        assert comum.get(caminho).headers.get("cache-control") == "no-store", caminho
