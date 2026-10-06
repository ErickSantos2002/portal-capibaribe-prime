"""Épico A · Minha unidade (H-06, RNF-12): ver, corrigir e apagar os próprios dados."""

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.modelos import Historico, Sessao, Unidade
from app.seguranca.senhas import SENHA_INICIAL, senha_confere
from app.seguranca.sessoes import NOME_COOKIE
from testes.conftest import ADMIN, CABECALHO_PORTAL, COMISSAO, COMUM, NAO_ATIVADA

CONTATO = {
    "responsavel_nome": "Rafael (fictício)",
    "celular": "81 98765-4321",
    "email": "rafael@exemplo.com",
}
# "Apagar meus dados" pede a senha atual (revisão do M1, C1).
APAGAR = {"confirmo": True, "senha": f"senha-{COMUM}"}


def unidade(engine_app, login: str = COMUM) -> Unidade:
    with Session(engine_app) as db:
        return db.scalars(select(Unidade).where(Unidade.login == login)).one()


def historico(engine_app, acao: str) -> list[Historico]:
    with Session(engine_app) as db:
        return list(db.scalars(select(Historico).where(Historico.acao == acao)))


# --- ver ----------------------------------------------------------------------------------------


def test_h06_mostra_bloco_apartamento_contatos_e_aparelhos(logar, predio):
    resposta = logar(COMUM).get("/api/minha-unidade")
    assert resposta.status_code == 200
    assert resposta.headers["cache-control"] == "no-store"
    corpo = resposta.json()
    assert corpo["unidade"] == {"login": COMUM, "bloco": 1, "apartamento": "203"}
    assert corpo["responsavel_nome"] == f"Responsável {COMUM} (fictício)"
    assert corpo["celular"] == "81900000002"
    assert corpo["email"] is None
    assert corpo["papeis"] == []
    assert corpo["ativada_em"] is not None
    [aparelho] = corpo["aparelhos"]
    assert aparelho["descricao"] == "Android · Chrome"
    assert aparelho["este_aparelho"] is True
    assert set(aparelho) == {"id", "descricao", "criada_em", "ultimo_uso_em", "este_aparelho"}


def test_h06_lista_so_aparelhos_em_vigor_da_propria_unidade(logar, predio, engine_dono):
    eu = logar(COMUM)
    logar(COMUM)  # outro aparelho em vigor
    logar(COMISSAO)  # de outra unidade: não aparece
    encerrado = logar(COMUM)
    encerrado.post("/api/acesso/sair")
    logar(COMUM)  # sem uso há mais de 180 dias (abaixo)
    with engine_dono.begin() as con:
        con.execute(
            text(
                "update sessao set ultimo_uso_em = now() - interval '181 days' "
                "where id = (select max(id) from sessao)"
            )
        )
    aparelhos = eu.get("/api/minha-unidade").json()["aparelhos"]
    assert len(aparelhos) == 2
    assert [a["este_aparelho"] for a in aparelhos].count(True) == 1


def test_h06_mostra_o_papel_de_gestao(logar, predio):
    assert logar(COMISSAO).get("/api/minha-unidade").json()["papeis"] == ["comissao"]


def test_h06_sem_sessao_e_401_e_sessao_restrita_e_403(cliente, logar, predio):
    assert cliente.get("/api/minha-unidade").status_code == 401
    resposta = logar(NAO_ATIVADA).get("/api/minha-unidade")
    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "primeiro_acesso_pendente"


# --- editar responsável, celular e e-mail -------------------------------------------------------


def test_h06_edita_responsavel_celular_e_email(logar, predio, engine_app):
    resposta = logar(COMUM).put("/api/minha-unidade/dados", json=CONTATO)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert (corpo["responsavel_nome"], corpo["celular"], corpo["email"]) == (
        "Rafael (fictício)",
        "81987654321",
        "rafael@exemplo.com",
    )
    assert unidade(engine_app).celular == "81987654321"


def test_h06_editar_pode_apagar_so_o_email(logar, predio, engine_app):
    c = logar(COMUM)
    c.put("/api/minha-unidade/dados", json=CONTATO)
    c.put("/api/minha-unidade/dados", json={**CONTATO, "email": ""})
    assert unidade(engine_app).email is None


