"""Épico B do M3 · link do anexo (spec do M3, seção 5.3; `m3-anexos.md`, seção 2.3).

Quem vê o aviso vê o anexo, de qualquer versão. Fora disso, 404 igual a aviso inexistente.
"""

from urllib.parse import parse_qs, urlsplit

import pytest

from testes.conftest import ADMIN, COMISSAO, COMUM, NAO_ATIVADA
from testes.test_anexos_apoio import JPEG, enviar
from testes.test_avisos_apoio import ativar

pytestmark = pytest.mark.usefixtures("predio")

NAO_ACHAMOS = "aviso_nao_encontrado"


def _publicar(cliente, armazenamento, *, blocos: list[int] | None = None, **arquivo):
    anexo = enviar(cliente, armazenamento, **arquivo)
    corpo = {"titulo": "Fundação", "texto": "A foto está abaixo.", "anexos": [anexo["id"]]}
    corpo |= {"para_todos": False, "blocos": blocos} if blocos else {"para_todos": True}
    resposta = cliente.post("/api/avisos", json=corpo)
    assert resposta.status_code == 201, resposta.text
    return resposta.json(), anexo


def _link(cliente, aviso_id: int, arquivo_id: int, **params):
    return cliente.get(f"/api/avisos/{aviso_id}/anexos/{arquivo_id}/link", params=params)


def _nao_achou(resposta) -> None:
    assert resposta.status_code == 404, resposta.text
    assert resposta.json()["codigo"] == NAO_ACHAMOS


def test_morador_abre_a_foto(logar, armazenamento):
    aviso, foto = _publicar(
        logar(COMISSAO), armazenamento, nome="fundação.jpg", conteudo=JPEG, tipo="image/jpeg"
    )
    resposta = _link(logar(COMUM), aviso["id"], foto["id"])
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert set(corpo) == {"url", "expira_em"}
    url = urlsplit(corpo["url"])
    assert url.path.startswith("/arquivos/")
    assert parse_qs(url.query) == {"tipo": ["image/jpeg"], "baixar": ["0"]}


def test_baixar(logar, armazenamento):
    aviso, pdf = _publicar(logar(ADMIN), armazenamento)
    corpo = _link(logar(COMUM), aviso["id"], pdf["id"], baixar="true").json()
    assert parse_qs(urlsplit(corpo["url"]).query)["baixar"] == ["1"]


def test_anexo_de_versao_antiga_tambem_abre(logar, armazenamento):
    admin = logar(ADMIN)
    aviso, pdf = _publicar(admin, armazenamento)
    corpo = {"titulo": "Fundação", "texto": "Sem foto.", "anexos": []}
    corrigido = admin.put(f"/api/avisos/{aviso['id']}", json=corpo)
    assert corrigido.status_code == 200, corrigido.text
    assert _link(logar(COMUM), aviso["id"], pdf["id"]).status_code == 200


def test_aviso_de_outro_bloco_nao_mostra_o_anexo(logar, armazenamento, engine_app):
    # 1203 é do Bloco 1; o aviso é só para o Bloco 2.
    aviso, pdf = _publicar(logar(COMISSAO), armazenamento, blocos=[2])
    _nao_achou(_link(logar(COMUM), aviso["id"], pdf["id"]))
    ativar(engine_app, "2101")
    assert _link(logar("2101"), aviso["id"], pdf["id"]).status_code == 200
    # A gestão vê todos os avisos.
    assert _link(logar(ADMIN), aviso["id"], pdf["id"]).status_code == 200


def test_arquivo_que_nao_e_deste_aviso(logar, armazenamento):
    admin = logar(ADMIN)
    aviso, _ = _publicar(admin, armazenamento)
    outro, pdf_do_outro = _publicar(admin, armazenamento)
    solto = enviar(admin, armazenamento)
    documento = enviar(admin, armazenamento, finalidade="documento")
    for arquivo_id in (pdf_do_outro["id"], solto["id"], documento["id"], 999_999):
        _nao_achou(_link(admin, aviso["id"], arquivo_id))
    _nao_achou(_link(admin, 999_999, pdf_do_outro["id"]))
    assert _link(admin, outro["id"], pdf_do_outro["id"]).status_code == 200


def test_aviso_arquivado_continua_abrindo(logar, armazenamento):
    admin = logar(ADMIN)
    aviso, pdf = _publicar(admin, armazenamento)
    assert admin.post(f"/api/avisos/{aviso['id']}/arquivar").status_code == 200
    assert _link(logar(COMUM), aviso["id"], pdf["id"]).status_code == 200


def test_sem_bucket_503_so_para_quem_ve(logar, armazenamento):
    from app.main import app
    from app.servicos.armazenamento import obter_armazenamento

    comissao = logar(COMISSAO)
    para_todos, pdf = _publicar(comissao, armazenamento)
    do_bloco_2, pdf_bloco_2 = _publicar(comissao, armazenamento, blocos=[2])
    app.dependency_overrides[obter_armazenamento] = lambda: None
    comum = logar(COMUM)
    resposta = _link(comum, para_todos["id"], pdf["id"])
    assert resposta.status_code == 503, resposta.text
    assert resposta.json()["codigo"] == "arquivos_desligados"
    # Quem não vê o aviso continua recebendo 404, com ou sem bucket.
    _nao_achou(_link(comum, do_bloco_2["id"], pdf_bloco_2["id"]))


def test_sem_sessao_completa(cliente, logar, armazenamento):
    aviso, pdf = _publicar(logar(ADMIN), armazenamento)
    assert _link(cliente, aviso["id"], pdf["id"]).status_code == 401
    assert _link(logar(NAO_ATIVADA), aviso["id"], pdf["id"]).status_code == 403
