"""Épico B do M3 · publicar aviso com anexos (H-12; spec `m3-anexos.md`, seção 2.1)."""

from typing import Any

import pytest
from sqlalchemy import text

from testes.conftest import ADMIN, COMISSAO, COMUM
from testes.test_anexos_apoio import JPEG, PDF, anexos_no_banco, enviar, pedir_sem_confirmar
from testes.test_avisos_apoio import historico, publicar

pytestmark = pytest.mark.usefixtures("predio")

ENVIE_DE_NOVO = "Envie o arquivo de novo."


def _corpo(anexos: Any, **extra) -> dict:
    return {
        "titulo": "Visita à obra",
        "texto": "As regras estão no PDF.",
        "para_todos": True,
        "anexos": anexos,
        **extra,
    }


def recusado(resposta, mensagem: str) -> None:
    assert resposta.status_code == 422, resposta.text
    corpo = resposta.json()
    assert corpo["codigo"] == "dados_invalidos"
    assert corpo["mensagem"] == mensagem
    assert corpo["campos"] == [{"campo": "anexos", "mensagem": mensagem}]


def _avisos(engine) -> int:
    with engine.connect() as con:
        return con.execute(text("select count(*) from aviso")).scalar_one()


def test_publicar_com_foto_e_pdf(logar, armazenamento, engine_app):
    comissao = logar(COMISSAO)
    pdf = enviar(comissao, armazenamento)
    foto = enviar(comissao, armazenamento, nome="fundação.jpg", conteudo=JPEG, tipo="image/jpeg")
    resposta = comissao.post("/api/avisos", json=_corpo([foto["id"], pdf["id"]]))
    assert resposta.status_code == 201, resposta.text
    aviso = resposta.json()
    assert aviso["anexos"] == [foto, pdf]
    assert aviso["quantidade_anexos"] == 2
    assert anexos_no_banco(engine_app, aviso["id"]) == [(1, 1, foto["id"]), (1, 2, pdf["id"])]
    # Quem vê o aviso vê os anexos.
    comum = logar(COMUM)
    assert comum.get(f"/api/avisos/{aviso['id']}").json()["anexos"] == [foto, pdf]
    [item] = comum.get("/api/avisos").json()["itens"]
    assert item["quantidade_anexos"] == 2
    [registro] = historico(engine_app, "aviso_publicado")
    assert registro["detalhes"]["anexos"] == 2


def test_cinco_anexos_valem_e_seis_nao(logar, armazenamento, engine_app):
    admin = logar(ADMIN)
    ids = [enviar(admin, armazenamento, nome=f"foto {n}.pdf")["id"] for n in range(6)]
    recusado(admin.post("/api/avisos", json=_corpo(ids)), "Até 5 anexos por aviso.")
    assert _avisos(engine_app) == 0
    resposta = admin.post("/api/avisos", json=_corpo(ids[:5]))
    assert resposta.status_code == 201, resposta.text
    assert [a["id"] for a in resposta.json()["anexos"]] == ids[:5]


def test_o_mesmo_arquivo_duas_vezes(logar, armazenamento, engine_app):
    admin = logar(ADMIN)
    pdf = enviar(admin, armazenamento)
    recusado(
        admin.post("/api/avisos", json=_corpo([pdf["id"], pdf["id"]])),
        "O mesmo arquivo foi escolhido duas vezes.",
    )
    assert _avisos(engine_app) == 0


def test_sem_anexos_continua_como_antes(logar, armazenamento, engine_app):
    for anexos in (None, []):
        resposta = logar(ADMIN).post("/api/avisos", json=_corpo(anexos))
        assert resposta.status_code == 201, resposta.text
        assert resposta.json()["anexos"] == []
    assert publicar(logar(ADMIN))["quantidade_anexos"] == 0
    # O histórico do aviso sem anexo é o mesmo de antes (o épico A compara o detalhe inteiro).
    registros = historico(engine_app, "aviso_publicado")
    assert len(registros) == 3
    assert all("anexos" not in r["detalhes"] for r in registros)


def test_arquivo_de_outra_unidade_da_gestao(logar, armazenamento, engine_app):
    pdf = enviar(logar(ADMIN), armazenamento)
    recusado(logar(COMISSAO).post("/api/avisos", json=_corpo([pdf["id"]])), ENVIE_DE_NOVO)
    assert _avisos(engine_app) == 0


def test_pendente_inexistente_ou_de_documento(logar, armazenamento, engine_app):
    admin = logar(ADMIN)
    pendente = pedir_sem_confirmar(admin, armazenamento)
    documento = enviar(admin, armazenamento, finalidade="documento")
    for arquivo_id in (pendente["arquivo_id"], documento["id"], 999_999):
        recusado(admin.post("/api/avisos", json=_corpo([arquivo_id])), ENVIE_DE_NOVO)
    assert _avisos(engine_app) == 0


def test_arquivo_ja_usado_em_outro_aviso(logar, armazenamento, engine_app):
    admin = logar(ADMIN)
    pdf = enviar(admin, armazenamento)
    assert admin.post("/api/avisos", json=_corpo([pdf["id"]])).status_code == 201
    recusado(admin.post("/api/avisos", json=_corpo([pdf["id"]])), ENVIE_DE_NOVO)
    assert _avisos(engine_app) == 1


def test_corrida_no_banco_vira_a_mesma_mensagem(logar, armazenamento, engine_app, monkeypatch):
    """Dois avisos ao mesmo tempo com o mesmo arquivo: a conferência da API passou nos dois e o
    banco (`arquivo_em_uso`) recusa o segundo. Aqui, a conferência da API é desligada."""
    from app.servicos import avisos

    admin = logar(ADMIN)
    pdf = enviar(admin, armazenamento)
    assert admin.post("/api/avisos", json=_corpo([pdf["id"]])).status_code == 201
    monkeypatch.setattr(avisos, "_em_uso_fora_do_aviso", lambda *a, **k: False)
    recusado(admin.post("/api/avisos", json=_corpo([pdf["id"]])), ENVIE_DE_NOVO)
    assert _avisos(engine_app) == 1


def test_unidade_comum_nao_publica(logar, armazenamento):
    assert logar(COMUM).post("/api/avisos", json=_corpo([1])).status_code == 403


def test_o_anexo_tem_o_nome_e_o_tamanho_real(logar, armazenamento):
    admin = logar(ADMIN)
    pdf = enviar(admin, armazenamento)
    [anexo] = admin.post("/api/avisos", json=_corpo([pdf["id"]])).json()["anexos"]
    assert anexo == {
        "id": pdf["id"],
        "nome": "Regras da visita.pdf",
        "tipo": "application/pdf",
        "tamanho_bytes": len(PDF),
    }