def test_h06_editar_recusa_nome_vazio_e_nao_muda_nada(logar, predio, engine_app):
    resposta = logar(COMUM).put(
        "/api/minha-unidade/dados", json={**CONTATO, "responsavel_nome": " "}
    )
    assert resposta.status_code == 422
    assert resposta.json()["mensagem"] == "Escreva o nome de quem responde pela unidade."
    assert unidade(engine_app).responsavel_nome == f"Responsável {COMUM} (fictício)"


def test_h06_editar_sem_cabecalho_portal_e_403(cliente, logar, predio):
    """Com sessão válida, mas sem `X-Portal: 1` (o que um site de terceiros mandaria)."""
    cliente.cookies.set(NOME_COOKIE, logar(COMUM).cookies[NOME_COOKIE])
    resposta = cliente.put("/api/minha-unidade/dados", json=CONTATO)
    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "requisicao_recusada"


# --- trocar a senha ------------------------------------------------------------------------------


def test_h06_trocar_senha_pede_a_atual(logar, predio, engine_app):
    resposta = logar(COMUM).put(
        "/api/minha-unidade/senha",
        json={
            "senha_atual": "errada",
            "senha_nova": "nova-senha-123",
            "senha_nova_repetida": "nova-senha-123",
        },
    )
    assert resposta.status_code == 400
    assert resposta.json() == {
        "codigo": "senha_atual_incorreta",
        "mensagem": "A senha atual não confere.",
    }
    assert senha_confere(unidade(engine_app).senha_hash, f"senha-{COMUM}")


def test_h06_trocar_senha_grava_a_nova_e_desconecta_os_outros(logar, predio, engine_app):
    outro = logar(COMUM)
    eu = logar(COMUM)
    resposta = eu.put(
        "/api/minha-unidade/senha",
        json={
            "senha_atual": f"senha-{COMUM}",
            "senha_nova": "nova-senha-123",
            "senha_nova_repetida": "nova-senha-123",
        },
    )
    assert resposta.status_code == 204
    assert resposta.headers["set-cookie"].startswith(f"{NOME_COOKIE}=")
    assert senha_confere(unidade(engine_app).senha_hash, "nova-senha-123")
    assert eu.get("/api/minha-unidade").status_code == 200
    assert outro.get("/api/minha-unidade").status_code == 401
    [registro] = historico(engine_app, "senha_trocada")
    assert registro.unidade_id == predio[COMUM]


@pytest.mark.parametrize(
    ("nova", "repetida", "mensagem"),
    [
        ("curta", "curta", "A senha nova precisa ter pelo menos 8 caracteres."),
        (
            SENHA_INICIAL,
            SENHA_INICIAL,
            "Escolha uma senha diferente da inicial, que todo mundo conhece.",
        ),
        (
            "nova-senha-123",
            "outra-senha-123",
            "As duas senhas estão diferentes. Escreva a mesma nas duas.",
        ),
        # U7 (revisão do M1): trocar pela mesma senha não troca nada e derrubaria os aparelhos.
        (
            f"senha-{COMUM}",
            f"senha-{COMUM}",
            "A senha nova é igual à atual. Escolha uma diferente.",
        ),
    ],
)
def test_h06_senha_nova_segue_as_regras_do_primeiro_acesso(logar, predio, nova, repetida, mensagem):
    resposta = logar(COMUM).put(
        "/api/minha-unidade/senha",
        json={"senha_atual": f"senha-{COMUM}", "senha_nova": nova, "senha_nova_repetida": repetida},
    )
    assert resposta.status_code == 422
    assert resposta.json()["mensagem"] == mensagem


# --- desconectar um aparelho ---------------------------------------------------------------------


def ids_das_sessoes(engine_app, login: str) -> list[int]:
    with Session(engine_app) as db:
        return list(
            db.scalars(
                select(Sessao.id)
                .join(Unidade, Unidade.id == Sessao.unidade_id)
                .where(Unidade.login == login)
                .order_by(Sessao.id)
            )
        )


