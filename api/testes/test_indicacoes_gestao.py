"""Moderação das indicações: esconder, resolver aviso e categorias (spec de 18/10/2026, seções
3.2, 4 e 8). Esconder e resolver: a gestão (Comissão e administração). Categorias: só a
administração."""

import pytest
from sqlalchemy import text

from testes.apoio_indicacoes import esconder_opiniao_no_banco, ids_da_lista, indicar
from testes.conftest import ADMIN, COMISSAO, COMUM

pytestmark = pytest.mark.usefixtures("predio")


def _erro(resposta) -> tuple[int, str]:
    return resposta.status_code, resposta.json()["codigo"]


def _historico(engine, acao: str) -> list[dict]:
    with engine.connect() as con:
        return [
            dict(linha._mapping)
            for linha in con.execute(
                text(
                    "select unidade_id, entidade, entidade_id, detalhes from historico"
                    " where acao = :a order by id"
                ),
                {"a": acao},
            )
        ]


def _avisos_abertos(engine, prestador: int) -> int:
    with engine.connect() as con:
        return con.execute(
            text(
                "select count(*) from aviso_servico where prestador_id = :p"
                " and resolvido_em is null"
            ),
            {"p": prestador},
        ).scalar_one()


def _id_do_aviso(engine, prestador: int) -> int:
    with engine.connect() as con:
        return con.execute(
            text("select min(id) from aviso_servico where prestador_id = :p"), {"p": prestador}
        ).scalar_one()


def _id_da_opiniao(engine, prestador: int, unidade: int) -> int:
    with engine.connect() as con:
        return con.execute(
            text("select id from opiniao_servico where prestador_id = :p and unidade_id = :u"),
            {"p": prestador, "u": unidade},
        ).scalar_one()


def test_so_gestao_esconde_e_resolve(logar, engine_app, predio):
    p = indicar(logar(ADMIN))
    logar(COMUM).post(f"/api/indicacoes/{p}/aviso")
    aviso = _id_do_aviso(engine_app, p)
    opiniao = _id_da_opiniao(engine_app, p, predio[ADMIN])
    comum = logar(COMUM)
    for caminho in (
        f"/api/indicacoes/{p}/esconder",
        f"/api/indicacoes/opinioes/{opiniao}/esconder",
        f"/api/indicacoes/avisos/{aviso}/resolver",
    ):
        assert _erro(comum.post(caminho)) == (403, "sem_permissao")
    assert logar(COMISSAO).post(f"/api/indicacoes/avisos/{aviso}/resolver").status_code == 204
    assert logar(ADMIN).post(f"/api/indicacoes/opinioes/{opiniao}/esconder").status_code == 204
    assert logar(COMISSAO).post(f"/api/indicacoes/{p}/esconder").status_code == 204


def test_ids_inexistentes_404(logar):
    admin = logar(ADMIN)
    assert _erro(admin.post("/api/indicacoes/9999/esconder"))[0] == 404
    assert _erro(admin.post("/api/indicacoes/opinioes/9999/esconder"))[0] == 404
    assert _erro(admin.post("/api/indicacoes/avisos/9999/resolver"))[0] == 404
    assert admin.post("/api/indicacoes/opinioes/0/esconder").status_code == 422


def test_so_admin_mexe_em_categoria(logar):
    r = logar(COMISSAO).post("/api/indicacoes/categorias", json={"nome": "Jardinagem"})
    assert _erro(r) == (403, "sem_permissao")
    assert _erro(logar(COMISSAO).put("/api/indicacoes/categorias/1", json={"nome": "X Y"})) == (
        403,
        "sem_permissao",
    )
    r = logar(ADMIN).post("/api/indicacoes/categorias", json={"nome": "Jardinagem"})
    assert r.status_code == 201 and r.json()["nome"] == "Jardinagem"


def test_esconder_tira_da_lista_resolve_avisos_e_registra(logar, engine_app, predio):
    p = indicar(logar(COMUM))
    logar(ADMIN).post(f"/api/indicacoes/{p}/aviso", json={"motivo": "Pediu para sair"})
    assert logar(COMISSAO).post(f"/api/indicacoes/{p}/esconder").status_code == 204
    assert ids_da_lista(logar(COMISSAO)) == []
    assert _avisos_abertos(engine_app, p) == 0
    assert _historico(engine_app, "indicacao_escondida") == [
        {
            "unidade_id": predio[COMISSAO],
            "entidade": "prestador",
            "entidade_id": p,
            "detalhes": {},
        }
    ]
    assert logar(COMISSAO).get(f"/api/indicacoes/{p}").json()["escondido"] is True
    # Esconder de novo não faz nada (nem registra outra vez).
    assert logar(ADMIN).post(f"/api/indicacoes/{p}/esconder").status_code == 204
    assert len(_historico(engine_app, "indicacao_escondida")) == 1


