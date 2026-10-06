"""Contrato das rotas do M2 (spec do M2, seção 4), antes dos épicos.

As rotas já existem com os esquemas, as permissões e o CSRF de verdade, e respondem 501
`em_construcao` até o épico implementar: o épico A (push) e o épico B (recuperação) trocam só o
corpo. Os testes de 501 são os únicos que os épicos apagam.
"""

import pytest
from sqlalchemy import text

from testes.conftest import CABECALHO_PORTAL, COMUM, NAO_ATIVADA

pytestmark = pytest.mark.usefixtures("predio")

P256DH = "B" + "A" * 86
AUTH = "C" * 22
INSCRICAO = {
    "endpoint": "https://fcm.googleapis.com/fcm/send/abc:123",
    "p256dh": P256DH,
    "auth": AUTH,
}
TOKEN = "t" * 43
SENHAS = {"senha_nova": "senha-nova-boa", "senha_nova_repetida": "senha-nova-boa"}

# (método, caminho, corpo válido)
ROTAS_PUSH = [
    ("GET", "/api/notificacoes", None),
    ("PUT", "/api/notificacoes/este-aparelho", INSCRICAO),
    ("DELETE", "/api/notificacoes/este-aparelho", None),
]
ROTAS_RECUPERACAO = [
    ("POST", "/api/acesso/recuperacao", {"login": "1203"}),
    ("POST", "/api/acesso/recuperacao/conferir", {"token": TOKEN}),
    ("POST", "/api/acesso/recuperacao/redefinir", {"token": TOKEN, **SENHAS}),
]


def _codigo(resposta) -> tuple[int, str]:
    return resposta.status_code, resposta.json().get("codigo")


def test_rotas_do_m2_declaradas():
    from app.main import app

    caminhos = app.openapi()["paths"]
    no_app = {
        (metodo.upper(), caminho)
        for caminho, operacoes in caminhos.items()
        if caminho.startswith(("/api/notificacoes", "/api/acesso/recuperacao"))
        for metodo in operacoes
    }
    assert no_app == {(m, c) for m, c, _ in ROTAS_PUSH + ROTAS_RECUPERACAO}


# --- épico A · push ----------------------------------------------------------------------------


@pytest.mark.parametrize(("metodo", "caminho", "corpo"), ROTAS_PUSH)
def test_push_exige_sessao_completa(cliente, logar, metodo, caminho, corpo):
    cliente.headers.update(CABECALHO_PORTAL)
    assert _codigo(cliente.request(metodo, caminho, json=corpo)) == (401, "sem_sessao")
    restrita = logar(NAO_ATIVADA).request(metodo, caminho, json=corpo)
    assert _codigo(restrita) == (403, "primeiro_acesso_pendente")


@pytest.mark.parametrize(("metodo", "caminho", "corpo"), ROTAS_PUSH)
def test_push_em_construcao(logar, metodo, caminho, corpo):
    assert _codigo(logar(COMUM).request(metodo, caminho, json=corpo)) == (501, "em_construcao")


@pytest.mark.parametrize(("metodo", "caminho", "corpo"), ROTAS_PUSH[1:])
def test_push_exige_cabecalho_portal(logar, metodo, caminho, corpo):
    cliente = logar(COMUM)
    del cliente.headers["X-Portal"]
    assert _codigo(cliente.request(metodo, caminho, json=corpo)) == (403, "requisicao_recusada")


@pytest.mark.parametrize(
    ("mudar", "campo"),
    [
        ({"endpoint": "http://fcm.googleapis.com/fcm/send/abc"}, "endpoint"),
        ({"endpoint": "https://intranet.local/fcm/send/abc"}, "endpoint"),
        ({"endpoint": "https://fcm.googleapis.com.exemplo.com/x"}, "endpoint"),
        ({"endpoint": "https://evil.com/?fcm.googleapis.com"}, "endpoint"),
        ({"endpoint": "https://user@fcm.googleapis.com/x"}, "endpoint"),
        ({"endpoint": "https://fcm.googleapis.com:8443/x"}, "endpoint"),
        ({"endpoint": "https://fcm.googleapis.com/" + "a" * 2048}, "endpoint"),
        ({"p256dh": "curta"}, "p256dh"),
        ({"auth": "C/" * 11}, "auth"),
    ],
)
def test_inscricao_so_aceita_servicos_de_push_conhecidos(logar, mudar, campo):
    resposta = logar(COMUM).put("/api/notificacoes/este-aparelho", json=INSCRICAO | mudar)
    assert _codigo(resposta) == (422, "dados_invalidos")
    assert resposta.json()["campos"][0]["campo"] == campo


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://fcm.googleapis.com/fcm/send/abc:123",
        "https://updates.push.services.mozilla.com/wpush/v2/gAAAA",
        "https://web.push.apple.com/QGv0d9",
        "https://wns2-bn3p.notify.windows.com/w/?token=BQYAAAB",
    ],
)
def test_inscricao_aceita_chrome_firefox_safari_e_edge(logar, endpoint):
    resposta = logar(COMUM).put(
        "/api/notificacoes/este-aparelho", json=INSCRICAO | {"endpoint": endpoint}
    )
    assert _codigo(resposta) == (501, "em_construcao")


