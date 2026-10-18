"""Indicações pela API: categorias, lista, busca, parecidos, indicar e abrir (spec de
18/10/2026, seções 3.1, 3.3, 4 e 7). As regras do banco têm os próprios testes de burla
(`test_indicacoes_banco.py`)."""

from unittest.mock import ANY

import pytest

from app.modelos.indicacoes import CATEGORIAS_INICIAIS
from app.servicos.indicacoes import normalizar
from testes.apoio_indicacoes import (
    NOVA,
    categoria_da_api,
    esconder_opiniao_no_banco,
    esconder_prestador_no_banco,
    ids_da_lista,
    indicar,
    opinar_no_banco,
)
from testes.conftest import ADMIN, COMISSAO, COMUM

pytestmark = pytest.mark.usefixtures("predio")


def test_normalizar():
    assert normalizar("  JOÃO   da  Silva ") == "joao da silva"
    assert normalizar("Marcenária & Filhos") == "marcenaria & filhos"


def test_categorias_na_ordem(logar):
    itens = logar(COMUM).get("/api/indicacoes/categorias").json()["itens"]
    assert [c["nome"] for c in itens] == [n for n, _ in CATEGORIAS_INICIAIS]


def test_indicar_cria_prestador_e_primeira_opiniao(logar, predio):
    r = logar(COMUM).post("/api/indicacoes", json=NOVA)
    assert r.status_code == 201, r.text
    p = logar(COMISSAO).get(f"/api/indicacoes/{r.json()['id']}").json()
    assert p["nome"] == "Marcenaria Exemplo" and p["telefone"] == "81999990001"
    assert p["celular"] is True and p["categoria"]["nome"] == "Móveis planejados"
    assert p["recomendam"] == 1 and p["nao_recomendam"] == 0
    assert p["opinioes"][0]["unidade"] == {"login": "1203", "bloco": 1, "apartamento": "203"}
    assert p["opinioes"][0]["comentario"] == "Fez a cozinha no prazo."
    assert p["opinioes"][0]["minha"] is False
    assert "Responsável" not in str(p) and "responsavel" not in r.text


def test_quem_indicou_ve_a_propria_opiniao_e_pode_corrigir(logar):
    p = indicar(logar(COMUM))
    eu = logar(COMUM).get(f"/api/indicacoes/{p}").json()
    assert eu["minha_opiniao"] == {
        "recomenda": True,
        "comentario": "Fez a cozinha no prazo.",
        "escondida": False,
    }
    assert eu["opinioes"][0]["minha"] is True
    assert eu["pode_corrigir"] is True and eu["ja_avisei"] is False
    assert eu["escondido"] is False and eu["avisos"] is None
    outro = logar(COMISSAO).get(f"/api/indicacoes/{p}").json()
    assert outro["minha_opiniao"] is None and outro["pode_corrigir"] is True  # gestão
    assert outro["avisos"] == []


@pytest.mark.parametrize("mesmo", ["(81) 9 9999-0001", "+55 81 99999 0001", "81999990001"])
def test_telefone_igual_com_mascara_da_409_com_id(logar, mesmo):
    criado = indicar(logar(COMUM))
    r = logar(ADMIN).post("/api/indicacoes", json={**NOVA, "telefone": mesmo, "nome": "Outro"})
    assert r.status_code == 409
    assert r.json() == {"codigo": "prestador_ja_existe", "mensagem": ANY, "id": criado}


def test_telefone_de_escondido_da_409_sem_id(logar, engine_app, predio):
    criado = indicar(logar(COMUM))
    esconder_prestador_no_banco(engine_app, criado, predio[COMISSAO])
    r = logar(ADMIN).post("/api/indicacoes", json={**NOVA, "nome": "Outro"})
    assert r.status_code == 409
    assert r.json()["codigo"] == "prestador_indisponivel" and "id" not in r.json()
    assert r.json()["mensagem"] == "Esse prestador não está disponível no Portal."


def test_ordem_mais_recomendados_e_desempate_pela_mais_recente(logar, engine_app, predio):
    comum = logar(COMUM)
    a = indicar(comum, nome="Primeiro", telefone="81999990001")
    b = indicar(comum, nome="Segundo", telefone="81999990002")
    c = indicar(comum, nome="Terceiro", telefone="81999990003", recomenda=False)
    d = indicar(comum, nome="Quarto", telefone="81999990004")
    # b ganha mais duas recomendações; a e d empatam com 1, e a tem a opinião mais recente
    # (um "não recomendo" não muda a contagem de quem recomenda).
    opinar_no_banco(engine_app, b, predio[ADMIN])
    opinar_no_banco(engine_app, b, predio[COMISSAO])
    opinar_no_banco(engine_app, a, predio[ADMIN], recomenda=False)
    assert ids_da_lista(comum) == [b, a, d, c]
    lista = comum.get("/api/indicacoes").json()["itens"]
    por_id = {i["id"]: i for i in lista}
    assert (por_id[b]["recomendam"], por_id[b]["nao_recomendam"]) == (3, 0)
    assert (por_id[a]["recomendam"], por_id[a]["nao_recomendam"]) == (1, 1)
    assert (por_id[c]["recomendam"], por_id[c]["nao_recomendam"]) == (0, 1)


