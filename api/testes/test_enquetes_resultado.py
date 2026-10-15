"""Épico B do M4 · lista, enquete aberta, resultado e "quais apartamentos votaram" (H-21, H-22).

Contrato: `docs/superpowers/specs/m4-contrato.md`, seção 3; spec do épico:
`docs/superpowers/specs/m4-votar.md`.
"""

import pytest
from sqlalchemy import text

from testes.test_enquetes_voto_apoio import (
    ADMIN,
    COMISSAO,
    COMUM,
    nova,
    vencer,
    votar_no_banco,
)

pytestmark = pytest.mark.usefixtures("predio")

NAO_ENCONTRADA = "enquete_nao_encontrada"
UNIDADES_POR_BLOCO = 64


def _ok(resposta) -> dict:
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


# --- quem vê ------------------------------------------------------------------------------------


def test_comum_fora_do_destino_recebe_404_igual_a_inexistente(logar, engine_app, predio):
    so_do_bloco_2 = nova(engine_app, predio, blocos=(2,))
    comum = logar(COMUM)
    fora = comum.get(f"/api/enquetes/{so_do_bloco_2.id}")
    inexistente = comum.get("/api/enquetes/999999")
    assert fora.status_code == inexistente.status_code == 404
    assert fora.json() == inexistente.json()
    assert fora.json()["codigo"] == NAO_ENCONTRADA
    assert _ok(comum.get("/api/enquetes"))["itens"] == []


def test_gestao_ve_todas_mas_so_vota_no_destino(logar, engine_app, predio):
    so_do_bloco_1 = nova(engine_app, predio, blocos=(1,))
    comissao = _ok(logar(COMISSAO).get(f"/api/enquetes/{so_do_bloco_1.id}"))
    assert comissao["pode_votar"] is False
    assert comissao["blocos"] == [1]
    assert _ok(logar(COMUM).get(f"/api/enquetes/{so_do_bloco_1.id}"))["pode_votar"] is True
    assert [e["id"] for e in _ok(logar(COMISSAO).get("/api/enquetes"))["itens"]] == [
        so_do_bloco_1.id
    ]


# --- lista --------------------------------------------------------------------------------------


def test_lista_abertas_primeiro_depois_terminadas(logar, engine_app, engine_superusuario, predio):
    longe = nova(engine_app, predio, dias=20, pergunta="Termina longe?")
    perto = nova(engine_app, predio, dias=2, pergunta="Termina perto?")
    antiga = nova(engine_app, predio, pergunta="Terminou faz tempo?")
    recente = nova(engine_app, predio, pergunta="Terminou agora?")
    vencer(engine_superusuario, antiga.id, minutos=600)
    vencer(engine_superusuario, recente.id, minutos=5)
    itens = _ok(logar(COMUM).get("/api/enquetes"))["itens"]
    assert [i["id"] for i in itens] == [perto.id, longe.id, recente.id, antiga.id]
    assert [i["encerrada"] for i in itens] == [False, False, True, True]


def test_lista_empate_pelo_id_mais_novo(logar, engine_app, engine_superusuario, predio):
    a = nova(engine_app, predio)
    b = nova(engine_app, predio)
    with engine_superusuario.begin() as con:
        con.execute(text("set local session_replication_role = replica"))
        con.execute(
            text("update enquete set encerra_em = (select encerra_em from enquete where id = :a)"),
            {"a": a.id},
        )
    assert [i["id"] for i in _ok(logar(COMUM).get("/api/enquetes"))["itens"]] == [b.id, a.id]


def test_lista_diz_se_a_unidade_ja_votou(logar, engine_app, predio):
    votada = nova(engine_app, predio)
    pendente = nova(engine_app, predio)
    votar_no_banco(engine_app, votada.id, predio[COMUM], votada.opcoes[0])
    itens = {i["id"]: i for i in _ok(logar(COMUM).get("/api/enquetes"))["itens"]}
    assert itens[votada.id]["ja_votou"] is True
    assert itens[pendente.id]["ja_votou"] is False
    # O voto é do apartamento, não da pessoa: outra unidade do mesmo bloco não "herda".
    assert all(not i["ja_votou"] for i in _ok(logar(ADMIN).get("/api/enquetes"))["itens"])


