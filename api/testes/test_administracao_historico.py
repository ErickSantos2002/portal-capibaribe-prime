"""H-11 · Histórico de ações (RNF-14)."""

import json

import pytest
from sqlalchemy import text

from app.main import app
from testes.test_administracao_apoio import ADMIN, COMISSAO, COMUM, NAO_ATIVADA


@pytest.fixture
def admin(predio, logar, engine_dono):
    # Começa com o histórico vazio (o `dono` pode; o `app` não), para contar só o que o teste
    # registra.
    with engine_dono.begin() as con:
        con.execute(text("delete from historico"))
    return logar(ADMIN)


def _registrar(engine, acao: str, unidade_id, entidade=None, entidade_id=None, detalhes=None):
    with engine.begin() as con:
        return con.execute(
            text(
                "insert into historico (unidade_id, acao, entidade, entidade_id, detalhes)"
                " values (:u, :a, :e, :i, cast(:d as jsonb)) returning id"
            ),
            {
                "u": unidade_id,
                "a": acao,
                "e": entidade,
                "i": entidade_id,
                "d": json.dumps(detalhes or {}),
            },
        ).scalar_one()


def _publicar_aviso(engine, unidade_id: int, titulo: str) -> int:
    with engine.begin() as con:
        aviso = con.execute(
            text(
                "insert into aviso (publicado_por, publicado_como, para_todos)"
                " values (:u, 'comissao', true) returning id"
            ),
            {"u": unidade_id},
        ).scalar_one()
        con.execute(
            text(
                "insert into aviso_versao (aviso_id, versao, titulo, texto, criada_por)"
                " values (:a, 1, :t, 'Texto', :u)"
            ),
            {"a": aviso, "t": titulo, "u": unidade_id},
        )
    return aviso


def test_historico_traz_quem_quando_o_que_e_o_item(admin, predio):
    admin.put(f"/api/admin/unidades/{COMUM}/papeis/comissao")

    resposta = admin.get("/api/admin/historico")

    assert resposta.status_code == 200
    assert resposta.headers["cache-control"] == "no-store"
    item = resposta.json()["itens"][0]
    assert item["ocorrido_em"]
    assert item["unidade"] == {"login": ADMIN, "bloco": 1, "apartamento": "101"}
    assert item["acao"] == "papel_concedido"
    assert item["entidade"] == "unidade"
    assert item["entidade_id"] == predio[COMUM]
    assert item["unidade_afetada"] == {"login": COMUM, "bloco": 1, "apartamento": "203"}
    assert item["aviso_titulo"] is None
    assert item["detalhes"] == {"papel": "comissao"}


def test_historico_mostra_as_acoes_do_m1(admin, engine_app, predio):
    """Primeiro acesso, bloqueio, reset, papel, aviso publicado/corrigido/arquivado."""
    aviso = _publicar_aviso(engine_app, predio[COMISSAO], "Vistoria da obra no dia 15")
    _registrar(engine_app, "primeiro_acesso", predio[COMUM], "unidade", predio[COMUM])
    _registrar(engine_app, "unidade_bloqueada", None, "unidade", predio[NAO_ATIVADA])
    _registrar(engine_app, "aviso_publicado", predio[COMISSAO], "aviso", aviso)
    _registrar(engine_app, "aviso_corrigido", predio[COMISSAO], "aviso", aviso, {"versao": 2})
    _registrar(engine_app, "aviso_arquivado", predio[COMISSAO], "aviso", aviso)
    admin.post(f"/api/admin/unidades/{COMUM}/resetar", json={"confirmo": True})

    itens = admin.get("/api/admin/historico").json()["itens"]

    assert [i["acao"] for i in itens] == [
        "unidade_resetada",
        "aviso_arquivado",
        "aviso_corrigido",
        "aviso_publicado",
        "unidade_bloqueada",
        "primeiro_acesso",
    ]
    bloqueio = itens[4]
    # Ação do próprio Portal: sem unidade que fez ("Portal" na tela).
    assert bloqueio["unidade"] is None
    assert bloqueio["unidade_afetada"] == {"login": NAO_ATIVADA, "bloco": 4, "apartamento": "203"}
    publicado = itens[3]
    assert publicado["unidade"]["login"] == COMISSAO
    assert publicado["aviso_titulo"] == "Vistoria da obra no dia 15"
    assert publicado["unidade_afetada"] is None
    assert itens[2]["detalhes"] == {"versao": 2}


