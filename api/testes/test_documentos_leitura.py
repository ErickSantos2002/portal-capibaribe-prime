"""Épico A do M3 · consultar documentos (H-18): quem vê o quê, a lista, o documento aberto e o
link do arquivo (spec do épico, seção 2.1).

Critério do roadmap: documento de nível "gestão" não aparece nem baixa por link direto para a
conta comum. Fora do que a unidade vê, a resposta é igual à de documento inexistente.
"""

import pytest

from testes.conftest import ADMIN, COMISSAO, COMUM, NAO_ATIVADA
from testes.test_documentos_apoio import PDF, arquivar, nova_versao, publicar_documento

pytestmark = pytest.mark.usefixtures("predio", "armazenamento")

NAO_ENCONTRADO = {
    "codigo": "documento_nao_encontrado",
    "mensagem": (
        "Não achamos este documento. O link pode estar incompleto, ou ele não está mais disponível."
    ),
}


@pytest.fixture
def tres_niveis(logar, armazenamento) -> dict[str, dict]:
    """Um documento de cada nível, com datas diferentes."""
    return {
        "publico": publicar_documento(
            logar,
            armazenamento,
            titulo="Como acessar o Portal",
            categoria="orientacao",
            acesso="publico",
            data_documento="2026-10-28",
        ),
        "compradores": publicar_documento(
            logar,
            armazenamento,
            titulo="Cronograma da obra",
            categoria="obra",
            acesso="compradores",
            data_documento="2026-11-01",
        ),
        "gestao": publicar_documento(
            logar,
            armazenamento,
            titulo="Ata da reunião da Comissão",
            categoria="ata",
            acesso="gestao",
            data_documento="2026-10-18",
        ),
    }


def _titulos(resposta) -> list[str]:
    assert resposta.status_code == 200, resposta.text
    return [i["titulo"] for i in resposta.json()["itens"]]


# --- lista -------------------------------------------------------------------------------------


def test_unidade_comum_nao_ve_documento_da_gestao_na_lista(logar, tres_niveis):
    assert _titulos(logar(COMUM).get("/api/documentos")) == [
        "Cronograma da obra",
        "Como acessar o Portal",
    ]


@pytest.mark.parametrize("login", [ADMIN, COMISSAO])
def test_gestao_ve_os_tres_niveis_por_data_do_documento(logar, tres_niveis, login):
    assert _titulos(logar(login).get("/api/documentos")) == [
        "Cronograma da obra",
        "Como acessar o Portal",
        "Ata da reunião da Comissão",
    ]


def test_mesma_data_desempata_pelo_mais_novo(logar, armazenamento):
    publicar_documento(logar, armazenamento, titulo="Primeiro")
    publicar_documento(logar, armazenamento, titulo="Segundo")
    assert _titulos(logar(COMUM).get("/api/documentos")) == ["Segundo", "Primeiro"]


def test_item_da_lista(logar, armazenamento):
    documento = nova_versao(logar, armazenamento, publicar_documento(logar, armazenamento)["id"])
    [item] = logar(COMUM).get("/api/documentos").json()["itens"]
    assert item == {
        "id": documento["id"],
        "titulo": "Convenção do condomínio",
        "categoria": "convencao",
        "data_documento": "2026-10-01",
        "acesso": "compradores",
        "versao": 2,
        "atualizado_em": documento["atualizado_em"],
        "arquivo": {
            "id": documento["arquivo"]["id"],
            "nome": "Versão nova.pdf",
            "tipo": "application/pdf",
            "tamanho_bytes": len(PDF),
        },
        "arquivado_em": None,
    }


def test_publicos_sem_sessao_so_os_publicos(cliente, logar, tres_niveis):
    for quem in (cliente, logar(NAO_ATIVADA), logar(COMUM), logar(ADMIN)):
        assert _titulos(quem.get("/api/documentos/publicos")) == ["Como acessar o Portal"]


# --- arquivados --------------------------------------------------------------------------------


def test_arquivado_sai_da_lista_e_vai_para_os_arquivados_da_gestao(cliente, logar, tres_niveis):
    arquivar(logar, tres_niveis["publico"]["id"])
    assert "Como acessar o Portal" not in _titulos(logar(COMISSAO).get("/api/documentos"))
    assert _titulos(cliente.get("/api/documentos/publicos")) == []
    assert _titulos(logar(COMISSAO).get("/api/documentos?arquivados=true")) == [
        "Como acessar o Portal"
    ]


def test_unidade_comum_nao_ve_arquivados(logar, tres_niveis):
    arquivar(logar, tres_niveis["compradores"]["id"])
    assert _titulos(logar(COMUM).get("/api/documentos?arquivados=true")) == []
    documento_id = tres_niveis["compradores"]["id"]
    assert logar(COMUM).get(f"/api/documentos/{documento_id}").json() == NAO_ENCONTRADO
    link = logar(COMUM).get(f"/api/documentos/{documento_id}/versoes/1/link")
    assert (link.status_code, link.json()) == (404, NAO_ENCONTRADO)


