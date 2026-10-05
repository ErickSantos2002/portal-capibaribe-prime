"""H-15 · Corrigir ou arquivar aviso (e fixar/desafixar). RN-05: nada se apaga."""

import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import text

from testes.test_avisos_apoio import COMISSAO, COMUM, historico, publicar

pytestmark = pytest.mark.usefixtures("predio")


@pytest.fixture
def aviso(logar) -> dict:
    return publicar(logar(COMISSAO), titulo="Reunião às 19h", texto="No salão da igreja.")


# --- H-15: editar mostra "Editado em", com a versão anterior ----------------------------------


def test_corrigir_cria_versao(logar, engine_app, predio, aviso):
    comissao = logar(COMISSAO)
    resposta = comissao.put(
        f"/api/avisos/{aviso['id']}",
        json={"titulo": "Reunião às 19h30", "texto": "No salão da igreja da Várzea."},
    )
    assert resposta.status_code == 200, resposta.text
    corrigido = resposta.json()
    assert corrigido["titulo"] == "Reunião às 19h30"
    assert corrigido["texto"] == "No salão da igreja da Várzea."
    assert corrigido["editado_em"] is not None
    assert corrigido["publicado_em"] == aviso["publicado_em"]
    assert [(v["versao"], v["titulo"], v["texto"]) for v in corrigido["versoes_anteriores"]] == [
        (1, "Reunião às 19h", "No salão da igreja.")
    ]
    # Todos veem o "Editado em" e a versão de antes, não só a gestão.
    para_morador = logar(COMUM).get(f"/api/avisos/{aviso['id']}").json()
    assert para_morador["editado_em"] == corrigido["editado_em"]
    assert len(para_morador["versoes_anteriores"]) == 1
    item = logar(COMUM).get("/api/avisos").json()["itens"][0]
    assert item["editado_em"] == corrigido["editado_em"]

    assert historico(engine_app, "aviso_corrigido") == [
        {
            "unidade_id": predio[COMISSAO],
            "entidade": "aviso",
            "entidade_id": aviso["id"],
            "detalhes": {"versao": 2, "titulo": "Reunião às 19h30"},
        }
    ]


def test_versoes_anteriores_da_mais_nova(logar, aviso):
    comissao = logar(COMISSAO)
    for titulo in ("Versão 2", "Versão 3"):
        comissao.put(f"/api/avisos/{aviso['id']}", json={"titulo": titulo, "texto": "Texto"})
    lido = comissao.get(f"/api/avisos/{aviso['id']}").json()
    assert lido["titulo"] == "Versão 3"
    assert [v["versao"] for v in lido["versoes_anteriores"]] == [2, 1]


def test_corrigir_sem_mudanca(logar, aviso):
    resposta = logar(COMISSAO).put(
        f"/api/avisos/{aviso['id']}",
        json={"titulo": " Reunião às 19h ", "texto": "No salão da igreja.\n"},
    )
    assert resposta.status_code == 409
    assert resposta.json() == {"codigo": "sem_mudanca", "mensagem": "Nada mudou no aviso."}


def test_corrigir_valida_como_publicar(logar, aviso):
    resposta = logar(COMISSAO).put(f"/api/avisos/{aviso['id']}", json={"titulo": "", "texto": "X"})
    assert resposta.status_code == 422
    assert resposta.json()["mensagem"] == "Escreva o título do aviso."


def test_corrigir_inexistente(logar):
    resposta = logar(COMISSAO).put("/api/avisos/999", json={"titulo": "T", "texto": "X"})
    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "aviso_nao_encontrado"


def test_duas_correcoes_ao_mesmo_tempo(logar, engine_app, predio, aviso):
    """A segunda correção bate na chave (aviso, versão) e vira 409, não 500."""
    comissao = logar(COMISSAO)
    with engine_app.connect() as con:
        transacao = con.begin()
        con.execute(
            text(
                "insert into aviso_versao (aviso_id, versao, titulo, texto, criada_por)"
                " values (:a, 2, 'Outra correção', 'Texto', :u)"
            ),
            {"a": aviso["id"], "u": predio[COMISSAO]},
        )
        with ThreadPoolExecutor(1) as executor:
            futura = executor.submit(
                comissao.put,
                f"/api/avisos/{aviso['id']}",
                json={"titulo": "Minha correção", "texto": "Texto"},
            )
            time.sleep(0.5)  # a correção da API espera a outra transação na chave
            transacao.commit()
            resposta = futura.result(timeout=10)
    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "aviso_corrigido_agora"
    assert comissao.get(f"/api/avisos/{aviso['id']}").json()["titulo"] == "Outra correção"
    assert historico(engine_app, "aviso_corrigido") == []