def test_h06_desconecta_outro_aparelho(logar, predio, engine_app):
    outro = logar(COMUM)
    eu = logar(COMUM)
    id_outro = ids_das_sessoes(engine_app, COMUM)[0]
    resposta = eu.delete(f"/api/minha-unidade/aparelhos/{id_outro}")
    assert resposta.status_code == 204
    assert "set-cookie" not in resposta.headers
    assert outro.get("/api/minha-unidade").status_code == 401
    assert eu.get("/api/minha-unidade").status_code == 200
    [registro] = historico(engine_app, "aparelho_desconectado")
    assert (registro.unidade_id, registro.entidade, registro.entidade_id) == (
        predio[COMUM],
        "sessao",
        id_outro,
    )


def test_h06_desconectar_o_proprio_aparelho_apaga_o_cookie(logar, predio, engine_app):
    eu = logar(COMUM)
    [proprio] = ids_das_sessoes(engine_app, COMUM)
    resposta = eu.delete(f"/api/minha-unidade/aparelhos/{proprio}")
    assert resposta.status_code == 204
    assert "Max-Age=0" in resposta.headers["set-cookie"]
    assert eu.get("/api/acesso/eu").status_code == 401


def test_h06_aparelho_de_outra_unidade_e_404_e_continua_conectado(logar, predio, engine_app):
    vizinho = logar(COMISSAO)
    [id_vizinho] = ids_das_sessoes(engine_app, COMISSAO)
    resposta = logar(COMUM).delete(f"/api/minha-unidade/aparelhos/{id_vizinho}")
    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "aparelho_nao_encontrado"
    assert vizinho.get("/api/minha-unidade").status_code == 200


def test_h06_aparelho_ja_desconectado_ou_inexistente_e_404(logar, predio, engine_app):
    saiu = logar(COMUM)
    saiu.post("/api/acesso/sair")
    [id_saiu] = ids_das_sessoes(engine_app, COMUM)
    eu = logar(COMUM)
    assert eu.delete(f"/api/minha-unidade/aparelhos/{id_saiu}").status_code == 404
    assert eu.delete("/api/minha-unidade/aparelhos/999999").status_code == 404


# --- apagar meus dados ---------------------------------------------------------------------------


def test_h06_apagar_dados_exige_confirmacao(logar, predio, engine_app):
    resposta = logar(COMUM).post(
        "/api/minha-unidade/apagar-dados", json={**APAGAR, "confirmo": False}
    )
    assert resposta.status_code == 422
    assert unidade(engine_app).responsavel_nome is not None


def test_h06_apagar_dados_volta_a_nao_ativada_com_mudar123(logar, predio, engine_app):
    resposta = logar(COMUM).post("/api/minha-unidade/apagar-dados", json=APAGAR)
    assert resposta.status_code == 204
    assert "Max-Age=0" in resposta.headers["set-cookie"]
    u = unidade(engine_app)
    assert (u.responsavel_nome, u.celular, u.email) == (None, None, None)
    assert u.ativada_em is None
    assert u.precisa_trocar_senha is True
    assert senha_confere(u.senha_hash, SENHA_INICIAL)
    [registro] = historico(engine_app, "dados_apagados")
    assert registro.unidade_id == predio[COMUM]


def test_h06_apagar_dados_desconecta_todos_os_aparelhos(logar, predio, engine_app):
    outro = logar(COMUM)
    eu = logar(COMUM)
    eu.post("/api/minha-unidade/apagar-dados", json=APAGAR)
    assert outro.get("/api/acesso/eu").status_code == 401
    assert eu.get("/api/acesso/eu").status_code == 401
    # A descrição do aparelho também é dado pessoal (modelo de dados, seção 5): some.
    assert ids_das_sessoes(engine_app, COMUM) == []


def test_h06_depois_de_apagar_entra_com_mudar123_no_primeiro_acesso(cliente, logar, predio):
    logar(COMUM).post("/api/minha-unidade/apagar-dados", json=APAGAR)
    resposta = cliente.post(
        "/api/acesso/entrar",
        json={"login": COMUM, "senha": SENHA_INICIAL},
        headers=CABECALHO_PORTAL,
    )
    assert resposta.json()["precisa_trocar_senha"] is True