def test_historico_mostra_o_titulo_em_vigor_do_aviso(admin, engine_app, predio):
    aviso = _publicar_aviso(engine_app, predio[COMISSAO], "Título antigo")
    with engine_app.begin() as con:
        con.execute(
            text(
                "insert into aviso_versao (aviso_id, versao, titulo, texto, criada_por)"
                " values (:a, 2, 'Título corrigido', 'Texto', :u)"
            ),
            {"a": aviso, "u": predio[COMISSAO]},
        )
    _registrar(engine_app, "aviso_publicado", predio[COMISSAO], "aviso", aviso)

    item = admin.get("/api/admin/historico").json()["itens"][0]
    assert item["aviso_titulo"] == "Título corrigido"


def test_historico_pagina_do_mais_novo_para_o_mais_antigo(admin, engine_app, predio):
    ids = [_registrar(engine_app, "primeiro_acesso", predio[COMUM]) for _ in range(5)]

    primeira = admin.get("/api/admin/historico", params={"limite": 2}).json()
    assert [i["id"] for i in primeira["itens"]] == [ids[4], ids[3]]
    assert primeira["proximo"] == ids[3]

    segunda = admin.get(
        "/api/admin/historico", params={"limite": 2, "antes_de": primeira["proximo"]}
    ).json()
    assert [i["id"] for i in segunda["itens"]] == [ids[2], ids[1]]

    terceira = admin.get(
        "/api/admin/historico", params={"limite": 2, "antes_de": segunda["proximo"]}
    ).json()
    assert [i["id"] for i in terceira["itens"]] == [ids[0]]
    assert terceira["proximo"] is None


def test_historico_pagina_exata_nao_promete_proxima(admin, engine_app, predio):
    for _ in range(2):
        _registrar(engine_app, "primeiro_acesso", predio[COMUM])
    pagina = admin.get("/api/admin/historico", params={"limite": 2}).json()
    assert len(pagina["itens"]) == 2
    assert pagina["proximo"] is None


def test_historico_limite_padrao_e_50(admin, engine_app, predio):
    with engine_app.begin() as con:
        con.execute(
            text(
                "insert into historico (unidade_id, acao)"
                " select :u, 'primeiro_acesso' from generate_series(1, 60)"
            ),
            {"u": predio[COMUM]},
        )
    pagina = admin.get("/api/admin/historico").json()
    assert len(pagina["itens"]) == 50
    assert pagina["proximo"] is not None


@pytest.mark.parametrize(
    "consulta", [{"limite": 0}, {"limite": 101}, {"antes_de": 0}, {"limite": "muitos"}]
)
def test_historico_consulta_invalida_e_422(admin, consulta):
    resposta = admin.get("/api/admin/historico", params=consulta)
    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "dados_invalidos"


def test_historico_nao_leva_dado_pessoal(admin, engine_app):
    """Modelo de dados, seção 5: nome, celular e e-mail não aparecem no histórico."""
    admin.put(f"/api/admin/unidades/{COMUM}/papeis/comissao")
    admin.post(f"/api/admin/unidades/{COMUM}/resetar", json={"confirmo": True})

    corpo = admin.get("/api/admin/historico").text

    assert "Responsável" not in corpo
    assert "81900000" not in corpo
    assert "@" not in corpo


def test_historico_nao_tem_rota_de_apagar():
    """Ninguém apaga o histórico: não existe rota que altere `/api/admin/historico`, e o banco
    nega UPDATE e DELETE ao `app` (`test_permissoes.py::test_app_nao_altera_historico`)."""
    metodos = {
        metodo
        for caminho, operacoes in app.openapi()["paths"].items()
        if caminho.startswith("/api/admin/historico")
        for metodo in operacoes
    }
    assert metodos == {"get"}