def test_aparelho_diz_se_recebe_notificacao(logar, engine_app, predio):
    cliente = logar(COMUM)
    with engine_app.begin() as con:
        sessao = con.execute(
            text("select max(id) from sessao where unidade_id = :u"), {"u": predio[COMUM]}
        ).scalar_one()
        con.execute(
            text(
                "insert into inscricao_push (sessao_id, endpoint, chave_p256dh, chave_auth)"
                " values (:s, 'https://fcm.googleapis.com/fcm/send/x', :p, :a)"
            ),
            {"s": sessao, "p": P256DH, "a": AUTH},
        )
    outro = logar(COMUM)
    aparelhos = outro.get("/api/minha-unidade").json()["aparelhos"]
    assert {a["id"]: a["notificacoes"] for a in aparelhos} == {
        sessao: True,
        max(a["id"] for a in aparelhos): False,
    }
    assert cliente.get("/api/minha-unidade").status_code == 200


# --- épico B · recuperação ---------------------------------------------------------------------


@pytest.mark.parametrize(("metodo", "caminho", "corpo"), ROTAS_RECUPERACAO)
def test_recuperacao_sem_sessao_chega_na_rota(cliente, metodo, caminho, corpo):
    # Quem esqueceu a senha não tem sessão: a rota não pede.
    resposta = cliente.request(metodo, caminho, json=corpo, headers=CABECALHO_PORTAL)
    assert _codigo(resposta) == (501, "em_construcao")


@pytest.mark.parametrize(("metodo", "caminho", "corpo"), ROTAS_RECUPERACAO)
def test_recuperacao_exige_cabecalho_portal(cliente, metodo, caminho, corpo):
    # CSRF: sem o cabeçalho, outro site poderia mandar e-mails em nome do morador.
    assert _codigo(cliente.request(metodo, caminho, json=corpo)) == (403, "requisicao_recusada")


@pytest.mark.parametrize(
    ("caminho", "corpo", "campo", "mensagem"),
    [
        (
            "/api/acesso/recuperacao",
            {"login": "9999"},
            "login",
            "Escolha o bloco e escreva o número do apartamento.",
        ),
        ("/api/acesso/recuperacao/conferir", {"token": ""}, "token", None),
        ("/api/acesso/recuperacao/conferir", {"token": "x" * 101}, "token", None),
        (
            "/api/acesso/recuperacao/redefinir",
            {"token": TOKEN, "senha_nova": "curta", "senha_nova_repetida": "curta"},
            "senha_nova",
            "A senha nova precisa ter pelo menos 8 caracteres.",
        ),
        (
            "/api/acesso/recuperacao/redefinir",
            {"token": TOKEN, "senha_nova": "mudar123", "senha_nova_repetida": "mudar123"},
            "senha_nova",
            "Escolha uma senha diferente da inicial, que todo mundo conhece.",
        ),
        (
            "/api/acesso/recuperacao/redefinir",
            {"token": TOKEN, "senha_nova": "senha-nova-boa", "senha_nova_repetida": "outra"},
            "senha_nova_repetida",
            "As duas senhas estão diferentes. Escreva a mesma nas duas.",
        ),
    ],
)
def test_recuperacao_valida_o_corpo(cliente, caminho, corpo, campo, mensagem):
    resposta = cliente.post(caminho, json=corpo, headers=CABECALHO_PORTAL)
    assert _codigo(resposta) == (422, "dados_invalidos")
    erro = resposta.json()["campos"][0]
    assert erro["campo"] == campo
    if mensagem:
        assert erro["mensagem"] == mensagem
    # A senha digitada nunca volta na resposta.
    assert "senha-nova-boa" not in resposta.text


def test_acoes_do_m2_no_historico(engine_app, predio):
    from sqlalchemy.orm import Session

    from app.servicos.historico import Acao, registrar

    # Os detalhes que o épico B vai gravar passam pelo filtro de dado pessoal.
    with Session(engine_app) as db:
        registrar(
            db,
            Acao.recuperacao_pedida,
            unidade_id=None,
            entidade="unidade",
            entidade_id=predio[COMUM],
            detalhes={"enviado": False, "motivo": "sem_email"},
        )
        registrar(
            db,
            Acao.senha_redefinida,
            unidade_id=predio[COMUM],
            entidade="unidade",
            entidade_id=predio[COMUM],
        )
        db.commit()
