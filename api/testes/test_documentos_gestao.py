"""Épico A do M3 · publicar (H-17, RF-33), nova versão (H-19) e arquivar (spec do épico, seções
2.2 e 2.3). Permissão, CSRF e validação do corpo estão em `test_m3_rotas.py`."""

import pytest
from sqlalchemy import text

from testes.conftest import ADMIN, COMISSAO, COMUM
from testes.test_avisos_apoio import historico
from testes.test_documentos_apoio import (
    arquivar,
    corpo,
    enviar_arquivo,
    nova_versao,
    publicar_documento,
)

pytestmark = pytest.mark.usefixtures("predio")

ENVIE_DE_NOVO = "Envie o arquivo de novo."


def _contar(engine, tabela: str) -> int:
    with engine.connect() as con:
        return con.execute(text(f"select count(*) from {tabela}")).scalar_one()  # noqa: S608


@pytest.fixture
def agendados(monkeypatch) -> list[int]:
    """Os avisos que a rota mandou notificar (depois do commit)."""
    from app.rotas import documentos

    chamados: list[int] = []
    monkeypatch.setattr(
        documentos.notificacoes, "agendar", lambda _tarefas, aviso_id: chamados.append(aviso_id)
    )
    return chamados


# --- publicar ----------------------------------------------------------------------------------


def test_publicar_devolve_o_documento(logar, armazenamento, engine_app, predio, agendados):
    cliente = logar(COMISSAO)
    arquivo_id = enviar_arquivo(cliente, armazenamento)
    resposta = cliente.post("/api/documentos", json=corpo(arquivo_id))
    assert resposta.status_code == 201, resposta.text
    documento = resposta.json()
    assert documento["titulo"] == "Convenção do condomínio"
    assert documento["versao"] == 1
    assert documento["arquivo"]["id"] == arquivo_id
    assert documento["versoes_anteriores"] == []
    assert documento["aviso_id"] is None
    assert documento["arquivado_em"] is None
    assert _contar(engine_app, "aviso") == 0
    assert agendados == []
    assert historico(engine_app, "documento_publicado") == [
        {
            "unidade_id": predio[COMISSAO],
            "entidade": "documento",
            "entidade_id": documento["id"],
            "detalhes": {
                "versao": 1,
                "acesso": "compradores",
                "categoria": "convencao",
                "avisou": False,
            },
        }
    ]


def test_avisar_as_unidades_publica_o_aviso_junto(logar, armazenamento, engine_app, agendados):
    documento = publicar_documento(
        logar, armazenamento, avisar_unidades=True, titulo="Regimento interno"
    )
    aviso_id = documento["aviso_id"]
    assert aviso_id is not None
    assert agendados == [aviso_id]
    aviso = logar(COMUM).get(f"/api/avisos/{aviso_id}").json()
    assert aviso["titulo"] == "Documento novo: Regimento interno"
    assert aviso["categoria"] == "geral"
    assert aviso["para_todos"] is True
    assert aviso["fixado"] is False
    assert "“Regimento interno”" in aviso["texto"]
    assert "Abrir o documento" in aviso["texto"]
    assert aviso["documento"] == {"id": documento["id"], "titulo": "Regimento interno"}
    assert historico(engine_app, "documento_publicado")[0]["detalhes"]["avisou"] is True
    # O pedido de notificação entra na mesma transação (M2).
    assert _contar(engine_app, "notificacao_envio") > 0


def test_titulo_comprido_cabe_no_aviso(logar, armazenamento, agendados):
    titulo = "Ata " + "x" * 116
    documento = publicar_documento(logar, armazenamento, avisar_unidades=True, titulo=titulo)
    aviso = logar(COMUM).get(f"/api/avisos/{documento['aviso_id']}").json()
    assert len(aviso["titulo"]) == 120
    assert aviso["titulo"].startswith("Documento novo: Ata xxx")
    assert aviso["titulo"].endswith("…")


def test_aviso_de_documento_publico_aparece_para_todos(logar, armazenamento, agendados):
    documento = publicar_documento(
        logar, armazenamento, avisar_unidades=True, acesso="publico", login=ADMIN
    )
    assert logar(COMUM).get(f"/api/avisos/{documento['aviso_id']}").status_code == 200


@pytest.mark.parametrize(
    "como",
    ["de_outra_unidade", "pendente", "de_aviso", "inexistente"],
)
def test_arquivo_que_nao_serve_pede_para_enviar_de_novo(
    logar, armazenamento, engine_app, agendados, como
):
    cliente = logar(COMISSAO)
    if como == "de_outra_unidade":
        arquivo_id = enviar_arquivo(logar(ADMIN), armazenamento)
    elif como == "pendente":
        arquivo_id = enviar_arquivo(cliente, armazenamento, confirmar=False)
    elif como == "de_aviso":
        arquivo_id = enviar_arquivo(cliente, armazenamento, finalidade="aviso")
    else:
        arquivo_id = 999999
    resposta = cliente.post("/api/documentos", json=corpo(arquivo_id, avisar_unidades=True))
    assert resposta.status_code == 422, resposta.text
    assert resposta.json()["codigo"] == "arquivo_invalido"
    assert resposta.json()["mensagem"] == ENVIE_DE_NOVO
    assert resposta.json()["campos"] == [{"campo": "arquivo_id", "mensagem": ENVIE_DE_NOVO}]
    assert _contar(engine_app, "documento") == 0
    assert _contar(engine_app, "aviso") == 0
    assert agendados == []


