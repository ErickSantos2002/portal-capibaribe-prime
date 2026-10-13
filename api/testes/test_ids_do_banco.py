"""Id fora do tipo do banco é 422, nunca 500 (fechamento do M3).

Os ids das tabelas são `bigint` (até 2**63 - 1). Um número maior chegava ao Postgres e virava
erro 500 em quase toda rota com id; os épicos do M3 consertaram as rotas deles, e o fechamento
levou a regra para o Portal todo com o tipo comum `IdBanco` (`app/esquemas/comum.py`).

O primeiro teste varre o OpenAPI: toda rota com `{..._id}` no caminho, em todo método, recebe um
número fora do `bigint` e tem de responder 422 apontando aquele parâmetro. Rota nova com id entra
sozinha na varredura.
"""

import pytest

from testes.conftest import ADMIN, COMUM

pytestmark = pytest.mark.usefixtures("predio")

FORA_DO_BIGINT = "99999999999999999999"
MAIOR_ID = 2**63 - 1

# O que entra no lugar dos outros parâmetros do caminho (válidos, para só o id estar errado).
OUTROS = {"{versao}": "1", "{login}": COMUM, "{papel}": "comissao"}


def _rotas_com_id() -> list[tuple[str, str, str]]:
    from app.main import app

    rotas = []
    for caminho, operacoes in app.openapi()["paths"].items():
        for metodo in operacoes:
            for parametro in operacoes[metodo].get("parameters", []):
                if parametro["in"] == "path" and parametro["name"].endswith("_id"):
                    rotas.append((metodo.upper(), caminho, parametro["name"]))
    return rotas


def _url(caminho: str, parametro: str) -> str:
    url = caminho.replace("{" + parametro + "}", FORA_DO_BIGINT)
    for marcador, valor in OUTROS.items():
        url = url.replace(marcador, valor)
    # Os outros ids ficam válidos.
    while "_id}" in url:
        inicio = url.index("{")
        url = url[:inicio] + "1" + url[url.index("}", inicio) + 1 :]
    return url


def test_a_varredura_acha_as_rotas_com_id():
    rotas = {(m, c) for m, c, _ in _rotas_com_id()}
    # Algumas de cada área, para a varredura não passar vazia.
    assert ("GET", "/api/avisos/{aviso_id}") in rotas
    assert ("POST", "/api/arquivos/{arquivo_id}/confirmar") in rotas
    assert ("DELETE", "/api/minha-unidade/aparelhos/{sessao_id}") in rotas
    assert ("GET", "/api/documentos/{documento_id}/versoes/{versao}/abrir") in rotas
    assert ("GET", "/api/avisos/{aviso_id}/anexos/{arquivo_id}/abrir") in rotas


def test_id_fora_do_bigint_no_caminho_e_422_em_toda_rota(logar):
    admin = logar(ADMIN)
    erradas = []
    for metodo, caminho, parametro in _rotas_com_id():
        # Corpo vazio: se a rota tem corpo, ele também é recusado, por isso o teste confere que o
        # id aparece entre os campos inválidos (e não só que deu 422).
        resposta = admin.request(metodo, _url(caminho, parametro), json={}, follow_redirects=False)
        campos = (
            [c["campo"] for c in resposta.json().get("campos") or []]
            if resposta.status_code == 422
            else []
        )
        if resposta.status_code != 422 or parametro not in campos:
            erradas.append((metodo, caminho, parametro, resposta.status_code))
    assert erradas == []


@pytest.mark.parametrize("valor", [FORA_DO_BIGINT, "0", "-1"])
def test_historico_antes_de_fora_do_bigint(logar, valor):
    resposta = logar(ADMIN).get(f"/api/admin/historico?antes_de={valor}")
    assert resposta.status_code == 422, resposta.text
    assert resposta.json()["campos"][0]["campo"] == "antes_de"


def test_historico_antes_de_no_limite_do_bigint(logar):
    resposta = logar(ADMIN).get(f"/api/admin/historico?antes_de={MAIOR_ID}")
    assert resposta.status_code == 200, resposta.text


@pytest.mark.parametrize("valor", [FORA_DO_BIGINT, "0", "10"])
def test_alcance_com_bloco_fora_da_faixa(logar, valor):
    resposta = logar(ADMIN).get(f"/api/avisos/alcance?blocos={valor}")
    assert resposta.status_code == 422, resposta.text


def test_id_no_limite_do_bigint_e_so_nao_encontrado(logar):
    # O maior bigint passa da validação e chega ao banco sem erro: só não existe.
    resposta = logar(ADMIN).get(f"/api/avisos/{MAIOR_ID}")
    assert resposta.status_code == 404, resposta.text


@pytest.mark.parametrize(
    ("caminho", "corpo"),
    [
        (
            "/api/documentos",
            {
                "titulo": "Convenção",
                "categoria": "convencao",
                "data_documento": "2026-10-01",
                "acesso": "compradores",
                "arquivo_id": int(FORA_DO_BIGINT),
            },
        ),
        ("/api/documentos/1/versoes", {"arquivo_id": int(FORA_DO_BIGINT)}),
        (
            "/api/avisos",
            {
                "titulo": "Aviso",
                "texto": "Texto.",
                "para_todos": True,
                "anexos": [int(FORA_DO_BIGINT)],
            },
        ),
    ],
)
def test_id_fora_do_bigint_no_corpo(logar, caminho, corpo):
    resposta = logar(ADMIN).post(caminho, json=corpo)
    assert resposta.status_code == 422, resposta.text
    assert resposta.json()["codigo"] == "dados_invalidos"