def test_esconder_a_unica_opiniao_tira_da_lista_e_a_pagina_abre(logar, engine_app, predio):
    p = indicar(logar(COMUM))
    opiniao = _id_da_opiniao(engine_app, p, predio[COMUM])
    assert logar(ADMIN).post(f"/api/indicacoes/opinioes/{opiniao}/esconder").status_code == 204
    assert ids_da_lista(logar(ADMIN)) == []
    assert logar(ADMIN).get(f"/api/indicacoes/{p}").status_code == 200
    assert _historico(engine_app, "indicacao_opiniao_escondida") == [
        {
            "unidade_id": predio[ADMIN],
            "entidade": "prestador",
            "entidade_id": p,
            "detalhes": {"opiniao": opiniao},
        }
    ]
    # De novo: nada muda.
    assert logar(ADMIN).post(f"/api/indicacoes/opinioes/{opiniao}/esconder").status_code == 204
    assert len(_historico(engine_app, "indicacao_opiniao_escondida")) == 1


def test_aviso_sem_opiniao_visivel_conta_para_a_gestao(logar, engine_app, predio):
    p = indicar(logar(COMUM))
    logar(ADMIN).post(f"/api/indicacoes/{p}/aviso")
    esconder_opiniao_no_banco(engine_app, p, predio[COMUM], predio[COMISSAO])
    gestao = logar(ADMIN)
    assert gestao.get("/api/indicacoes").json()["com_aviso"] == 1
    assert ids_da_lista(gestao) == []
    com_aviso = gestao.get("/api/indicacoes", params={"com_aviso": "true"}).json()
    assert [i["id"] for i in com_aviso["itens"]] == [p]
    assert com_aviso["itens"][0]["avisos_abertos"] == 1
    assert gestao.get(f"/api/indicacoes/{p}").status_code == 200


def test_resolver_tira_do_filtro(logar, engine_app, predio):
    p = indicar(logar(COMUM))
    logar(ADMIN).post(f"/api/indicacoes/{p}/aviso")
    aviso = _id_do_aviso(engine_app, p)
    assert logar(COMISSAO).post(f"/api/indicacoes/avisos/{aviso}/resolver").status_code == 204
    gestao = logar(COMISSAO).get("/api/indicacoes", params={"com_aviso": "true"}).json()
    assert gestao["itens"] == [] and gestao["com_aviso"] == 0
    assert _historico(engine_app, "indicacao_aviso_resolvido") == [
        {
            "unidade_id": predio[COMISSAO],
            "entidade": "prestador",
            "entidade_id": p,
            "detalhes": {},
        }
    ]
    # Resolvido, quem avisou pode avisar de novo.
    assert logar(ADMIN).get(f"/api/indicacoes/{p}").json()["ja_avisei"] is False
    assert logar(COMISSAO).post(f"/api/indicacoes/avisos/{aviso}/resolver").status_code == 204


def test_categoria_nova_entra_antes_de_outros(logar, engine_app, predio):
    admin = logar(ADMIN)
    assert admin.post("/api/indicacoes/categorias", json={"nome": "Jardinagem"}).status_code == 201
    assert admin.post("/api/indicacoes/categorias", json={"nome": "Piscina"}).status_code == 201
    cats = admin.get("/api/indicacoes/categorias").json()["itens"]
    assert [c["nome"] for c in cats][-3:] == ["Jardinagem", "Piscina", "Outros"]
    assert _historico(engine_app, "categoria_criada")[0] == {
        "unidade_id": predio[ADMIN],
        "entidade": "categoria_servico",
        "entidade_id": cats[-3]["id"],
        "detalhes": {"categoria": "Jardinagem"},
    }


def test_renomear_e_repetida_da_409(logar, engine_app):
    admin = logar(ADMIN)
    r = admin.put("/api/indicacoes/categorias/1", json={"nome": "Marcenaria"})
    assert r.status_code == 200 and r.json() == {"id": 1, "nome": "Marcenaria"}
    assert _historico(engine_app, "categoria_renomeada")[0]["detalhes"] == {
        "categoria": "Marcenaria"
    }
    r = admin.put("/api/indicacoes/categorias/1", json={"nome": "eletricista"})
    assert _erro(r) == (409, "categoria_ja_existe")
    r = admin.post("/api/indicacoes/categorias", json={"nome": "PINTURA"})
    assert _erro(r) == (409, "categoria_ja_existe")
    # Mudar só a maiúscula da própria categoria passa.
    assert admin.put("/api/indicacoes/categorias/1", json={"nome": "MARCENARIA"}).status_code == 200
    assert admin.put("/api/indicacoes/categorias/9999", json={"nome": "Nada"}).status_code == 404


def test_historico_sem_nome_do_prestador(logar, engine_app, predio):
    p = indicar(logar(COMUM), nome="Marcenaria Exemplo")
    logar(ADMIN).post(f"/api/indicacoes/{p}/aviso")
    aviso = _id_do_aviso(engine_app, p)
    opiniao = _id_da_opiniao(engine_app, p, predio[COMUM])
    admin = logar(ADMIN)
    admin.post(f"/api/indicacoes/avisos/{aviso}/resolver")
    admin.post(f"/api/indicacoes/opinioes/{opiniao}/esconder")
    admin.post(f"/api/indicacoes/{p}/esconder")
    with engine_app.connect() as con:
        detalhes = con.execute(text("select detalhes::text from historico")).scalars().all()
    assert detalhes and not any("Marcenaria" in d or "81999990001" in d for d in detalhes)
