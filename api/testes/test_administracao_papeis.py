"""H-09 · Dar e retirar o papel de Comissão (e de administrador). RF-09, RN-06."""

import threading

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from testes.apoio import restricao
from testes.test_administracao_apoio import (
    ADMIN,
    COMISSAO,
    COMUM,
    NAO_ATIVADA,
    contar,
    fotografia,
    linhas,
)


@pytest.fixture
def admin(predio, logar):
    return logar(ADMIN)


def _papel(login: str, papel: str) -> str:
    return f"/api/admin/unidades/{login}/papeis/{papel}"


def _papeis_em_vigor(engine, unidade_id: int) -> list[str]:
    return [
        r["papel"]
        for r in linhas(
            engine,
            "select papel::text from unidade_papel where unidade_id = :u and retirado_em is null",
            u=unidade_id,
        )
    ]


def test_dar_comissao_libera_a_gestao(admin, logar):
    """Na próxima vez que a unidade abrir o Portal, aparecem as opções de publicar."""
    morador = logar(COMUM)
    assert morador.get("/api/acesso/eu").json()["gestao"] is False

    resposta = admin.put(_papel(COMUM, "comissao"))

    assert resposta.status_code == 200
    assert resposta.json()["papeis"] == ["comissao"]
    eu = morador.get("/api/acesso/eu").json()
    assert eu["gestao"] is True
    assert eu["papeis"] == ["comissao"]


def test_retirar_comissao_vale_na_hora_mesmo_logada(admin, logar):
    comissao = logar(COMISSAO)
    assert comissao.get("/api/acesso/eu").json()["gestao"] is True

    resposta = admin.delete(_papel(COMISSAO, "comissao"))

    assert resposta.status_code == 200
    assert resposta.json()["papeis"] == []
    # Mesma sessão, sem sair e entrar: o papel é lido do banco a cada requisição.
    eu = comissao.get("/api/acesso/eu").json()
    assert eu["gestao"] is False
    assert eu["papeis"] == []


def test_retirar_grava_quem_retirou(admin, engine_app, predio):
    admin.delete(_papel(COMISSAO, "comissao"))
    papel = linhas(
        engine_app, "select * from unidade_papel where unidade_id = :u", u=predio[COMISSAO]
    )[0]
    assert papel["retirado_em"] is not None
    assert papel["retirado_por"] == predio[ADMIN]


def test_dar_grava_quem_deu(admin, engine_app, predio):
    admin.put(_papel(COMUM, "comissao"))
    papel = linhas(
        engine_app, "select * from unidade_papel where unidade_id = :u", u=predio[COMUM]
    )[0]
    assert papel["concedido_por"] == predio[ADMIN]


def test_dar_e_idempotente(admin, engine_app, predio):
    admin.put(_papel(COMUM, "comissao"))
    antes = fotografia(engine_app)

    resposta = admin.put(_papel(COMUM, "comissao"))

    assert resposta.status_code == 200
    assert resposta.json()["papeis"] == ["comissao"]
    assert fotografia(engine_app) == antes


def test_retirar_o_que_nao_tem_e_idempotente(admin, engine_app):
    antes = fotografia(engine_app)

    resposta = admin.delete(_papel(COMUM, "comissao"))

    assert resposta.status_code == 200
    assert resposta.json()["papeis"] == []
    assert fotografia(engine_app) == antes


def test_dar_de_novo_depois_de_retirar(admin, engine_app, predio):
    admin.delete(_papel(COMISSAO, "comissao"))
    resposta = admin.put(_papel(COMISSAO, "comissao"))

    assert resposta.json()["papeis"] == ["comissao"]
    assert (
        contar(
            engine_app,
            "select count(*) from unidade_papel where unidade_id = :u",
            u=predio[COMISSAO],
        )
        == 2
    )


def test_nao_da_papel_a_unidade_nao_ativada(admin, engine_app):
    antes = fotografia(engine_app)

    resposta = admin.put(_papel(NAO_ATIVADA, "comissao"))

    assert resposta.status_code == 409
    assert resposta.json() == {
        "codigo": "unidade_nao_ativada",
        "mensagem": "Só dá para dar papel a um apartamento que já entrou no Portal.",
    }
    assert fotografia(engine_app) == antes