def test_h06_apagar_dados_mantem_as_leituras_da_unidade(logar, predio, engine_dono, engine_app):
    """Os votos (M4) e as leituras são da unidade, não da pessoa: ficam."""
    with engine_dono.begin() as con:
        con.execute(
            text(
                """
                with a as (
                    insert into aviso (publicado_por, publicado_como, para_todos)
                    values (:admin, 'admin', true) returning id
                ), v as (
                    insert into aviso_versao (aviso_id, versao, titulo, texto, criada_por)
                    select id, 1, 'Teste', 'Texto', :admin from a
                )
                insert into aviso_leitura (aviso_id, unidade_id) select id, :comum from a
                """
            ),
            {"admin": predio[ADMIN], "comum": predio[COMUM]},
        )
    logar(COMUM).post("/api/minha-unidade/apagar-dados", json=APAGAR)
    with Session(engine_app) as db:
        leituras = db.scalar(
            text("select count(*) from aviso_leitura where unidade_id = :u"), {"u": predio[COMUM]}
        )
    assert leituras == 1


def test_h06_unidade_com_papel_de_gestao_nao_apaga(logar, predio, engine_app):
    resposta = logar(COMISSAO).post(
        "/api/minha-unidade/apagar-dados", json={**APAGAR, "senha": f"senha-{COMISSAO}"}
    )
    assert resposta.status_code == 409
    assert resposta.json() == {
        "codigo": "unidade_com_papel_de_gestao",
        "mensagem": (
            "Este apartamento tem papel de gestão. Peça à administração do Portal para retirar "
            "o papel antes."
        ),
    }
    assert unidade(engine_app, COMISSAO).ativada_em is not None


def test_h06_sessao_restrita_nao_apaga_nem_edita(logar, predio):
    restrita = logar(NAO_ATIVADA)
    assert restrita.post("/api/minha-unidade/apagar-dados", json=APAGAR).status_code == 403
    assert restrita.put("/api/minha-unidade/dados", json=CONTATO).status_code == 403


# --- C1: apagar exige a senha atual (sessão esquecida não toma a conta) --------------------------


def test_c1_apagar_sem_senha_e_recusado(logar, predio, engine_app):
    resposta = logar(COMUM).post("/api/minha-unidade/apagar-dados", json={"confirmo": True})
    assert resposta.status_code == 422
    assert resposta.json()["campos"][0]["campo"] == "senha"
    assert unidade(engine_app).ativada_em is not None


def test_c1_apagar_com_senha_errada_e_recusado_e_conta_tentativa(logar, predio, engine_app):
    eu = logar(COMUM)
    resposta = eu.post("/api/minha-unidade/apagar-dados", json={**APAGAR, "senha": "chute"})
    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "senha_atual_incorreta"
    assert unidade(engine_app).ativada_em is not None
    # A sessão continua (errar a senha não derruba quem já está dentro).
    assert eu.get("/api/acesso/eu").status_code == 200
    with Session(engine_app) as db:
        assert (
            db.scalar(text("select count(*) from entrada_tentativa where login = :l"), {"l": COMUM})
            == 1
        )


def test_c1_cinco_erros_ao_apagar_bloqueiam_aquele_ip(logar, cliente, predio, engine_app):
    eu = logar(COMUM)
    codigos = [
        eu.post("/api/minha-unidade/apagar-dados", json={**APAGAR, "senha": "chute"}).status_code
        for _ in range(5)
    ]
    assert codigos == [400, 400, 400, 400, 423]
    # Bloqueado: nem a senha certa apaga, e a entrada daquele IP também está bloqueada.
    assert eu.post("/api/minha-unidade/apagar-dados", json=APAGAR).status_code == 423
    entrar = cliente.post(
        "/api/acesso/entrar",
        json={"login": COMUM, "senha": f"senha-{COMUM}"},
        headers=CABECALHO_PORTAL,
    )
    assert entrar.status_code == 423
    assert unidade(engine_app).ativada_em is not None


def test_c1_a_partir_do_terceiro_erro_ao_apagar_diz_quantas_faltam(logar, predio):
    eu = logar(COMUM)
    mensagens = [
        eu.post("/api/minha-unidade/apagar-dados", json={**APAGAR, "senha": "x"}).json()["mensagem"]
        for _ in range(3)
    ]
    assert mensagens[0] == "A senha atual não confere."
    assert mensagens[2] == (
        "A senha atual não confere. Faltam 2 tentativas antes de a entrada ser bloqueada por 15 "
        "minutos."
    )
