"""H-08 · Resetar uma unidade (RF-07)."""

import pytest
from sqlalchemy import text

from app.seguranca.senhas import SENHA_INICIAL, senha_confere
from testes.test_administracao_apoio import (
    ADMIN,
    COMISSAO,
    COMUM,
    NAO_ATIVADA,
    contar,
    fotografia,
    linhas,
)

CONFIRMO = {"confirmo": True}


@pytest.fixture
def admin(predio, logar):
    return logar(ADMIN)


def _unidade(engine, login: str) -> dict:
    return linhas(engine, "select * from unidade where login = :l", l=login)[0]


def _resetar(cliente, login: str, corpo=CONFIRMO):
    return cliente.post(f"/api/admin/unidades/{login}/resetar", json=corpo)


@pytest.mark.parametrize("corpo", [None, {}, {"confirmo": False}, {"confirmo": "sim"}])
def test_resetar_sem_confirmar_recusa(admin, engine_app, corpo):
    """H-08: o reset só acontece com a confirmação explícita."""
    antes = fotografia(engine_app)

    resposta = _resetar(admin, COMUM, corpo)

    assert resposta.status_code == 422
    assert fotografia(engine_app) == antes


def test_resetar_volta_a_unidade_ao_estado_inicial(admin, engine_app, engine_dono):
    with engine_dono.begin() as con:
        con.execute(
            text("update unidade set email = 'fulano@example.com' where login = :l"),
            {"l": COMUM},
        )

    resposta = _resetar(admin, COMUM)

    assert resposta.status_code == 200
    ficha = resposta.json()
    assert ficha["unidade"]["login"] == COMUM
    assert ficha["ativada"] is False
    assert ficha["ativada_em"] is None
    assert ficha["responsavel_nome"] is None
    assert ficha["celular"] is None
    assert ficha["email"] is None
    assert ficha["papeis"] == []
    assert ficha["bloqueada_ate"] is None
    assert ficha["aparelhos_conectados"] == 0

    unidade = _unidade(engine_app, COMUM)
    assert senha_confere(unidade["senha_hash"], SENHA_INICIAL)
    assert not senha_confere(unidade["senha_hash"], f"senha-{COMUM}")
    assert unidade["precisa_trocar_senha"] is True
    assert unidade["ativada_em"] is None
    assert unidade["responsavel_nome"] is None
    assert unidade["celular"] is None
    assert unidade["email"] is None


def test_resetar_desconecta_todos_os_aparelhos(admin, logar, engine_app):
    celular, computador = logar(COMUM), logar(COMUM)
    assert celular.get("/api/acesso/eu").status_code == 200

    _resetar(admin, COMUM)

    assert celular.get("/api/acesso/eu").status_code == 401
    assert computador.get("/api/acesso/eu").status_code == 401
    abertas = contar(
        engine_app,
        "select count(*) from sessao s join unidade u on u.id = s.unidade_id"
        " where u.login = :l and s.encerrada_em is null",
        l=COMUM,
    )
    assert abertas == 0


def test_resetar_retira_os_papeis(admin, logar, engine_app, predio):
    comissao = logar(COMISSAO)
    assert comissao.get("/api/acesso/eu").json()["gestao"] is True

    resposta = _resetar(admin, COMISSAO)

    assert resposta.status_code == 200
    assert resposta.json()["papeis"] == []
    papel = linhas(
        engine_app,
        "select * from unidade_papel where unidade_id = :u",
        u=predio[COMISSAO],
    )[0]
    assert papel["retirado_em"] is not None
    assert papel["retirado_por"] == predio[ADMIN]


def test_resetar_tira_o_bloqueio_de_unidade_nao_ativada(admin, engine_app, engine_dono):
    """Unidade não ativada também pode ser resetada: tira os bloqueios de 15 minutos (de todos
    os IPs daquele login) e os contadores."""
    with engine_dono.begin() as con:
        for letra in ("a", "b"):
            con.execute(
                text(
                    "insert into entrada_tentativa (login, ip_hash, bloqueada_ate, expira_em)"
                    " values (:l, repeat(:x, 64), now() + interval '15 minutes',"
                    " now() + interval '15 minutes')"
                ),
                {"l": NAO_ATIVADA, "x": letra},
            )

    resposta = _resetar(admin, NAO_ATIVADA)

    assert resposta.status_code == 200
    assert resposta.json()["bloqueada_ate"] is None
    restantes = contar(
        engine_app, "select count(*) from entrada_tentativa where login = :l", l=NAO_ATIVADA
    )
    assert restantes == 0


def test_resetar_mantem_as_leituras(admin, engine_app, predio):
    """H-08: "votos já dados continuam valendo". No M1 ainda não há votos; o que a unidade
    deixou registrado são as leituras de aviso (contrato, seção 2.3)."""
    with engine_app.begin() as con:
        aviso = con.execute(
            text(
                "insert into aviso (publicado_por, publicado_como, para_todos)"
                " values (:a, 'comissao', true) returning id"
            ),
            {"a": predio[COMISSAO]},
        ).scalar_one()
        con.execute(
            text(
                "insert into aviso_versao (aviso_id, versao, titulo, texto, criada_por)"
                " values (:v, 1, 'Vistoria', 'Texto', :a)"
            ),
            {"v": aviso, "a": predio[COMISSAO]},
        )
        con.execute(
            text("insert into aviso_leitura (aviso_id, unidade_id) values (:v, :u)"),
            {"v": aviso, "u": predio[COMUM]},
        )

    _resetar(admin, COMUM)

    assert contar(engine_app, "select count(*) from aviso_leitura") == 1


def test_resetar_registra_no_historico(admin, engine_app, predio):
    _resetar(admin, COMISSAO)

    registros = linhas(
        engine_app, "select * from historico where entidade_id = :u order by id", u=predio[COMISSAO]
    )
    acoes = [(r["acao"], r["unidade_id"], r["entidade"], r["detalhes"]) for r in registros]
    assert acoes == [
        (
            "papel_retirado",
            predio[ADMIN],
            "unidade",
            {"papel": "comissao", "origem": "reset"},
        ),
        ("unidade_resetada", predio[ADMIN], "unidade", {"papeis_retirados": ["comissao"]}),
    ]


def test_resetar_o_ultimo_admin_recusa(admin, engine_app):
    antes = fotografia(engine_app)

    resposta = _resetar(admin, ADMIN)

    assert resposta.status_code == 409
    assert resposta.json() == {
        "codigo": "ultimo_admin",
        "mensagem": "Esta é a única unidade administradora. Dê o papel de administrador a outra"
        " unidade antes.",
    }
    assert fotografia(engine_app) == antes
    assert admin.get("/api/acesso/eu").status_code == 200


def test_admin_reseta_a_propria_unidade_se_houver_outro_admin(admin, engine_app):
    admin.put(f"/api/admin/unidades/{COMISSAO}/papeis/admin")

    resposta = _resetar(admin, ADMIN)

    assert resposta.status_code == 200
    # A sessão de quem resetou também cai (a senha voltou a mudar123).
    assert admin.get("/api/acesso/eu").status_code == 401


def test_resetar_unidade_que_nao_existe_e_404(admin):
    resposta = _resetar(admin, "9999")
    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "unidade_nao_encontrada"


def test_resetar_duas_vezes_funciona(admin, engine_app):
    assert _resetar(admin, COMUM).status_code == 200
    assert _resetar(admin, COMUM).status_code == 200
    assert contar(engine_app, "select count(*) from historico where acao = 'unidade_resetada'") == 2
