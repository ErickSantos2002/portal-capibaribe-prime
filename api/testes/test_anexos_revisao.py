"""Épico B do M3 · achados das revisões de código e de UX (C1, C2, C5, U12).

- C1: dois pedidos com os mesmos arquivos em ordem diferente não viram deadlock (500).
- C2: correção feita num formulário velho não apaga o que outra pessoa pôs (`versao_base`).
- C5: ids fora do `bigint` são 422, não 500.
- U12: `…/anexos/{arquivo_id}/abrir` confere o acesso pela sessão e redireciona para um link
  novo a cada pedido (a foto e o PDF abrem mesmo com a página aberta há horas).
"""

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from testes.conftest import ADMIN, COMISSAO, COMUM
from testes.test_anexos_apoio import JPEG, enviar
from testes.test_avisos_apoio import ativar

pytestmark = pytest.mark.usefixtures("predio")

MAIOR_QUE_BIGINT = 2**63


def _publicar(cliente, anexos: list[int], **extra):
    corpo = {"titulo": "Vistoria", "texto": "Fotos abaixo.", "para_todos": True, "anexos": anexos}
    return cliente.post("/api/avisos", json={**corpo, **extra})


# --- C1 -----------------------------------------------------------------------------------------


@pytest.mark.parametrize("vez", range(4))
def test_mesmos_arquivos_em_ordem_diferente_nao_dao_500(logar, armazenamento, monkeypatch, vez):
    """Os dois pedidos passam pela conferência juntos e gravam os anexos ao mesmo tempo: um
    publica, o outro recebe a 422 de arquivo em uso (nunca 500 de deadlock)."""
    from app.servicos import avisos

    admin = logar(ADMIN)
    a = enviar(admin, armazenamento, nome="a.pdf")["id"]
    b = enviar(admin, armazenamento, nome="b.pdf")["id"]
    juntos = threading.Barrier(2, timeout=10)
    original = avisos._gravar_anexos

    def gravar_junto(*args, **kwargs):
        juntos.wait()
        return original(*args, **kwargs)

    monkeypatch.setattr(avisos, "_gravar_anexos", gravar_junto)
    clientes = [logar(ADMIN), logar(ADMIN)]
    with ThreadPoolExecutor(2) as fila:
        respostas = list(
            fila.map(
                lambda par: _publicar(par[0], par[1]), zip(clientes, [[a, b], [b, a]], strict=True)
            )
        )
    assert sorted(r.status_code for r in respostas) == [201, 422], [r.text for r in respostas]
    recusada = next(r for r in respostas if r.status_code == 422)
    assert recusada.json()["mensagem"] == "Envie o arquivo de novo."


# --- C2 -----------------------------------------------------------------------------------------


def test_correcao_de_formulario_velho_nao_apaga_o_anexo_dos_outros(logar, armazenamento):
    comissao, admin = logar(COMISSAO), logar(ADMIN)
    aviso = _publicar(comissao, []).json()
    # O admin abre o formulário (versão 1) e acrescenta uma foto: versão 2.
    foto = enviar(admin, armazenamento, nome="f.jpg", conteudo=JPEG, tipo="image/jpeg")
    corpo = {"titulo": "Vistoria", "texto": "Fotos abaixo.", "versao_base": 1}
    assert (
        admin.put(f"/api/avisos/{aviso['id']}", json={**corpo, "anexos": [foto["id"]]}).status_code
        == 200
    )
    # A Comissão, com o formulário aberto desde a versão 1, salva sem anexos.
    resposta = comissao.put(
        f"/api/avisos/{aviso['id']}", json={**corpo, "texto": "Outro texto.", "anexos": []}
    )
    assert resposta.status_code == 409, resposta.text
    assert resposta.json() == {
        "codigo": "aviso_corrigido_agora",
        "mensagem": "Outra pessoa corrigiu este aviso agora há pouco. Abra de novo e confira.",
    }
    assert comissao.get(f"/api/avisos/{aviso['id']}").json()["anexos"] == [foto]


