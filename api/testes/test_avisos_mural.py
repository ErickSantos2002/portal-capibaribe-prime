"""H-14 · Mural: ordem, não lidos, busca, destino; e "Avisos arquivados" (H-15)."""

import pytest
from sqlalchemy import text

from testes.test_avisos_apoio import ADMIN, COMISSAO, COMUM, publicar

pytestmark = pytest.mark.usefixtures("predio")


def _titulos(cliente, **consulta) -> list[str]:
    resposta = cliente.get("/api/avisos", params=consulta)
    assert resposta.status_code == 200, resposta.text
    return [item["titulo"] for item in resposta.json()["itens"]]


# --- H-14: fixados primeiro; depois do mais novo para o mais antigo ---------------------------


def test_ordem_do_mural(logar):
    comissao = logar(COMISSAO)
    publicar(comissao, titulo="Primeiro")
    publicar(comissao, titulo="Fixado antigo", fixado=True)
    publicar(comissao, titulo="Segundo")
    publicar(comissao, titulo="Fixado novo", fixado=True)
    publicar(comissao, titulo="Terceiro")
    assert _titulos(logar(COMUM)) == [
        "Fixado novo",
        "Fixado antigo",
        "Terceiro",
        "Segundo",
        "Primeiro",
    ]


def test_empate_de_data_vai_pelo_mais_recente(engine_app, predio, logar):
    # Na mesma transação, now() é o mesmo: os dois avisos têm a mesma data.
    with engine_app.begin() as con:
        for titulo in ("A", "B"):
            aviso_id = con.execute(
                text(
                    "insert into aviso (publicado_por, publicado_como, para_todos)"
                    " values (:u, 'comissao', true) returning id"
                ),
                {"u": predio[COMISSAO]},
            ).scalar_one()
            con.execute(
                text(
                    "insert into aviso_versao (aviso_id, versao, titulo, texto, criada_por)"
                    " values (:a, 1, :t, 'Texto', :u)"
                ),
                {"a": aviso_id, "t": titulo, "u": predio[COMISSAO]},
            )
    assert _titulos(logar(COMUM)) == ["B", "A"]


def test_item_do_mural(logar):
    aviso = publicar(
        logar(COMISSAO),
        titulo="Reunião",
        texto="Primeira linha\ncontinua aqui.\n\nSegundo parágrafo.",
        para_todos=False,
        blocos=[1, 2],
    )
    item = logar(COMUM).get("/api/avisos").json()["itens"][0]
    assert item == {
        "id": aviso["id"],
        "titulo": "Reunião",
        "resumo": "Primeira linha continua aqui.",
        "publicado_em": aviso["publicado_em"],
        "publicado_por": "Comissão",
        "editado_em": None,
        "fixado": False,
        "para_todos": False,
        "blocos": [1, 2],
        "arquivado_em": None,
        "lido": False,
    }


def test_resumo_corta_em_200(logar):
    publicar(logar(COMISSAO), texto="palavra " * 60)
    resumo = logar(COMUM).get("/api/avisos").json()["itens"][0]["resumo"]
    assert len(resumo) == 200
    assert resumo.endswith("…")


# --- H-14: aviso ainda não lido aparece destacado ---------------------------------------------


def test_lido_por_unidade(logar):
    aviso = publicar(logar(COMISSAO))
    comum = logar(COMUM)
    assert comum.get("/api/avisos").json()["itens"][0]["lido"] is False
    assert comum.get("/api/avisos/nao-lidos").json() == {"quantidade": 1}

    assert comum.post(f"/api/avisos/{aviso['id']}/lido").status_code == 204

    assert comum.get("/api/avisos").json()["itens"][0]["lido"] is True
    assert comum.get("/api/avisos/nao-lidos").json() == {"quantidade": 0}
    # Para quem publicou, já estava lido.
    assert logar(COMISSAO).get("/api/avisos").json()["itens"][0]["lido"] is True