def test_cartao_traz_o_trecho_mais_recente_com_comentario(logar, engine_app, predio):
    p = indicar(logar(COMUM), comentario="Primeira impressão")
    opinar_no_banco(engine_app, p, predio[ADMIN], comentario="Voltou para ajustar, ótimo")
    opinar_no_banco(engine_app, p, predio[COMISSAO])  # sem comentário: não vira trecho
    cartao = logar(COMUM).get("/api/indicacoes").json()["itens"][0]
    assert cartao["trecho"] == {
        "unidade": {"login": "1101", "bloco": 1, "apartamento": "101"},
        "comentario": "Voltou para ajustar, ótimo",
        "em": ANY,
    }
    assert cartao["categoria"] == {"id": 1, "nome": "Móveis planejados"}


@pytest.fixture
def tres(logar):
    comum = logar(COMUM)
    return {
        "joao": indicar(comum, nome="João da Silva", telefone="81999990001", categoria_id=7),
        "fios": indicar(
            comum, nome="Fios & Cia", telefone="81999990002", categoria_id=5, comentario=None
        ),
        "eletrica": indicar(
            comum, nome="Instalação Elétrica Rápida", telefone="81999990003", categoria_id=11
        ),
        "limpa": indicar(
            comum,
            nome="Casa Limpa",
            telefone="81999990004",
            categoria_id=10,
            comentario="Muito pontual",
        ),
    }


@pytest.mark.parametrize(
    ("termo", "esperados"),
    [
        ("joao", ["joao"]),
        ("JOÃO", ["joao"]),
        ("  joão  ", ["joao"]),
        ("eletrica", ["eletrica"]),
        ("ELETRICISTA", ["fios"]),
        ("pontual", ["limpa"]),
    ],
)
def test_busca_sem_acento_nem_maiuscula_acha_nome_categoria_e_comentario(
    logar, tres, termo, esperados
):
    assert sorted(ids_da_lista(logar(COMUM), busca=termo)) == sorted(tres[e] for e in esperados)


@pytest.mark.parametrize("vazia", ["", "   "])
def test_busca_vazia_e_igual_a_sem_busca(logar, tres, vazia):
    comum = logar(COMUM)
    assert ids_da_lista(comum, busca=vazia) == ids_da_lista(comum)
    assert len(ids_da_lista(comum)) == 4


def test_busca_nao_acha_comentario_escondido(logar, engine_app, predio, tres):
    esconder_opiniao_no_banco(engine_app, tres["limpa"], predio[COMUM], predio[COMISSAO])
    assert ids_da_lista(logar(COMUM), busca="pontual") == []


def test_filtro_por_categoria(logar, tres):
    comum = logar(COMUM)
    eletricista = categoria_da_api(comum, "Eletricista")
    assert ids_da_lista(comum, categoria=eletricista) == [tres["fios"]]
    assert ids_da_lista(comum, categoria=eletricista, busca="joao") == []


def test_prestador_sem_opiniao_visivel_sai_da_lista_mas_abre(logar, engine_app, predio):
    p = indicar(logar(COMUM))
    esconder_opiniao_no_banco(engine_app, p, predio[COMUM], predio[COMISSAO])
    assert ids_da_lista(logar(ADMIN)) == []
    aberto = logar(ADMIN).get(f"/api/indicacoes/{p}")
    assert aberto.status_code == 200
    assert aberto.json()["opinioes"] == [] and aberto.json()["recomendam"] == 0
    # Uma opinião nova o traz de volta.
    opinar_no_banco(engine_app, p, predio[ADMIN])
    assert ids_da_lista(logar(ADMIN)) == [p]


def test_escondido_404_para_morador_e_aberto_para_a_gestao(logar, engine_app, predio):
    p = indicar(logar(COMUM))
    esconder_prestador_no_banco(engine_app, p, predio[COMISSAO])
    r = logar(COMUM).get(f"/api/indicacoes/{p}")
    assert (r.status_code, r.json()["codigo"]) == (404, "indicacao_nao_encontrada")
    gestao = logar(COMISSAO).get(f"/api/indicacoes/{p}").json()
    assert gestao["escondido"] is True
    assert ids_da_lista(logar(COMISSAO)) == []


