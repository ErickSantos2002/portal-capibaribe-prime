"""Rotas dos épicos do M3 que ainda respondem 501 `em_construcao` (spec do M3, seção 5).

Cada épico, ao implementar, troca o corpo da função e **apaga a própria seção** deste arquivo
(e tira as rotas dele de `EM_CONSTRUCAO` em `test_cache.py`). O que vale antes e depois dos
épicos (sessão, permissão, CSRF, validação) está em `test_m3_rotas.py`.
"""

import pytest

from testes.conftest import ADMIN, COMISSAO, COMUM
from testes.test_avisos_apoio import publicar
from testes.test_m3_rotas import NOVO_DOCUMENTO

pytestmark = pytest.mark.usefixtures("predio", "armazenamento")

EM_CONSTRUCAO = {
    "codigo": "em_construcao",
    "mensagem": "Esta parte do Portal ainda está sendo feita.",
}


def _501(resposta) -> None:
    assert resposta.status_code == 501, resposta.text
    assert resposta.json() == EM_CONSTRUCAO


# --- épico A · documentos ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "caminho",
    ["/api/documentos", "/api/documentos?arquivados=true", "/api/documentos/1"],
)
def test_a_leitura_dos_documentos(logar, caminho):
    _501(logar(COMUM).get(caminho))


def test_a_documentos_publicos_e_link(cliente):
    _501(cliente.get("/api/documentos/publicos"))
    _501(cliente.get("/api/documentos/1/versoes/1/link?baixar=true"))


def test_a_publicar_versao_e_arquivar(logar):
    comissao = logar(COMISSAO)
    _501(comissao.post("/api/documentos", json={**NOVO_DOCUMENTO, "avisar_unidades": True}))
    _501(comissao.post("/api/documentos/1/versoes", json={"arquivo_id": 1}))
    _501(comissao.post("/api/documentos/1/arquivar"))


# --- épico B · anexos nos avisos ---------------------------------------------------------------


def test_b_publicar_e_corrigir_com_anexos(logar):
    admin = logar(ADMIN)
    _501(
        admin.post(
            "/api/avisos", json={"titulo": "T", "texto": "X", "para_todos": True, "anexos": [1]}
        )
    )
    aviso = publicar(admin)
    _501(
        admin.put(f"/api/avisos/{aviso['id']}", json={"titulo": "T2", "texto": "X2", "anexos": [1]})
    )


def test_b_link_do_anexo(logar):
    aviso = publicar(logar(ADMIN))
    _501(logar(COMUM).get(f"/api/avisos/{aviso['id']}/anexos/1/link"))
