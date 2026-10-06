"""H-07 · Painel de ativação, e a ficha de uma unidade (base de H-08 e H-09)."""

import pytest
from sqlalchemy import text

from testes.test_administracao_apoio import ADMIN, COMISSAO, COMUM, NAO_ATIVADA


@pytest.fixture
def admin(predio, logar):
    return logar(ADMIN)


def _por_login(painel: dict) -> dict[str, dict]:
    return {u["unidade"]["login"]: u for u in painel["unidades"]}


# --- painel (H-07) ---------------------------------------------------------------------------


def test_painel_lista_as_320_unidades_por_bloco_com_os_dados(admin):
    resposta = admin.get("/api/admin/unidades")

    assert resposta.status_code == 200
    painel = resposta.json()
    unidades = painel["unidades"]
    assert len(unidades) == 320
    # Por bloco: a lista vem em ordem de login (bloco, andar, posição).
    logins = [u["unidade"]["login"] for u in unidades]
    assert logins == sorted(logins)
    assert {u["unidade"]["bloco"] for u in unidades} == {1, 2, 3, 4, 5}

    por_login = _por_login(painel)
    comum = por_login[COMUM]
    assert comum["unidade"] == {"login": COMUM, "bloco": 1, "apartamento": "203"}
    assert comum["andar"] == 2
    assert comum["ativada"] is True
    assert comum["ativada_em"] is not None
    assert comum["responsavel_nome"] == f"Responsável {COMUM} (fictício)"
    assert comum["celular"] == "81900000002"
    assert comum["papeis"] == []

    nao = por_login[NAO_ATIVADA]
    assert nao["ativada"] is False
    assert nao["ativada_em"] is None
    assert nao["responsavel_nome"] is None
    assert nao["celular"] is None

    assert por_login[ADMIN]["papeis"] == ["admin"]
    assert por_login[COMISSAO]["papeis"] == ["comissao"]


def test_painel_nao_mostra_email_nem_aparelho(admin):
    """Modelo de dados, seção 5: o painel leva só o que H-07 pede."""
    unidade = admin.get("/api/admin/unidades").json()["unidades"][0]
    assert set(unidade) == {
        "unidade",
        "andar",
        "ativada",
        "ativada_em",
        "responsavel_nome",
        "celular",
        "papeis",
    }


def test_painel_resume_adesao_geral_e_por_bloco(admin):
    painel = admin.get("/api/admin/unidades").json()

    # 3 ativadas de 320 = 0,94% → arredonda para 1.
    assert painel["resumo"] == {"total": 320, "ativadas": 3, "percentual": 1}
    blocos = {b["numero"]: b for b in painel["blocos"]}
    assert list(blocos) == [1, 2, 3, 4, 5]
    # Bloco 1: 1101 e 1203 de 64 = 3,1% → 3. Bloco 2: 2304 = 1,6% → 2.
    assert blocos[1] == {
        "numero": 1,
        "nome": "Bloco 1",
        "total": 64,
        "ativadas": 2,
        "percentual": 3,
    }
    assert blocos[2] == {
        "numero": 2,
        "nome": "Bloco 2",
        "total": 64,
        "ativadas": 1,
        "percentual": 2,
    }
    assert blocos[3]["ativadas"] == 0 and blocos[3]["percentual"] == 0


@pytest.mark.parametrize(
    ("situacao", "esperados"),
    [
        ("ativadas", {ADMIN, COMISSAO, COMUM}),
        ("gestao", {ADMIN, COMISSAO}),
    ],
)
def test_painel_filtra(admin, situacao, esperados):
    painel = admin.get("/api/admin/unidades", params={"situacao": situacao}).json()

    assert set(_por_login(painel)) == esperados
    # O resumo é sempre do prédio inteiro.
    assert painel["resumo"]["total"] == 320
    assert len(painel["blocos"]) == 5