def test_nao_lidos_ignora_arquivado_e_outro_bloco(logar):
    comissao = logar(COMISSAO)
    publicar(comissao, titulo="Para todos")
    publicar(comissao, titulo="Bloco 1", para_todos=False, blocos=[1])
    publicar(comissao, titulo="Bloco 3", para_todos=False, blocos=[3])
    arquivado = publicar(comissao, titulo="Arquivado")
    comissao.post(f"/api/avisos/{arquivado['id']}/arquivar")
    assert logar(COMUM).get("/api/avisos/nao-lidos").json() == {"quantidade": 2}


# --- H-14: só os avisos cujo destino inclui o bloco da unidade --------------------------------


def test_mural_so_do_bloco(logar):
    comissao = logar(COMISSAO)
    publicar(comissao, titulo="Para todos")
    publicar(comissao, titulo="Blocos 1 e 2", para_todos=False, blocos=[1, 2])
    publicar(comissao, titulo="Bloco 4", para_todos=False, blocos=[4])
    # 1203 é do Bloco 1.
    assert _titulos(logar(COMUM)) == ["Blocos 1 e 2", "Para todos"]
    # A gestão vê todos (precisa corrigir e conferir qualquer aviso).
    assert _titulos(logar(ADMIN)) == ["Bloco 4", "Blocos 1 e 2", "Para todos"]


# --- H-14: busca no título e no texto ---------------------------------------------------------


@pytest.fixture
def avisos_para_buscar(logar):
    comissao = logar(COMISSAO)
    publicar(comissao, titulo="Fundação do Bloco 4 concluída", texto="A engenharia enviou fotos.")
    publicar(comissao, titulo="Reunião", texto="No salão da igreja da Várzea, às 19h.")
    publicar(comissao, titulo="Boas-vindas", texto="Coloque o Portal na tela inicial.", fixado=True)


@pytest.mark.parametrize(
    ("busca", "esperado"),
    [
        ("fundacao", ["Fundação do Bloco 4 concluída"]),
        ("FUNDAÇÃO", ["Fundação do Bloco 4 concluída"]),
        ("varzea", ["Reunião"]),
        ("  igreja   salao ", ["Reunião"]),
        ("concluida bloco", ["Fundação do Bloco 4 concluída"]),
        ("tela inicial", ["Boas-vindas"]),
        ("piscina", []),
        ("", ["Boas-vindas", "Reunião", "Fundação do Bloco 4 concluída"]),
    ],
)
def test_busca(logar, avisos_para_buscar, busca, esperado):
    assert _titulos(logar(COMUM), busca=busca) == esperado


def test_busca_procura_so_na_versao_em_vigor(logar):
    aviso = publicar(logar(COMISSAO), titulo="Reunião às 19h", texto="No salão.")
    logar(COMISSAO).put(
        f"/api/avisos/{aviso['id']}", json={"titulo": "Reunião às 20h", "texto": "No salão."}
    )
    assert _titulos(logar(COMUM), busca="19h") == []
    assert _titulos(logar(COMUM), busca="20h") == ["Reunião às 20h"]


def test_busca_longa_demais(logar):
    resposta = logar(COMUM).get("/api/avisos", params={"busca": "x" * 101})
    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "dados_invalidos"


# --- H-15: arquivados ---------------------------------------------------------------------------


def test_arquivados_tem_lista_propria(logar):
    comissao = logar(COMISSAO)
    publicar(comissao, titulo="No mural")
    velho = publicar(comissao, titulo="Arquivado velho")
    novo = publicar(comissao, titulo="Arquivado novo", fixado=True)
    outro_bloco = publicar(comissao, titulo="Arquivado do Bloco 3", para_todos=False, blocos=[3])
    for aviso in (novo, velho, outro_bloco):
        assert comissao.post(f"/api/avisos/{aviso['id']}/arquivar").status_code == 200

    comum = logar(COMUM)
    assert _titulos(comum) == ["No mural"]
    assert _titulos(comum, arquivados="true") == ["Arquivado novo", "Arquivado velho"]
    assert _titulos(comum, arquivados="true", busca="velho") == ["Arquivado velho"]
    item = comum.get("/api/avisos", params={"arquivados": "true"}).json()["itens"][0]
    assert item["arquivado_em"] is not None