def test_gestao_abre_o_arquivado(logar, tres_niveis):
    documento_id = tres_niveis["compradores"]["id"]
    arquivar(logar, documento_id)
    aberto = logar(ADMIN).get(f"/api/documentos/{documento_id}")
    assert aberto.status_code == 200
    assert aberto.json()["arquivado_em"] is not None
    assert logar(ADMIN).get(f"/api/documentos/{documento_id}/versoes/1/link").status_code == 200


# --- documento aberto --------------------------------------------------------------------------


def test_documento_aberto_com_as_versoes_anteriores(logar, armazenamento):
    publicado = publicar_documento(logar, armazenamento)
    nova_versao(logar, armazenamento, publicado["id"])
    terceira = nova_versao(logar, armazenamento, publicado["id"])
    aberto = logar(COMUM).get(f"/api/documentos/{publicado['id']}").json()
    assert aberto == terceira
    assert aberto["versao"] == 3
    assert [v["versao"] for v in aberto["versoes_anteriores"]] == [2, 1]
    assert aberto["versoes_anteriores"][1]["arquivo"] == publicado["arquivo"]
    assert aberto["versoes_anteriores"][1]["enviada_em"] == publicado["atualizado_em"]
    assert aberto["aviso_id"] is None


def test_documento_da_gestao_e_igual_a_inexistente_para_a_conta_comum(logar, tres_niveis):
    da_gestao = logar(COMUM).get(f"/api/documentos/{tres_niveis['gestao']['id']}")
    inexistente = logar(COMUM).get("/api/documentos/999999")
    assert (da_gestao.status_code, da_gestao.json()) == (404, NAO_ENCONTRADO)
    assert (inexistente.status_code, inexistente.json()) == (404, NAO_ENCONTRADO)


# --- link do arquivo ---------------------------------------------------------------------------


def _link(cliente, documento_id: int, versao: int = 1, baixar: bool | None = None):
    caminho = f"/api/documentos/{documento_id}/versoes/{versao}/link"
    if baixar is not None:
        caminho += f"?baixar={str(baixar).lower()}"
    return cliente.get(caminho)


def test_link_abre_ou_baixa_o_arquivo_da_versao(logar, tres_niveis):
    documento_id = tres_niveis["compradores"]["id"]
    aberto = _link(logar(COMUM), documento_id)
    assert aberto.status_code == 200, aberto.text
    assert set(aberto.json()) == {"url", "expira_em"}
    assert "/arquivos/" in aberto.json()["url"]
    assert aberto.json()["url"].endswith("baixar=0")
    assert _link(logar(COMUM), documento_id, baixar=True).json()["url"].endswith("baixar=1")


def test_link_de_versao_antiga_abre_o_arquivo_daquela_versao(logar, armazenamento):
    publicado = publicar_documento(logar, armazenamento)
    nova_versao(logar, armazenamento, publicado["id"])
    um = _link(logar(COMUM), publicado["id"], 1).json()["url"]
    dois = _link(logar(COMUM), publicado["id"], 2).json()["url"]
    assert um != dois
    assert _link(logar(COMUM), publicado["id"], 3).json() == NAO_ENCONTRADO


def test_link_do_documento_da_gestao_nao_sai_para_a_conta_comum(cliente, logar, tres_niveis):
    documento_id = tres_niveis["gestao"]["id"]
    for quem in (cliente, logar(NAO_ATIVADA), logar(COMUM)):
        resposta = _link(quem, documento_id, baixar=True)
        assert (resposta.status_code, resposta.json()) == (404, NAO_ENCONTRADO)
    assert _link(logar(COMISSAO), documento_id).status_code == 200


def test_sem_sessao_so_abre_o_publico(cliente, logar, tres_niveis):
    assert _link(cliente, tres_niveis["publico"]["id"]).status_code == 200
    assert _link(logar(NAO_ATIVADA), tres_niveis["publico"]["id"]).status_code == 200
    for quem in (cliente, logar(NAO_ATIVADA)):
        assert _link(quem, tres_niveis["compradores"]["id"]).json() == NAO_ENCONTRADO


def test_link_sem_bucket_responde_503(logar, tres_niveis):
    from app.main import app
    from app.servicos.armazenamento import obter_armazenamento

    app.dependency_overrides[obter_armazenamento] = lambda: None
    resposta = _link(logar(COMUM), tres_niveis["compradores"]["id"])
    assert (resposta.status_code, resposta.json()["codigo"]) == (503, "arquivos_desligados")
    # A lista funciona igual, sem bucket.
    assert logar(COMUM).get("/api/documentos").status_code == 200
