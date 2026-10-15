"""Épico A do M4 · regressões da revisão independente (pontos 1, 2, 4, 5, 6 e 9 do
coordenador; o 3, o 7 e o 8 são do front). Cada teste falhava no código de antes da revisão."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from testes.apoio_m4 import votar
from testes.conftest import ADMIN, COMISSAO, COMUM
from testes.test_enquetes_gestao import _opcoes, agendados, corpo, criar, edicao  # noqa: F401

pytestmark = pytest.mark.usefixtures("predio", "agendados")


def _editar(logar, enquete: int, login: str = COMISSAO, **troca: Any):
    return logar(login).put(f"/api/enquetes/{enquete}", json=edicao(**troca))


def _editada_em(engine, enquete: int) -> str:
    with engine.connect() as con:
        valor = con.execute(
            text("select editada_em from enquete where id = :e"), {"e": enquete}
        ).scalar_one()
    return valor.isoformat()


# --- 1. pergunta nova recria as opções ----------------------------------------------------------


def test_pergunta_nova_recria_as_opcoes_e_o_voto_antigo_e_recusado(logar, engine_app, predio):
    gravada = criar(logar, pergunta="Aprovar gasto de R$ 1.000?", opcoes=["Sim", "Não"])
    sim_antigo = _opcoes(engine_app, gravada["id"])[0][0]
    resposta = _editar(
        logar, gravada["id"], pergunta="Aprovar gasto de R$ 10.000?", opcoes=["Sim", "Não"]
    )
    assert resposta.status_code == 200, resposta.text
    novas = _opcoes(engine_app, gravada["id"])
    assert [t for _, t, _ in novas] == ["Sim", "Não"]
    assert sim_antigo not in [i for i, _, _ in novas]
    # A tela antiga (pergunta de R$ 1.000) manda o id velho: o banco recusa.
    with pytest.raises(DBAPIError), engine_app.begin() as con:
        votar(con, gravada["id"], predio[COMUM], sim_antigo)


# --- 2. duas edições ao mesmo tempo -------------------------------------------------------------


def test_editar_com_a_versao_velha_e_recusado(logar, engine_app):
    gravada = criar(logar)
    primeira = _editar(logar, gravada["id"], opcoes=["Terça", "Quinta", "Sábado"])
    assert primeira.status_code == 200, primeira.text
    # A segunda pessoa abriu a tela antes da primeira salvar (`editada_em` nulo).
    segunda = _editar(logar, gravada["id"], ADMIN, pergunta="Outra pergunta?")
    assert segunda.status_code == 409
    assert segunda.json()["codigo"] == "enquete_mudou"
    assert "Abra de novo" in segunda.json()["mensagem"]
    assert [t for _, t, _ in _opcoes(engine_app, gravada["id"])] == ["Terça", "Quinta", "Sábado"]


def test_editar_com_a_versao_certa_passa(logar, engine_app):
    gravada = criar(logar)
    assert _editar(logar, gravada["id"], opcoes=["Sim", "Não"]).status_code == 200
    base = _editada_em(engine_app, gravada["id"])
    resposta = _editar(
        logar, gravada["id"], ADMIN, opcoes=["Sim", "Não", "Tanto faz"], editada_em_base=base
    )
    assert resposta.status_code == 200, resposta.text


def test_base_e_obrigatoria_no_corpo(logar):
    gravada = criar(logar)
    dados = edicao()
    del dados["editada_em_base"]
    resposta = logar(COMISSAO).put(f"/api/enquetes/{gravada['id']}", json=dados)
    assert resposta.status_code == 422
    assert "editada_em_base" in {c["campo"] for c in resposta.json()["campos"]}


# --- 4. perto do fim, sem mexer no término ------------------------------------------------------


def _perto_do_fim(engine, enquete: int) -> datetime:
    perto = datetime.now(UTC).replace(microsecond=0) + timedelta(minutes=30)
    with engine.begin() as con:
        con.execute(
            text("update enquete set encerra_em = :t where id = :e"), {"t": perto, "e": enquete}
        )
    return perto


def test_perto_do_fim_edita_sem_mexer_no_termino(logar, engine_app):
    gravada = criar(logar)
    perto = _perto_do_fim(engine_app, gravada["id"])
    resposta = _editar(
        logar,
        gravada["id"],
        pergunta="Qual o melhor dia? (corrigido)",
        encerra_em=perto.isoformat(),
        editada_em_base=_editada_em(engine_app, gravada["id"]),
    )
    assert resposta.status_code == 200, resposta.text


def test_perto_do_fim_mudar_o_termino_continua_pedindo_1_hora(logar, engine_app):
    gravada = criar(logar)
    perto = _perto_do_fim(engine_app, gravada["id"])
    resposta = _editar(
        logar,
        gravada["id"],
        encerra_em=(perto + timedelta(minutes=10)).isoformat(),
        editada_em_base=_editada_em(engine_app, gravada["id"]),
    )
    assert resposta.status_code == 422
    assert resposta.json()["campos"] == [
        {"campo": "encerra_em", "mensagem": "Escolha um término daqui a pelo menos 1 hora."}
    ]


# --- 5. link com aspas curvas -------------------------------------------------------------------


@pytest.mark.parametrize("fecha", ["”", "’", "»"])
def test_aspas_de_fechamento_nao_entram_no_link(fecha):
    from app.servicos.email import trechos

    linha = f"Viram “https://exemplo.com/planta{fecha}."
    links = [t["link"] for t in trechos(linha) if "link" in t]
    assert links == ["https://exemplo.com/planta"]


def test_o_aviso_com_link_na_pergunta_fica_com_o_link_certo(logar):
    from app.servicos.email import trechos

    gravada = criar(logar, pergunta="Viram a planta em https://exemplo.com/planta")
    aviso = logar(COMUM).get(f"/api/avisos/{gravada['aviso_id']}").json()
    linha = aviso["texto"].split("\n")[0]
    assert [t["link"] for t in trechos(linha) if "link" in t] == ["https://exemplo.com/planta"]


# --- 6. Unicode ---------------------------------------------------------------------------------


def test_opcoes_iguais_depois_de_normalizar(logar):
    resposta = logar(COMISSAO).post("/api/enquetes", json=corpo(opcoes=["Café", "Café"]))
    assert resposta.status_code == 422
    assert resposta.json()["mensagem"] == "Duas opções estão iguais."


def test_grava_normalizado(logar, engine_app):
    gravada = criar(logar, pergunta="Café ou chá?", opcoes=["Café", "Chá"])
    with engine_app.connect() as con:
        pergunta = con.execute(
            text("select pergunta from enquete where id = :e"), {"e": gravada["id"]}
        ).scalar_one()
    assert pergunta == "Café ou chá?"
    assert [t for _, t, _ in _opcoes(engine_app, gravada["id"])] == ["Café", "Chá"]


@pytest.mark.parametrize(
    ("troca", "mensagem"),
    [
        ({"opcoes": ["Sim", "́́"]}, "Cada opção precisa ter letras ou números."),
        ({"opcoes": ["Sim", "?!"]}, "Cada opção precisa ter letras ou números."),
        ({"pergunta": "́?"}, "Escreva a pergunta com letras ou números."),
    ],
)
def test_texto_sem_letra_nem_numero_e_recusado(logar, troca, mensagem):
    resposta = logar(COMISSAO).post("/api/enquetes", json=corpo(**troca))
    assert resposta.status_code == 422
    assert resposta.json()["mensagem"] == mensagem


# --- 9. editar sem os campos não volta ao padrão em silêncio ------------------------------------


@pytest.mark.parametrize("campo", ["multipla_escolha", "mostrar_resultado"])
def test_editar_exige_todos_os_campos(logar, engine_app, campo):
    gravada = criar(logar, multipla_escolha=True, mostrar_resultado="so_no_fim")
    dados = edicao(pergunta="Mudou só a pergunta?")
    del dados[campo]
    resposta = logar(COMISSAO).put(f"/api/enquetes/{gravada['id']}", json=dados)
    assert resposta.status_code == 422
    assert campo in {c["campo"] for c in resposta.json()["campos"]}
    with engine_app.connect() as con:
        linha = con.execute(
            text("select multipla_escolha, mostrar_resultado from enquete where id = :e"),
            {"e": gravada["id"]},
        ).one()
    assert tuple(linha) == (True, "so_no_fim")
