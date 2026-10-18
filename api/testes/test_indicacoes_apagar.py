""" "Apagar meus dados" (H-06) e o reset da gestão (H-08) levam as opiniões e os avisos da
unidade e tiram dela a autoria dos prestadores que indicou (spec de 18/10/2026, seção 6)."""

import pytest
from sqlalchemy import text

from testes.apoio_indicacoes import esconder_opiniao_no_banco, ids_da_lista, indicar
from testes.conftest import ADMIN, COMISSAO, COMUM

pytestmark = pytest.mark.usefixtures("predio")

APAGAR = {"senha": f"senha-{COMUM}", "confirmo": True}


def _contar(engine, tabela: str, unidade: int) -> int:
    with engine.connect() as con:
        return con.execute(
            text(f"select count(*) from {tabela} where unidade_id = :u"), {"u": unidade}
        ).scalar_one()


def _criado_por(engine, prestador: int) -> int | None:
    with engine.connect() as con:
        return con.execute(
            text("select criado_por from prestador where id = :p"), {"p": prestador}
        ).scalar_one()


@pytest.fixture
def cenario(logar, engine_app, predio) -> dict[str, int]:
    """COMUM indicou P1 (opinião visível), opinou em P2 (escondida pela gestão) e avisou P2."""
    comum = logar(COMUM)
    p1 = indicar(comum, telefone="81999990001")
    p2 = indicar(logar(ADMIN), telefone="81999990002", nome="Outro prestador")
    comum.put(f"/api/indicacoes/{p2}/opiniao", json={"recomenda": False, "comentario": "Ruim"})
    esconder_opiniao_no_banco(engine_app, p2, predio[COMUM], predio[COMISSAO])
    assert comum.post(f"/api/indicacoes/{p2}/aviso").status_code == 204
    return {"p1": p1, "p2": p2}


def _conferir_que_levou(logar, engine_app, predio, cenario) -> None:
    assert _contar(engine_app, "opiniao_servico", predio[COMUM]) == 0
    assert _contar(engine_app, "aviso_servico", predio[COMUM]) == 0
    assert _criado_por(engine_app, cenario["p1"]) is None
    # O prestador não some: sem opinião visível, só sai da lista.
    assert logar(ADMIN).get(f"/api/indicacoes/{cenario['p1']}").status_code == 200
    assert cenario["p1"] not in ids_da_lista(logar(ADMIN))
    assert cenario["p2"] in ids_da_lista(logar(ADMIN))
    assert _criado_por(engine_app, cenario["p2"]) == predio[ADMIN]


def test_apagar_meus_dados_leva_opinioes_avisos_e_o_direito_de_corrigir(
    logar, engine_app, predio, cenario
):
    r = logar(COMUM).post("/api/minha-unidade/apagar-dados", json=APAGAR)
    assert r.status_code == 204, r.text
    _conferir_que_levou(logar, engine_app, predio, cenario)


def test_reset_faz_o_mesmo(logar, engine_app, predio, cenario):
    r = logar(ADMIN).post(f"/api/admin/unidades/{COMUM}/resetar", json={"confirmo": True})
    assert r.status_code == 200, r.text
    _conferir_que_levou(logar, engine_app, predio, cenario)


def test_reset_leva_tambem_a_autoria_de_prestador_escondido(logar, engine_app, predio):
    p = indicar(logar(COMUM))
    logar(COMISSAO).post(f"/api/indicacoes/{p}/esconder")
    r = logar(ADMIN).post(f"/api/admin/unidades/{COMUM}/resetar", json={"confirmo": True})
    assert r.status_code == 200, r.text
    assert _criado_por(engine_app, p) is None


def test_proximo_morador_nao_corrige(logar, engine_app, engine_dono, predio, cenario):
    r = logar(ADMIN).post(f"/api/admin/unidades/{COMUM}/resetar", json={"confirmo": True})
    assert r.status_code == 200, r.text
    # O próximo morador ativa a mesma unidade.
    with engine_dono.begin() as con:
        con.execute(
            text(
                "update unidade set precisa_trocar_senha = false, ativada_em = now(),"
                " responsavel_nome = 'Novo morador (fictício)', celular = '81900000099'"
                " where id = :u"
            ),
            {"u": predio[COMUM]},
        )
    novo = logar(COMUM)
    assert novo.get(f"/api/indicacoes/{cenario['p1']}").json()["pode_corrigir"] is False
    r = novo.put(
        f"/api/indicacoes/{cenario['p1']}",
        json={"categoria_id": 1, "nome": "Tomado", "telefone": "81999990001"},
    )
    assert r.status_code == 403
    # E pode dar a própria opinião no prestador que a unidade antiga tinha escondida.
    r = novo.put(f"/api/indicacoes/{cenario['p2']}/opiniao", json={"recomenda": True})
    assert r.status_code == 200