def test_parecidos_ate_3_sem_escondidos(logar, engine_app, predio):
    comum, admin = logar(COMUM), logar(ADMIN)
    silva = indicar(comum, nome="Marcenaria Silva", telefone="81999990001")
    filhos = indicar(comum, nome="Marcenária Silva & Filhos", telefone="81999990002")
    opinar_no_banco(engine_app, filhos, predio[ADMIN])
    indicar(comum, nome="Silva Marcenaria", telefone="81999990003")
    souza = indicar(comum, nome="Marcenaria Souza", telefone="81999990004")
    indicar(comum, nome="Marcenaria Exemplo", telefone="81999990005", recomenda=False)
    escondido = indicar(comum, nome="Marcenaria Silva Velha", telefone="81999990006")
    esconder_prestador_no_banco(engine_app, escondido, predio[COMISSAO])
    r = admin.get("/api/indicacoes/parecidos", params={"nome": "marcenaria  silva"})
    assert r.status_code == 200
    itens = r.json()["itens"]
    assert [i["id"] for i in itens] == [filhos, silva, souza]
    assert itens[0]["categoria"]["nome"] == "Móveis planejados"


@pytest.mark.parametrize("curto", ["", "Ma", "  m  "])
def test_parecidos_so_com_3_letras(logar, curto):
    indicar(logar(COMUM), nome="Marcenaria Silva")
    r = logar(COMUM).get("/api/indicacoes/parecidos", params={"nome": curto})
    assert r.json() == {"itens": []}


def test_parecidos_por_trecho_do_nome(logar):
    p = indicar(logar(COMUM), nome="Marcenaria Silva")
    r = logar(COMUM).get("/api/indicacoes/parecidos", params={"nome": "Marcen"})
    assert [i["id"] for i in r.json()["itens"]] == [p]


def test_morador_nao_ve_campos_da_gestao(logar, predio):
    indicar(logar(COMUM))
    lista = logar(COMUM).get("/api/indicacoes").json()
    assert lista["com_aviso"] is None and lista["itens"][0]["avisos_abertos"] is None
    gestao = logar(ADMIN).get("/api/indicacoes").json()
    assert gestao["com_aviso"] == 0 and gestao["itens"][0]["avisos_abertos"] == 0
    # `com_aviso=1` do morador é ignorado.
    assert len(logar(COMUM).get("/api/indicacoes", params={"com_aviso": "1"}).json()["itens"]) == 1


def test_sem_sessao_401_e_id_fora_da_faixa_422(cliente, logar):
    assert cliente.get("/api/indicacoes").status_code == 401
    assert cliente.get("/api/indicacoes/categorias").status_code == 401
    assert cliente.post("/api/indicacoes", json=NOVA, headers={"X-Portal": "1"}).status_code == 401
    comum = logar(COMUM)
    assert comum.get("/api/indicacoes/9223372036854775808").status_code == 422
    assert comum.get("/api/indicacoes/0").status_code == 422
    assert comum.get("/api/indicacoes/9999").status_code == 404
    assert comum.get("/api/indicacoes", params={"categoria": "0"}).status_code == 422


def test_sem_cabecalho_portal_403(logar, cliente):
    comum = logar(COMUM)
    comum.headers.pop("X-Portal")
    assert comum.post("/api/indicacoes", json=NOVA).status_code == 403


def test_categoria_inexistente_422(logar):
    r = logar(COMUM).post("/api/indicacoes", json={**NOVA, "categoria_id": 9999})
    assert (r.status_code, r.json()["codigo"]) == (422, "categoria_inexistente")


def test_dados_invalidos_422(logar):
    r = logar(COMUM).post("/api/indicacoes", json={**NOVA, "telefone": "123"})
    assert r.status_code == 422 and r.json()["campos"][0]["campo"] == "telefone"
    sem = {k: v for k, v in NOVA.items() if k != "recomenda"}
    assert logar(COMUM).post("/api/indicacoes", json=sem).status_code == 422


def test_limite_do_dia_vira_429(logar):
    comum = logar(COMUM)
    for i in range(10):
        indicar(comum, telefone=f"8199999{i:04d}")
    r = comum.post("/api/indicacoes", json={**NOVA, "telefone": "81999998888"})
    assert (r.status_code, r.json()["codigo"]) == (429, "limite_do_dia")
    assert "indicações" in r.json()["mensagem"]