def test_versao_base_atual_ou_omitida_corrige(logar):
    admin = logar(ADMIN)
    aviso = _publicar(admin, []).json()
    caminho = f"/api/avisos/{aviso['id']}"
    corpo = {"titulo": "Vistoria", "anexos": []}
    assert admin.put(caminho, json={**corpo, "texto": "Dois.", "versao_base": 1}).status_code == 200
    # Sem `versao_base` (cliente antigo), como antes.
    assert admin.put(caminho, json={**corpo, "texto": "Três."}).status_code == 200
    assert (
        admin.put(caminho, json={**corpo, "texto": "Quatro.", "versao_base": 0}).status_code == 422
    )


# --- C5 -----------------------------------------------------------------------------------------


@pytest.mark.parametrize("anexos", [[MAIOR_QUE_BIGINT], [0], [-1]])
def test_id_de_anexo_fora_da_faixa(logar, anexos):
    resposta = _publicar(logar(ADMIN), anexos)
    assert resposta.status_code == 422, resposta.text
    assert resposta.json()["codigo"] == "dados_invalidos"


@pytest.mark.parametrize(
    "caminho",
    [
        f"/api/avisos/{MAIOR_QUE_BIGINT}/anexos/1/link",
        f"/api/avisos/1/anexos/{MAIOR_QUE_BIGINT}/link",
        f"/api/avisos/{MAIOR_QUE_BIGINT}/anexos/1/abrir",
        f"/api/avisos/1/anexos/{MAIOR_QUE_BIGINT}/abrir",
    ],
)
def test_id_da_rota_fora_do_bigint(logar, armazenamento, caminho):
    resposta = logar(COMUM).get(caminho, follow_redirects=False)
    assert resposta.status_code == 422, resposta.text


# --- U12 ----------------------------------------------------------------------------------------


def _com_foto(logar, armazenamento, **extra):
    comissao = logar(COMISSAO)
    foto = enviar(comissao, armazenamento, nome="f.jpg", conteudo=JPEG, tipo="image/jpeg")
    resposta = _publicar(comissao, [foto["id"]], **extra)
    assert resposta.status_code == 201, resposta.text
    return resposta.json(), foto


def test_abrir_redireciona_para_um_link_novo(logar, armazenamento):
    aviso, foto = _com_foto(logar, armazenamento)
    morador = logar(COMUM)
    caminho = f"/api/avisos/{aviso['id']}/anexos/{foto['id']}/abrir"
    resposta = morador.get(caminho, follow_redirects=False)
    assert resposta.status_code == 302, resposta.text
    assert resposta.headers["location"].startswith("https://armazenamento.falso/arquivos/")
    assert resposta.headers["cache-control"] == "no-store"
    # Navegação comum: sem `X-Portal` (é uma aba nova ou uma <img>).
    morador.headers.pop("X-Portal", None)
    assert morador.get(caminho, follow_redirects=False).status_code == 302


def test_abrir_quem_nao_ve_recebe_uma_pagina_simples(logar, armazenamento):
    aviso, foto = _com_foto(logar, armazenamento, para_todos=False, blocos=[2])
    resposta = logar(COMUM).get(
        f"/api/avisos/{aviso['id']}/anexos/{foto['id']}/abrir", follow_redirects=False
    )
    assert resposta.status_code == 404
    assert resposta.headers["content-type"].startswith("text/html")
    assert "Não achamos este aviso" in resposta.text
    assert "<script" not in resposta.text


def test_abrir_sem_bucket_e_pagina_simples(logar, armazenamento, engine_app):
    from app.main import app
    from app.servicos.armazenamento import obter_armazenamento

    aviso, foto = _com_foto(logar, armazenamento)
    app.dependency_overrides[obter_armazenamento] = lambda: None
    resposta = logar(COMUM).get(f"/api/avisos/{aviso['id']}/anexos/{foto['id']}/abrir")
    assert resposta.status_code == 503
    assert "ainda não está ligado" in resposta.text


def test_abrir_exige_sessao(cliente, logar, armazenamento, engine_app):
    aviso, foto = _com_foto(logar, armazenamento)
    caminho = f"/api/avisos/{aviso['id']}/anexos/{foto['id']}/abrir"
    assert cliente.get(caminho, follow_redirects=False).status_code == 401
    ativar(engine_app, "2101")
    assert logar("2101").get(caminho, follow_redirects=False).status_code == 302
