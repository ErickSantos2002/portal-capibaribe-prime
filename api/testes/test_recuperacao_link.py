"""Conferir e usar o link do e-mail (H-04; contrato do M2, seção 4.3; spec do épico B, 2.5).

Testes de segurança: token desconhecido, vencido, usado, de senha já trocada e de unidade
resetada respondem o mesmo 410; usar um link derruba os outros aparelhos e os outros links.
"""

import hashlib

import pytest
from sqlalchemy import text

from app.seguranca.sessoes import NOME_COOKIE
from testes.conftest import CABECALHO_PORTAL, COMISSAO, COMUM
from testes.test_avisos_apoio import historico

pytestmark = pytest.mark.usefixtures("predio")

CONFERIR = "/api/acesso/recuperacao/conferir"
REDEFINIR = "/api/acesso/recuperacao/redefinir"
SENHA = "uma-senha-nova-boa"
MSG_INVALIDO = (
    'Este link venceu ou já foi usado. Peça outro em "Esqueci minha senha". '
    "Se você já criou a senha nova, é só entrar com ela."
)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@pytest.fixture
def criar_token(engine_app):
    """`criar_token("1203")`: a unidade ganha e-mail e um link válido; devolve o token."""
    contador = iter(range(1000))

    def criar(login: str = COMUM) -> str:
        token = f"token-de-teste-{login}-{next(contador)}-" + "x" * 20
        with engine_app.begin() as con:
            con.execute(
                text("update unidade set email = 'm@example.com' where login = :l"), {"l": login}
            )
            con.execute(
                text(
                    "insert into token_recuperacao (unidade_id, token_hash)"
                    " select id, :h from unidade where login = :l"
                ),
                {"h": _hash(token), "l": login},
            )
        return token

    return criar


def _post(cliente, caminho: str, corpo: dict):
    return cliente.post(caminho, json=corpo, headers=CABECALHO_PORTAL)


def _redefinir(cliente, token: str, senha: str = SENHA):
    return _post(
        cliente, REDEFINIR, {"token": token, "senha_nova": senha, "senha_nova_repetida": senha}
    )


def _invalido(resposta) -> None:
    assert resposta.status_code == 410, resposta.text
    assert resposta.json() == {"codigo": "link_invalido", "mensagem": MSG_INVALIDO}


def _usado(engine, token: str) -> bool:
    with engine.connect() as con:
        return con.execute(
            text("select usado_em is not null from token_recuperacao where token_hash = :h"),
            {"h": _hash(token)},
        ).scalar_one()


def _vencer(engine_superusuario, token: str) -> None:
    with engine_superusuario.begin() as con:
        con.execute(text("set local session_replication_role = replica"))
        con.execute(
            text(
                "update token_recuperacao set criado_em = now() - interval '61 minutes',"
                " expira_em = now() - interval '1 minute' where token_hash = :h"
            ),
            {"h": _hash(token)},
        )


def _trocar_senha(engine, login: str) -> None:
    with engine.begin() as con:
        con.execute(
            text("update unidade set senha_hash = 'outro-hash' where login = :l"), {"l": login}
        )


# --- conferir ----------------------------------------------------------------------------------


def test_link_valido_mostra_a_placa_e_nao_gasta(cliente, engine_app, criar_token):
    token = criar_token()
    resposta = _post(cliente, CONFERIR, {"token": token})
    assert resposta.status_code == 200
    assert resposta.json() == {"unidade": {"login": COMUM, "bloco": 1, "apartamento": "203"}}
    assert _usado(engine_app, token) is False
    assert _post(cliente, CONFERIR, {"token": token}).status_code == 200


def test_link_inexistente(cliente, criar_token):
    criar_token()
    _invalido(_post(cliente, CONFERIR, {"token": "nao-existe-" + "y" * 32}))


def test_link_vencido(cliente, criar_token, engine_superusuario):
    token = criar_token()
    _vencer(engine_superusuario, token)
    _invalido(_post(cliente, CONFERIR, {"token": token}))
    _invalido(_redefinir(cliente, token))


def test_link_de_senha_ja_trocada(cliente, engine_app, criar_token):
    token = criar_token()
    _trocar_senha(engine_app, COMUM)
    _invalido(_post(cliente, CONFERIR, {"token": token}))
    _invalido(_redefinir(cliente, token))