def test_arquivo_ja_usado_em_outro_documento(logar, armazenamento, engine_app, agendados):
    documento = publicar_documento(logar, armazenamento)
    resposta = logar(COMISSAO).post(
        "/api/documentos",
        json=corpo(documento["arquivo"]["id"], titulo="Outro", avisar_unidades=True),
    )
    assert resposta.status_code == 409, resposta.text
    assert resposta.json()["codigo"] == "arquivo_em_uso"
    # Tudo ou nada: o aviso automático também não ficou.
    assert _contar(engine_app, "documento") == 1
    assert _contar(engine_app, "aviso") == 0
    assert agendados == []


# --- nova versão -------------------------------------------------------------------------------


def test_nova_versao_guarda_a_anterior(logar, armazenamento, engine_app, predio):
    publicado = publicar_documento(logar, armazenamento)
    documento = nova_versao(logar, armazenamento, publicado["id"], login=ADMIN)
    assert documento["versao"] == 2
    assert documento["arquivo"]["nome"] == "Versão nova.pdf"
    assert [v["versao"] for v in documento["versoes_anteriores"]] == [1]
    assert documento["versoes_anteriores"][0]["arquivo"] == publicado["arquivo"]
    assert historico(engine_app, "documento_versao_enviada") == [
        {
            "unidade_id": predio[ADMIN],
            "entidade": "documento",
            "entidade_id": publicado["id"],
            "detalhes": {"versao": 2},
        }
    ]


def test_nova_versao_de_documento_inexistente(logar, armazenamento):
    cliente = logar(COMISSAO)
    arquivo_id = enviar_arquivo(cliente, armazenamento)
    resposta = cliente.post("/api/documentos/999999/versoes", json={"arquivo_id": arquivo_id})
    assert (resposta.status_code, resposta.json()["codigo"]) == (404, "documento_nao_encontrado")


def test_documento_arquivado_nao_recebe_versao(logar, armazenamento):
    publicado = publicar_documento(logar, armazenamento)
    arquivar(logar, publicado["id"])
    cliente = logar(COMISSAO)
    arquivo_id = enviar_arquivo(cliente, armazenamento)
    resposta = cliente.post(
        f"/api/documentos/{publicado['id']}/versoes", json={"arquivo_id": arquivo_id}
    )
    assert resposta.status_code == 409
    assert resposta.json() == {
        "codigo": "documento_arquivado",
        "mensagem": "Documento arquivado não recebe versão nova.",
    }


def test_nova_versao_com_arquivo_que_nao_serve(logar, armazenamento):
    publicado = publicar_documento(logar, armazenamento)
    de_outro = enviar_arquivo(logar(ADMIN), armazenamento)
    resposta = logar(COMISSAO).post(
        f"/api/documentos/{publicado['id']}/versoes", json={"arquivo_id": de_outro}
    )
    assert resposta.status_code == 422
    assert resposta.json()["campos"] == [{"campo": "arquivo_id", "mensagem": ENVIE_DE_NOVO}]
    repetido = logar(COMISSAO).post(
        f"/api/documentos/{publicado['id']}/versoes",
        json={"arquivo_id": publicado["arquivo"]["id"]},
    )
    assert (repetido.status_code, repetido.json()["codigo"]) == (409, "arquivo_em_uso")


# --- arquivar ----------------------------------------------------------------------------------


def test_arquivar(logar, armazenamento, engine_app, predio):
    publicado = publicar_documento(logar, armazenamento)
    documento = arquivar(logar, publicado["id"], login=ADMIN)
    assert documento["arquivado_em"] is not None
    assert documento["id"] == publicado["id"]
    assert historico(engine_app, "documento_arquivado") == [
        {
            "unidade_id": predio[ADMIN],
            "entidade": "documento",
            "entidade_id": publicado["id"],
            "detalhes": {},
        }
    ]


def test_arquivar_de_novo_devolve_como_esta(logar, armazenamento, engine_app):
    publicado = publicar_documento(logar, armazenamento)
    primeiro = arquivar(logar, publicado["id"])
    segundo = arquivar(logar, publicado["id"], login=ADMIN)
    assert segundo == primeiro
    assert len(historico(engine_app, "documento_arquivado")) == 1


def test_arquivar_inexistente(logar):
    resposta = logar(COMISSAO).post("/api/documentos/999999/arquivar")
    assert (resposta.status_code, resposta.json()["codigo"]) == (404, "documento_nao_encontrado")


def test_arquivado_tira_o_botao_do_aviso(logar, armazenamento, agendados):
    documento = publicar_documento(logar, armazenamento, avisar_unidades=True)
    arquivar(logar, documento["id"])
    assert logar(COMUM).get(f"/api/avisos/{documento['aviso_id']}").json()["documento"] is None
