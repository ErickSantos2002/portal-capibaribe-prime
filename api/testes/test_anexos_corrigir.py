"""Épico B do M3 · corrigir aviso com anexos (H-12, H-15; spec `m3-anexos.md`, seção 2.1).

O anexo é da versão: a correção cria a versão nova com os anexos dela, e a versão antiga fica
como foi publicada (RN-05).
"""

import pytest

from testes.conftest import ADMIN, COMISSAO, COMUM
from testes.test_anexos_apoio import JPEG, anexos_no_banco, enviar
from testes.test_anexos_publicar import ENVIE_DE_NOVO, recusado
from testes.test_avisos_apoio import historico

pytestmark = pytest.mark.usefixtures("predio")


@pytest.fixture
def com_dois(logar, armazenamento):
    """Um aviso da Comissão com uma foto e um PDF. Devolve (cliente, aviso, foto, pdf)."""
    comissao = logar(COMISSAO)
    foto = enviar(comissao, armazenamento, nome="fundação.jpg", conteudo=JPEG, tipo="image/jpeg")
    pdf = enviar(comissao, armazenamento)
    resposta = comissao.post(
        "/api/avisos",
        json={
            "titulo": "Visita à obra",
            "texto": "Regras no PDF.",
            "para_todos": True,
            "anexos": [foto["id"], pdf["id"]],
        },
    )
    assert resposta.status_code == 201, resposta.text
    return comissao, resposta.json(), foto, pdf


def _corrigir(cliente, aviso: dict, **corpo):
    return cliente.put(
        f"/api/avisos/{aviso['id']}",
        json={"titulo": aviso["titulo"], "texto": aviso["texto"], **corpo},
    )


@pytest.mark.parametrize("corpo", [{}, {"anexos": None}])
def test_omitido_ou_nulo_repete_os_anexos(com_dois, engine_app, corpo):
    comissao, aviso, foto, pdf = com_dois
    resposta = _corrigir(comissao, aviso, texto="Regras atualizadas no PDF.", **corpo)
    assert resposta.status_code == 200, resposta.text
    corrigido = resposta.json()
    assert corrigido["anexos"] == [foto, pdf]
    assert corrigido["versoes_anteriores"][0]["anexos"] == [foto, pdf]
    assert anexos_no_banco(engine_app, aviso["id"]) == [
        (1, 1, foto["id"]),
        (1, 2, pdf["id"]),
        (2, 1, foto["id"]),
        (2, 2, pdf["id"]),
    ]


def test_lista_vazia_tira_todos_e_a_versao_antiga_guarda(com_dois, logar):
    comissao, aviso, foto, pdf = com_dois
    resposta = _corrigir(comissao, aviso, anexos=[])
    assert resposta.status_code == 200, resposta.text
    corrigido = resposta.json()
    assert corrigido["anexos"] == []
    assert corrigido["quantidade_anexos"] == 0
    assert corrigido["versoes_anteriores"][0]["anexos"] == [foto, pdf]
    # O morador também vê os anexos da versão antiga.
    aberto = logar(COMUM).get(f"/api/avisos/{aviso['id']}").json()
    assert aberto["versoes_anteriores"][0]["anexos"] == [foto, pdf]
    [item] = logar(COMUM).get("/api/avisos").json()["itens"]
    assert item["quantidade_anexos"] == 0


def test_trocar_so_a_ordem_e_mudanca(com_dois, engine_app):
    comissao, aviso, foto, pdf = com_dois
    resposta = _corrigir(comissao, aviso, anexos=[pdf["id"], foto["id"]])
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["anexos"] == [pdf, foto]
    [registro] = historico(engine_app, "aviso_corrigido")
    assert registro["detalhes"] == {"versao": 2, "titulo": aviso["titulo"], "anexos": 2}


@pytest.mark.parametrize("anexos", ["mesmos", None, "omitido"])
def test_tudo_igual_continua_sem_mudanca(com_dois, anexos):
    comissao, aviso, foto, pdf = com_dois
    corpo = {} if anexos == "omitido" else {"anexos": anexos}
    if anexos == "mesmos":
        corpo = {"anexos": [foto["id"], pdf["id"]]}
    resposta = _corrigir(comissao, aviso, categoria=aviso["categoria"], **corpo)
    assert resposta.status_code == 409, resposta.text
    assert resposta.json()["codigo"] == "sem_mudanca"


def test_acrescentar_um_anexo_novo(com_dois, armazenamento, engine_app):
    comissao, aviso, foto, pdf = com_dois
    outro = enviar(comissao, armazenamento, nome="mapa.pdf")
    resposta = _corrigir(comissao, aviso, anexos=[foto["id"], pdf["id"], outro["id"]])
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["anexos"] == [foto, pdf, outro]
    assert resposta.json()["quantidade_anexos"] == 3


def test_outra_pessoa_da_gestao_repete_os_anexos(com_dois, logar, armazenamento):
    """O admin corrige o aviso da Comissão: os arquivos foram enviados pela Comissão, mas já são
    anexos deste aviso; pode repetir e reordenar, e pode juntar um enviado por ele."""
    _, aviso, foto, pdf = com_dois
    admin = logar(ADMIN)
    dele = enviar(admin, armazenamento, nome="planta.pdf")
    resposta = _corrigir(admin, aviso, anexos=[pdf["id"], dele["id"], foto["id"]])
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["anexos"] == [pdf, dele, foto]


def test_arquivo_de_outra_pessoa_que_nao_e_deste_aviso(com_dois, logar, armazenamento):
    comissao, aviso, _, _ = com_dois
    do_admin = enviar(logar(ADMIN), armazenamento)
    recusado(_corrigir(comissao, aviso, anexos=[do_admin["id"]]), ENVIE_DE_NOVO)


def test_anexo_de_outro_aviso_nao_entra(com_dois, logar, armazenamento):
    comissao, aviso, foto, _ = com_dois
    pdf_novo = enviar(comissao, armazenamento)
    outro = comissao.post(
        "/api/avisos",
        json={"titulo": "Outro", "texto": "X", "para_todos": True, "anexos": [pdf_novo["id"]]},
    ).json()
    recusado(_corrigir(comissao, outro, anexos=[foto["id"]]), ENVIE_DE_NOVO)


def test_limites_tambem_valem_na_correcao(com_dois, armazenamento):
    comissao, aviso, foto, pdf = com_dois
    recusado(
        _corrigir(comissao, aviso, anexos=[foto["id"], foto["id"]]),
        ("O mesmo arquivo foi escolhido duas vezes."),
    )
    novos = [enviar(comissao, armazenamento, nome=f"{n}.pdf")["id"] for n in range(4)]
    recusado(
        _corrigir(comissao, aviso, anexos=[foto["id"], pdf["id"], *novos]),
        "Até 5 anexos por aviso.",
    )


def test_correcao_sem_anexos_nao_registra_anexos(logar, engine_app):
    from testes.test_avisos_apoio import publicar

    admin = logar(ADMIN)
    aviso = publicar(admin)
    assert _corrigir(admin, aviso, texto="Outro texto.").status_code == 200
    [registro] = historico(engine_app, "aviso_corrigido")
    assert "anexos" not in registro["detalhes"]