def test_painel_filtra_nao_ativadas(admin):
    painel = admin.get("/api/admin/unidades", params={"situacao": "nao_ativadas"}).json()
    logins = set(_por_login(painel))
    assert len(logins) == 317
    assert NAO_ATIVADA in logins
    assert not logins & {ADMIN, COMISSAO, COMUM}


def test_painel_todas_e_o_padrao(admin):
    todas = admin.get("/api/admin/unidades", params={"situacao": "todas"}).json()
    assert todas == admin.get("/api/admin/unidades").json()


def test_painel_filtro_desconhecido_e_422(admin):
    resposta = admin.get("/api/admin/unidades", params={"situacao": "qualquer"})
    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "dados_invalidos"


def test_painel_deixa_de_fora_unidade_desativada(admin, engine_dono):
    with engine_dono.begin() as con:
        con.execute(text("update unidade set ativa = false where login = '5708'"))

    painel = admin.get("/api/admin/unidades").json()

    assert "5708" not in _por_login(painel)
    assert painel["resumo"]["total"] == 319
    assert {b["numero"]: b["total"] for b in painel["blocos"]}[5] == 63


def test_painel_nao_fica_em_cache(admin):
    resposta = admin.get("/api/admin/unidades")
    assert resposta.headers["cache-control"] == "no-store"


# --- ficha da unidade ------------------------------------------------------------------------


def test_ficha_da_unidade(admin, logar):
    logar(COMUM)
    logar(COMUM)

    resposta = admin.get(f"/api/admin/unidades/{COMUM}")

    assert resposta.status_code == 200
    assert resposta.headers["cache-control"] == "no-store"
    ficha = resposta.json()
    assert ficha["unidade"] == {"login": COMUM, "bloco": 1, "apartamento": "203"}
    assert ficha["andar"] == 2
    assert ficha["ativada"] is True
    assert ficha["responsavel_nome"] == f"Responsável {COMUM} (fictício)"
    assert ficha["celular"] == "81900000002"
    assert ficha["email"] is None
    assert ficha["papeis"] == []
    assert ficha["bloqueada_ate"] is None
    assert ficha["aparelhos_conectados"] == 2


def test_ficha_conta_so_aparelhos_validos(admin, logar, engine_dono):
    logar(COMUM)
    logar(COMUM)
    with engine_dono.begin() as con:
        con.execute(
            text(
                "update sessao set encerrada_em = now() where id = (select min(s.id) from sessao s"
                " join unidade u on u.id = s.unidade_id where u.login = :l)"
            ),
            {"l": COMUM},
        )
    assert admin.get(f"/api/admin/unidades/{COMUM}").json()["aparelhos_conectados"] == 1


def test_ficha_mostra_bloqueio_e_papeis(admin, engine_dono):
    with engine_dono.begin() as con:
        # Bloqueio de um IP naquele login (revisão do M1, C2): a ficha mostra até quando.
        con.execute(
            text(
                "insert into entrada_tentativa (login, ip_hash, bloqueada_ate, expira_em)"
                " values (:l, repeat('a', 64), now() + interval '10 minutes',"
                " now() + interval '10 minutes')"
            ),
            {"l": NAO_ATIVADA},
        )
    nao = admin.get(f"/api/admin/unidades/{NAO_ATIVADA}").json()
    assert nao["ativada"] is False
    assert nao["bloqueada_ate"] is not None
    assert admin.get(f"/api/admin/unidades/{ADMIN}").json()["papeis"] == ["admin"]


@pytest.mark.parametrize("login", ["9999", "1801", "abc", "11011"])
def test_ficha_de_unidade_que_nao_existe_e_404(admin, login):
    resposta = admin.get(f"/api/admin/unidades/{login}")
    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "unidade_nao_encontrada"


def test_ficha_de_unidade_desativada_e_404(admin, engine_dono):
    with engine_dono.begin() as con:
        con.execute(text("update unidade set ativa = false where login = '5708'"))
    assert admin.get("/api/admin/unidades/5708").status_code == 404