def test_resumo_tem_os_campos_do_contrato(logar, engine_app, predio):
    criada = nova(engine_app, predio, blocos=(1, 3), multipla=True)
    [item] = _ok(logar(COMUM).get("/api/enquetes"))["itens"]
    assert item["id"] == criada.id
    assert item["pergunta"] == "Qual o melhor dia para a reunião?"
    assert item["multipla_escolha"] is True
    assert item["mostrar_resultado"] == "durante"
    assert item["para_todos"] is False
    assert item["blocos"] == [1, 3]
    assert item["editada_em"] is None
    assert set(item) >= {"encerra_em", "criada_em", "encerrada", "ja_votou"}
    assert "opcoes" not in item


# --- enquete aberta e resultado ----------------------------------------------------------------


def test_resultado_durante_mostra_votos_e_participacao(logar, engine_app, predio):
    criada = nova(engine_app, predio)
    a, b, c = criada.opcoes
    votar_no_banco(engine_app, criada.id, predio[COMUM], b)
    votar_no_banco(engine_app, criada.id, predio[ADMIN], b)
    votar_no_banco(engine_app, criada.id, predio[COMISSAO], a)
    enquete = _ok(logar(COMUM).get(f"/api/enquetes/{criada.id}"))
    assert [(o["id"], o["texto"], o["votos"]) for o in enquete["opcoes"]] == [
        (a, "Terça à noite", 1),
        (b, "Quinta à noite", 2),
        (c, "Sábado de manhã", 0),
    ]
    assert enquete["resultado_visivel"] is True
    assert enquete["participacao"] == {"votaram": 3, "total": 5 * UNIDADES_POR_BLOCO}
    assert enquete["meu_voto"] == [b]
    assert enquete["votado_em"] is not None
    assert enquete["ja_votou"] is True
    assert enquete["aviso_id"] == criada.aviso_id
    assert enquete["encerrada"] is False


def test_quem_nao_votou_ve_meu_voto_vazio(logar, engine_app, predio):
    criada = nova(engine_app, predio)
    enquete = _ok(logar(COMUM).get(f"/api/enquetes/{criada.id}"))
    assert enquete["meu_voto"] == []
    assert enquete["votado_em"] is None
    assert enquete["ja_votou"] is False
    assert enquete["participacao"]["votaram"] == 0


def test_participacao_conta_so_o_destino(logar, engine_app, predio):
    criada = nova(engine_app, predio, blocos=(1,))
    votar_no_banco(engine_app, criada.id, predio[COMUM], criada.opcoes[0])
    enquete = _ok(logar(COMUM).get(f"/api/enquetes/{criada.id}"))
    assert enquete["participacao"] == {"votaram": 1, "total": UNIDADES_POR_BLOCO}


def test_participacao_com_unidade_desativada_depois(logar, engine_app, engine_dono, predio):
    """Dúvida 13 do contrato: o total é o de agora (ativas); o voto de quem saiu continua."""
    criada = nova(engine_app, predio, blocos=(1,))
    votar_no_banco(engine_app, criada.id, predio[COMUM], criada.opcoes[0])
    with engine_dono.begin() as con:
        con.execute(
            text("update unidade set ativa = false where login in ('1203', '1204')"),
        )
    enquete = _ok(logar(ADMIN).get(f"/api/enquetes/{criada.id}"))
    # Revisão, ponto 2: quem votou e saiu continua na base (63 = 62 ativas + a que votou), e o
    # 1204, que saiu sem votar, não conta mais.
    assert enquete["participacao"] == {"votaram": 1, "total": UNIDADES_POR_BLOCO - 1}
    assert enquete["opcoes"][0]["votos"] == 1


@pytest.mark.parametrize("login", [COMUM, COMISSAO, ADMIN])
def test_so_no_fim_esconde_os_votos_de_todos_enquanto_aberta(logar, engine_app, predio, login):
    """Dúvida 4 do contrato: nem a gestão vê o parcial."""
    criada = nova(engine_app, predio, so_no_fim=True)
    votar_no_banco(engine_app, criada.id, predio[COMUM], criada.opcoes[1])
    enquete = _ok(logar(login).get(f"/api/enquetes/{criada.id}"))
    assert enquete["resultado_visivel"] is False
    assert [o["votos"] for o in enquete["opcoes"]] == [None, None, None]
    assert enquete["participacao"]["votaram"] == 1


