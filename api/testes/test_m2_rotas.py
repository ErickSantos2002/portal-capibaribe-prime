"""Contrato das rotas do M2 (spec do M2, seção 4): o que vale antes **e depois** dos épicos.

Sessão, permissão, CSRF, validação do corpo, a lista de serviços de push e o pedido de
recuperação (que já responde de verdade) ficam aqui e **não** são apagados pelos épicos. Os
testes de 501 `em_construcao`, que os épicos apagam, estão em `test_m2_em_construcao.py`.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.esquemas.push import InscricaoPush, servico_de_push_conhecido
from app.esquemas.recuperacao import MSG_PEDIDO
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


@pytest.mark.parametrize(("metodo", "caminho", "corpo"), ROTAS_PUSH[1:])
def test_push_exige_cabecalho_portal(logar, metodo, caminho, corpo):
    cliente = logar(COMUM)
    del cliente.headers["X-Portal"]
    assert _codigo(cliente.request(metodo, caminho, json=corpo)) == (403, "requisicao_recusada")


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://fcm.googleapis.com/fcm/send/abc",
        "https://intranet.local/fcm/send/abc",
        "https://fcm.googleapis.com.exemplo.com/x",
        "https://evil.com/?fcm.googleapis.com",
        "https://evil.com/#fcm.googleapis.com",
        "https://user@fcm.googleapis.com/x",
        "https://fcm.googleapis.com:8443/x",
        "https://fcm.googleapis.com:443/x",
        "https://xfcm.googleapis.com/x",
        "https://[::1]/x",
        "nao é url",
        # Revisão do épico A: o requests (urllib3) lê a barra invertida diferente do urlsplit
        # e conectava em 169.254.169.254.
        "https://169.254.169.254\\.fcm.googleapis.com/latest",
        "https://169.254.169.254%5C.fcm.googleapis.com/latest",
        "https://169.254.169.254%5c.fcm.googleapis.com/latest",
        "https://fcm.googleapis.com\\@169.254.169.254/x",
        "https://169.254.169.254@fcm.googleapis.com/x",
        "https://fcm.googleapis.com/fcm send/x",
        "https://fcm.googleapis.com /x",
        "https://169.254.169.254\\.FCM.GOOGLEAPIS.COM/latest",
        "HTTPS://fcm.googleapis.com/fcm/send/x",
        "https://fcm.googleapis.com./fcm/send/x",
        "https://fcm.googleapis.com/fcm/send/x\\y",
        "https://fcm.googleapis.com/fcm/send/\n",
        "https://fcm.googleapis.com/fcm/send/é",
    ],
)
def test_servico_de_push_desconhecido_recusado(endpoint):
    # SSRF: a função faz um POST para o endpoint a cada aviso (spec do M2, seção 4.2).
    assert servico_de_push_conhecido(endpoint) is False


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://fcm.googleapis.com/fcm/send/abc:123",
        "https://updates.push.services.mozilla.com/wpush/v2/gAAAA",
        "https://web.push.apple.com/QGv0d9",
        "https://wns2-bn3p.notify.windows.com/w/?token=BQYAAAB",
        "https://FCM.googleapis.com/fcm/send/x",
    ],
    ids=["chrome", "firefox", "safari", "edge", "maiusculas"],
)
def test_servicos_de_push_dos_navegadores_aceitos(endpoint):
    assert servico_de_push_conhecido(endpoint) is True
    assert InscricaoPush(endpoint=endpoint, p256dh=P256DH, auth=AUTH).endpoint == endpoint


@pytest.mark.parametrize(
    ("mudar", "campo"),
    [
        ({"endpoint": "https://intranet.local/fcm/send/abc"}, "endpoint"),
        ({"endpoint": "https://fcm.googleapis.com/" + "a" * 2048}, "endpoint"),
        ({"p256dh": "curta"}, "p256dh"),
        ({"auth": "C/" * 11}, "auth"),
    ],
)
def test_rota_de_inscricao_valida_o_corpo(logar, mudar, campo):
    resposta = logar(COMUM).put("/api/notificacoes/este-aparelho", json=INSCRICAO | mudar)
    assert _codigo(resposta) == (422, "dados_invalidos")
    assert resposta.json()["campos"][0]["campo"] == campo


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
def test_recuperacao_nao_pede_sessao(cliente, metodo, caminho, corpo):
    # Quem esqueceu a senha não tem sessão: a rota não pode recusar por isso, antes ou depois
    # do épico (hoje 202 ou 501; depois, 202, 200 ou 410).
    resposta = cliente.request(metodo, caminho, json=corpo, headers=CABECALHO_PORTAL)
    assert resposta.status_code not in (401, 403), resposta.text


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


@pytest.fixture
def pedidos(monkeypatch) -> list[str]:
    """Troca o trabalho de segundo plano do pedido por um que só anota o login."""
    from app.servicos import recuperacao

    anotados: list[str] = []
    monkeypatch.setattr(recuperacao, "processar_pedido", anotados.append)
    return anotados


@pytest.fixture
def sem_banco():
    """A requisição do pedido não pode tocar no banco (revisão do contrato, achado 3)."""
    from app.banco import obter_sessao
    from app.main import app

    def quebrado():
        raise AssertionError("o pedido de recuperação abriu o banco dentro da requisição")

    app.dependency_overrides[obter_sessao] = quebrado
    yield
    app.dependency_overrides.pop(obter_sessao)


def test_pedido_responde_igual_e_deixa_tudo_para_depois(cliente, engine_app, pedidos, sem_banco):
    # 1203 sem e-mail, 1101 com e-mail, 6101 não existe (o prédio tem 5 blocos): a resposta e o
    # caminho dentro da requisição são os mesmos; quem tem e-mail só se descobre depois dela.
    with engine_app.begin() as con:
        con.execute(text("update unidade set email = 'a@example.com' where login = '1101'"))
    respostas = [
        cliente.post("/api/acesso/recuperacao", json={"login": login}, headers=CABECALHO_PORTAL)
        for login in ("1203", "1101", "6101")
    ]
    # Épico B: a resposta ganhou `remetente` e `assunto` (iguais para todos os logins).
    assert len({(r.status_code, r.text) for r in respostas}) == 1
    assert respostas[0].status_code == 202
    assert respostas[0].json()["mensagem"] == MSG_PEDIDO
    assert pedidos == ["1203", "1101", "6101"]


def test_acoes_do_m2_no_historico(engine_app, predio):
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


def test_historico_sabe_se_ja_registrou_na_ultima_hora(engine_app, engine_superusuario, predio):
    # Achado 3: um script contra os 320 logins não pode encher o histórico (Neon Free).
    from datetime import timedelta

    from app.servicos.historico import Acao, registrado_recentemente, registrar

    def recente(entidade_id: int) -> bool:
        with Session(engine_app) as db:
            return registrado_recentemente(
                db,
                Acao.recuperacao_pedida,
                entidade="unidade",
                entidade_id=entidade_id,
                janela=timedelta(hours=1),
            )

    assert recente(predio[COMUM]) is False
    with Session(engine_app) as db:
        registrar(
            db,
            Acao.recuperacao_pedida,
            unidade_id=None,
            entidade="unidade",
            entidade_id=predio[COMUM],
            detalhes={"enviado": True, "motivo": None},
        )
        db.commit()
    assert recente(predio[COMUM]) is True
    assert recente(predio[NAO_ATIVADA]) is False
    with engine_superusuario.begin() as con:
        con.execute(text("set local session_replication_role = replica"))
        con.execute(text("update historico set ocorrido_em = now() - interval '61 minutes'"))
    assert recente(predio[COMUM]) is False