def test_link_de_unidade_resetada_ou_desativada(cliente, engine_app, engine_dono, criar_token):
    token = criar_token()
    with engine_dono.begin() as con:
        con.execute(text("update unidade set ativa = false where login = :l"), {"l": COMUM})
    _invalido(_post(cliente, CONFERIR, {"token": token}))
    _invalido(_redefinir(cliente, token))


# --- redefinir ---------------------------------------------------------------------------------


def test_redefinir_entra_e_derruba_os_outros_aparelhos(
    cliente, logar, engine_app, criar_token, predio
):
    outro_aparelho = logar(COMUM)
    assert outro_aparelho.get("/api/acesso/eu").status_code == 200
    token = criar_token()
    resposta = _redefinir(cliente, token)
    assert resposta.status_code == 200, resposta.text
    assert resposta.json() == {
        "unidade": {"login": COMUM, "bloco": 1, "apartamento": "203"},
        "papeis": [],
        "gestao": False,
        "admin": False,
        "precisa_trocar_senha": False,
    }
    # Este aparelho já está entrado, com a sessão nova.
    assert NOME_COOKIE in resposta.cookies
    assert cliente.get("/api/acesso/eu").json()["unidade"]["login"] == COMUM
    # O outro aparelho caiu.
    assert outro_aparelho.get("/api/acesso/eu").status_code == 401
    assert _usado(engine_app, token) is True
    assert historico(engine_app, "senha_redefinida") == [
        {
            "unidade_id": predio[COMUM],
            "entidade": "unidade",
            "entidade_id": predio[COMUM],
            "detalhes": {},
        }
    ]


def test_senha_nova_vale_para_entrar(cliente, criar_token):
    _redefinir(cliente, criar_token())
    cliente.cookies.clear()
    entrar = _post(cliente, "/api/acesso/entrar", {"login": COMUM, "senha": SENHA})
    assert entrar.status_code == 200
    velha = _post(cliente, "/api/acesso/entrar", {"login": COMUM, "senha": f"senha-{COMUM}"})
    assert velha.status_code == 401


def test_link_so_vale_uma_vez(cliente, criar_token):
    token = criar_token()
    assert _redefinir(cliente, token).status_code == 200
    _invalido(_redefinir(cliente, token, "outra-senha-boa"))
    _invalido(_post(cliente, CONFERIR, {"token": token}))


def test_usar_um_link_mata_os_outros_links_da_unidade(cliente, criar_token):
    primeiro, segundo = criar_token(), criar_token()
    assert _redefinir(cliente, segundo).status_code == 200
    _invalido(_post(cliente, CONFERIR, {"token": primeiro}))
    _invalido(_redefinir(cliente, primeiro, "outra-senha-boa"))


def test_link_de_outra_unidade_nao_mexe_nesta(cliente, criar_token, logar):
    token_comum = criar_token(COMUM)
    criar_token(COMISSAO)
    comissao = logar(COMISSAO)
    assert _redefinir(cliente, token_comum).status_code == 200
    assert comissao.get("/api/acesso/eu").status_code == 200


def test_redefinir_tira_o_bloqueio_por_senhas_erradas(cliente, engine_app, criar_token):
    for _ in range(5):
        _post(cliente, "/api/acesso/entrar", {"login": COMUM, "senha": "errada-errada"})
    bloqueado = _post(cliente, "/api/acesso/entrar", {"login": COMUM, "senha": f"senha-{COMUM}"})
    assert bloqueado.status_code == 423
    assert _redefinir(cliente, criar_token()).status_code == 200
    cliente.cookies.clear()
    assert _post(cliente, "/api/acesso/entrar", {"login": COMUM, "senha": SENHA}).status_code == 200


def test_falha_nao_troca_a_senha(cliente, engine_app, criar_token, engine_superusuario):
    token = criar_token()
    _vencer(engine_superusuario, token)
    _invalido(_redefinir(cliente, token))
    entrar = _post(cliente, "/api/acesso/entrar", {"login": COMUM, "senha": f"senha-{COMUM}"})
    assert entrar.status_code == 200
    assert historico(engine_app, "senha_redefinida") == []


def test_senha_digitada_nao_volta_na_resposta(cliente, criar_token):
    resposta = _redefinir(cliente, criar_token())
    assert SENHA not in resposta.text