def test_so_no_fim_mostra_o_proprio_voto(logar, engine_app, predio):
    """Esconder o resultado não esconde da unidade o que ela mesma marcou."""
    criada = nova(engine_app, predio, so_no_fim=True)
    votar_no_banco(engine_app, criada.id, predio[COMUM], criada.opcoes[1])
    assert _ok(logar(COMUM).get(f"/api/enquetes/{criada.id}"))["meu_voto"] == [criada.opcoes[1]]


def test_so_no_fim_mostra_tudo_depois_do_prazo(logar, engine_app, engine_superusuario, predio):
    criada = nova(engine_app, predio, so_no_fim=True)
    votar_no_banco(engine_app, criada.id, predio[COMUM], criada.opcoes[1])
    vencer(engine_superusuario, criada.id)
    enquete = _ok(logar(COMUM).get(f"/api/enquetes/{criada.id}"))
    assert enquete["encerrada"] is True
    assert enquete["resultado_visivel"] is True
    assert [o["votos"] for o in enquete["opcoes"]] == [0, 1, 0]
    assert enquete["pode_votar"] is False


def test_multipla_escolha_conta_cada_opcao(logar, engine_app, predio):
    criada = nova(engine_app, predio, multipla=True)
    a, b, c = criada.opcoes
    votar_no_banco(engine_app, criada.id, predio[COMUM], a, c)
    votar_no_banco(engine_app, criada.id, predio[ADMIN], c)
    enquete = _ok(logar(COMUM).get(f"/api/enquetes/{criada.id}"))
    assert [o["votos"] for o in enquete["opcoes"]] == [1, 0, 2]
    assert enquete["participacao"]["votaram"] == 2
    assert sorted(enquete["meu_voto"]) == [a, c]


# --- pode editar --------------------------------------------------------------------------------


def test_pode_editar_so_gestao_aberta_e_sem_voto(logar, engine_app, engine_superusuario, predio):
    criada = nova(engine_app, predio)
    assert _ok(logar(COMISSAO).get(f"/api/enquetes/{criada.id}"))["pode_editar"] is True
    assert _ok(logar(ADMIN).get(f"/api/enquetes/{criada.id}"))["pode_editar"] is True
    assert _ok(logar(COMUM).get(f"/api/enquetes/{criada.id}"))["pode_editar"] is False
    votar_no_banco(engine_app, criada.id, predio[COMUM], criada.opcoes[0])
    assert _ok(logar(COMISSAO).get(f"/api/enquetes/{criada.id}"))["pode_editar"] is False
    sem_voto = nova(engine_app, predio)
    vencer(engine_superusuario, sem_voto.id)
    assert _ok(logar(COMISSAO).get(f"/api/enquetes/{sem_voto.id}"))["pode_editar"] is False


# --- quais apartamentos votaram (H-22) ----------------------------------------------------------


def test_votantes_sem_dizer_em_que(logar, engine_app, predio):
    criada = nova(engine_app, predio, blocos=(1,), so_no_fim=True)
    votar_no_banco(engine_app, criada.id, predio[COMUM], criada.opcoes[2])
    votantes = _ok(logar(COMISSAO).get(f"/api/enquetes/{criada.id}/votantes"))
    assert votantes["votaram"] == [{"login": COMUM, "bloco": 1, "apartamento": "203"}]
    # O admin (1101) entrou e não votou; o resto do Bloco 1 nem entrou.
    assert votantes["entraram_sem_votar"] == [{"login": ADMIN, "bloco": 1, "apartamento": "101"}]
    assert len(votantes["nao_entraram"]) == UNIDADES_POR_BLOCO - 2
    assert all(u["bloco"] == 1 for u in votantes["nao_entraram"])
    logins = [u["login"] for u in votantes["nao_entraram"]]
    assert logins == sorted(logins)
    assert "opcao" not in str(votantes) and "Quinta" not in str(votantes)