# --- H-15: arquivar tira do mural; continua em "Avisos arquivados" ----------------------------


def test_arquivar(logar, engine_app, predio):
    comissao = logar(COMISSAO)
    aviso = publicar(comissao, fixado=True)
    resposta = comissao.post(f"/api/avisos/{aviso['id']}/arquivar")
    assert resposta.status_code == 200
    arquivado = resposta.json()
    assert arquivado["arquivado_em"] is not None
    # Fixado não tem sentido fora do mural.
    assert arquivado["fixado"] is False

    comum = logar(COMUM)
    assert comum.get("/api/avisos").json()["itens"] == []
    assert [i["id"] for i in comum.get("/api/avisos?arquivados=true").json()["itens"]] == [
        aviso["id"]
    ]
    # Continua acessível pelo link.
    assert comum.get(f"/api/avisos/{aviso['id']}").status_code == 200
    assert historico(engine_app, "aviso_arquivado") == [
        {
            "unidade_id": predio[COMISSAO],
            "entidade": "aviso",
            "entidade_id": aviso["id"],
            "detalhes": {},
        }
    ]


def test_arquivar_de_novo(logar, aviso):
    comissao = logar(COMISSAO)
    comissao.post(f"/api/avisos/{aviso['id']}/arquivar")
    resposta = comissao.post(f"/api/avisos/{aviso['id']}/arquivar")
    assert resposta.status_code == 409
    assert resposta.json() == {
        "codigo": "aviso_arquivado",
        "mensagem": "Este aviso já está arquivado.",
    }


def test_arquivado_nao_se_corrige_nem_se_fixa(logar, aviso):
    comissao = logar(COMISSAO)
    comissao.post(f"/api/avisos/{aviso['id']}/arquivar")
    corrigir = comissao.put(f"/api/avisos/{aviso['id']}", json={"titulo": "Novo", "texto": "X"})
    assert corrigir.status_code == 409
    assert corrigir.json() == {
        "codigo": "aviso_arquivado",
        "mensagem": "Aviso arquivado não pode ser corrigido.",
    }
    fixar = comissao.put(f"/api/avisos/{aviso['id']}/fixado", json={"fixado": True})
    assert fixar.status_code == 409
    assert fixar.json()["codigo"] == "aviso_arquivado"


def test_arquivar_inexistente(logar):
    assert logar(COMISSAO).post("/api/avisos/999/arquivar").status_code == 404


# --- H-15: não existe apagar ------------------------------------------------------------------


def test_nao_existe_rota_de_apagar(logar, aviso):
    resposta = logar(COMISSAO).delete(f"/api/avisos/{aviso['id']}")
    assert resposta.status_code == 405
    assert logar(COMUM).get(f"/api/avisos/{aviso['id']}").status_code == 200


# --- fixar no topo (RF-12) --------------------------------------------------------------------


def test_fixar_e_desafixar(logar, engine_app, aviso):
    comissao = logar(COMISSAO)
    caminho = f"/api/avisos/{aviso['id']}/fixado"
    assert comissao.put(caminho, json={"fixado": True}).json()["fixado"] is True
    assert comissao.put(caminho, json={"fixado": True}).status_code == 200
    assert comissao.put(caminho, json={"fixado": False}).json()["fixado"] is False
    # Histórico só quando mudou.
    assert len(historico(engine_app, "aviso_fixado")) == 1
    assert len(historico(engine_app, "aviso_desafixado")) == 1


def test_fixado_exige_booleano(logar, aviso):
    resposta = logar(COMISSAO).put(f"/api/avisos/{aviso['id']}/fixado", json={})
    assert resposta.status_code == 422