def test_nao_retira_o_ultimo_admin(admin, engine_app):
    antes = fotografia(engine_app)

    resposta = admin.delete(_papel(ADMIN, "admin"))

    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "ultimo_admin"
    assert fotografia(engine_app) == antes
    assert admin.get("/api/acesso/eu").json()["admin"] is True


def test_dar_admin_a_outra_e_retirar_o_proprio(admin, logar, engine_app, predio):
    assert admin.put(_papel(COMISSAO, "admin")).json()["papeis"] == ["admin", "comissao"]

    resposta = admin.delete(_papel(ADMIN, "admin"))

    assert resposta.status_code == 200
    assert _papeis_em_vigor(engine_app, predio[ADMIN]) == []
    # Quem retirou o próprio papel perde o acesso ao painel na hora.
    assert admin.get("/api/admin/unidades").status_code == 403
    assert logar(COMISSAO).get("/api/admin/unidades").status_code == 200


@pytest.mark.parametrize("papel", ["sindico", "conselho", "dono", "ADMIN"])
def test_papel_fora_do_m1_e_422(admin, engine_app, papel):
    antes = fotografia(engine_app)
    assert admin.put(_papel(COMUM, papel)).status_code == 422
    assert admin.delete(_papel(COMUM, papel)).status_code == 422
    assert fotografia(engine_app) == antes


def test_papel_em_unidade_que_nao_existe_e_404(admin):
    assert admin.put(_papel("9999", "comissao")).json()["codigo"] == "unidade_nao_encontrada"
    assert admin.delete(_papel("9999", "comissao")).status_code == 404


def test_papeis_registram_no_historico(admin, engine_app, predio):
    admin.put(_papel(COMUM, "comissao"))
    admin.put(_papel(COMUM, "comissao"))  # repetido: não registra de novo
    admin.delete(_papel(COMUM, "comissao"))
    admin.delete(_papel(COMUM, "comissao"))  # repetido: não registra de novo

    registros = linhas(
        engine_app,
        "select acao, unidade_id, entidade, entidade_id, detalhes from historico"
        " where entidade_id = :u order by id",
        u=predio[COMUM],
    )
    alvo = {"unidade_id": predio[ADMIN], "entidade": "unidade", "entidade_id": predio[COMUM]}
    assert registros == [
        {"acao": "papel_concedido", **alvo, "detalhes": {"papel": "comissao"}},
        {"acao": "papel_retirado", **alvo, "detalhes": {"papel": "comissao"}},
    ]


def test_dar_ao_mesmo_tempo_nao_duplica(admin, logar, engine_app, predio):
    """Dois cliques (ou duas abas) ao mesmo tempo: um papel em vigor e um registro."""
    outro = logar(ADMIN)
    respostas = []

    def dar(cliente):
        respostas.append(cliente.put(_papel(COMUM, "comissao")).status_code)

    fios = [threading.Thread(target=dar, args=(c,)) for c in (admin, outro)]
    for fio in fios:
        fio.start()
    for fio in fios:
        fio.join()

    assert respostas == [200, 200]
    assert _papeis_em_vigor(engine_app, predio[COMUM]) == ["comissao"]
    assert contar(engine_app, "select count(*) from historico where acao = 'papel_concedido'") == 1


def test_unidade_resetada_depois_nao_recebe_papel(admin):
    admin.post(f"/api/admin/unidades/{COMUM}/resetar", json={"confirmo": True})
    assert admin.put(_papel(COMUM, "comissao")).status_code == 409


def test_banco_tambem_recusa_papel_em_unidade_nao_ativada(engine_app, predio):
    """A regra não depende só da rota (restrição `papel_em_unidade_ativada`)."""
    with pytest.raises(IntegrityError) as erro, engine_app.begin() as con:
        con.execute(
            text("insert into unidade_papel (unidade_id, papel) values (:u, 'comissao')"),
            {"u": predio[NAO_ATIVADA]},
        )
    assert restricao(erro.value) == "papel_em_unidade_ativada"