def test_votantes_inclui_quem_votou_e_foi_desativado(logar, engine_app, engine_dono, predio):
    criada = nova(engine_app, predio, blocos=(1,), so_no_fim=True)
    votar_no_banco(engine_app, criada.id, predio[COMUM], criada.opcoes[0])
    with engine_dono.begin() as con:
        con.execute(text("update unidade set ativa = false where login = '1203'"))
    votantes = _ok(logar(COMISSAO).get(f"/api/enquetes/{criada.id}/votantes"))
    assert [u["login"] for u in votantes["votaram"]] == [COMUM]
    todos = votantes["votaram"] + votantes["entraram_sem_votar"] + votantes["nao_entraram"]
    assert len(todos) == UNIDADES_POR_BLOCO


def test_votantes_de_enquete_inexistente_404(logar):
    resposta = logar(COMISSAO).get("/api/enquetes/999999/votantes")
    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == NAO_ENCONTRADA


def test_votantes_so_para_a_gestao(logar, engine_app, predio):
    criada = nova(engine_app, predio)
    assert logar(COMUM).get(f"/api/enquetes/{criada.id}/votantes").status_code == 403


# --- revisão do épico B -------------------------------------------------------------------------


def test_participacao_nunca_passa_do_total(logar, engine_app, engine_dono, predio):
    """Revisão, ponto 2: votaram e desativadas depois davam "1 de 1" (o admin, que não votou,
    era o único da base) e mais de 100%."""
    criada = nova(engine_app, predio, blocos=(1,))
    votar_no_banco(engine_app, criada.id, predio[COMUM], criada.opcoes[0])
    with engine_dono.begin() as con:
        outra = con.execute(text("select id from unidade where login = '1102'")).scalar_one()
    votar_no_banco(engine_app, criada.id, outra, criada.opcoes[0])
    with engine_dono.begin() as con:
        con.execute(
            text("update unidade set ativa = false where login like '1%' and login <> :a"),
            {"a": ADMIN},
        )
    participacao = _ok(logar(ADMIN).get(f"/api/enquetes/{criada.id}"))["participacao"]
    # A base: o admin (ativo, não votou) e as duas que votaram e saíram.
    assert participacao == {"votaram": 2, "total": 3}


def test_votantes_somam_o_total_da_participacao(logar, engine_app, engine_dono, predio):
    criada = nova(engine_app, predio, blocos=(1,), so_no_fim=True)
    votar_no_banco(engine_app, criada.id, predio[COMUM], criada.opcoes[0])
    with engine_dono.begin() as con:
        con.execute(text("update unidade set ativa = false where login in ('1203', '1204')"))
    comissao = logar(COMISSAO)
    total = _ok(comissao.get(f"/api/enquetes/{criada.id}"))["participacao"]
    votantes = _ok(comissao.get(f"/api/enquetes/{criada.id}/votantes"))
    todos = votantes["votaram"] + votantes["entraram_sem_votar"] + votantes["nao_entraram"]
    assert len(votantes["votaram"]) == total["votaram"]
    assert len(todos) == total["total"]


def test_votantes_no_durante_so_depois_do_fim(logar, engine_app, engine_superusuario, predio):
    """Revisão, ponto 1: no "durante", a contagem ao vivo menos a contagem de antes, cruzada com
    quem entrou na lista, diz em quê cada apartamento votou. A lista só sai no fim."""
    criada = nova(engine_app, predio)
    votar_no_banco(engine_app, criada.id, predio[COMUM], criada.opcoes[2])
    comissao = logar(COMISSAO)
    resposta = comissao.get(f"/api/enquetes/{criada.id}/votantes")
    assert resposta.status_code == 409
    corpo = resposta.json()
    assert corpo["codigo"] == "votantes_so_no_fim"
    assert "só no fim" in corpo["mensagem"]
    assert COMUM not in resposta.text
    vencer(engine_superusuario, criada.id)
    votantes = _ok(comissao.get(f"/api/enquetes/{criada.id}/votantes"))
    assert [u["login"] for u in votantes["votaram"]] == [COMUM]


def test_votantes_no_so_no_fim_aberta(logar, engine_app, predio):
    criada = nova(engine_app, predio, so_no_fim=True)
    votar_no_banco(engine_app, criada.id, predio[COMUM], criada.opcoes[2])
    votantes = _ok(logar(COMISSAO).get(f"/api/enquetes/{criada.id}/votantes"))
    assert [u["login"] for u in votantes["votaram"]] == [COMUM]
