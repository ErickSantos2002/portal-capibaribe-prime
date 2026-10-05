"""Validações do contrato (spec do M1, seção 4): mensagens em português, sem o valor digitado."""

import pytest
from pydantic import ValidationError

from app.esquemas.acesso import (
    ApagarDados,
    DadosDaUnidade,
    Entrar,
    PrimeiroAcesso,
    TrocarSenha,
)
from app.esquemas.administracao import ConfirmarReset
from app.esquemas.avisos import CorrigirAviso, NovoAviso
from app.main import app
from app.seguranca.dependencias import exige_cabecalho_portal

SENHA = "boa-senha-1"
CONTATO = {"responsavel_nome": "Maria (fictícia)", "celular": "(81) 9 1234-5678"}


def _mensagens(erro: pytest.ExceptionInfo[ValidationError]) -> dict[str, str]:
    return {
        str(e["loc"][0]): str((e.get("ctx") or {}).get("error", e["msg"]))
        for e in erro.value.errors()
    }


def _primeiro_acesso(**mudancas) -> PrimeiroAcesso:
    dados = {"senha_nova": SENHA, "senha_nova_repetida": SENHA, **CONTATO, **mudancas}
    return PrimeiroAcesso(**dados)


# --- épico A ---------------------------------------------------------------------------------


def test_primeiro_acesso_normaliza():
    dados = _primeiro_acesso(email="  Maria@Example.COM ", responsavel_nome="  Maria  ")
    assert dados.celular == "81912345678"
    assert dados.email == "maria@example.com"
    assert dados.responsavel_nome == "Maria"
    assert _primeiro_acesso(email="").email is None
    assert _primeiro_acesso(email="   ").email is None
    assert _primeiro_acesso().email is None
    assert _primeiro_acesso(celular="81 3333-4444").celular == "8133334444"


@pytest.mark.parametrize(
    ("mudancas", "campo", "mensagem"),
    [
        (
            {"senha_nova": "curta", "senha_nova_repetida": "curta"},
            "senha_nova",
            "A senha nova precisa ter pelo menos 8 letras ou números.",
        ),
        (
            {"senha_nova": "mudar123", "senha_nova_repetida": "mudar123"},
            "senha_nova",
            "Escolha uma senha diferente da inicial, que todo mundo conhece.",
        ),
        (
            {"senha_nova_repetida": "outra-senha"},
            "senha_nova_repetida",
            "As duas senhas estão diferentes. Escreva a mesma nas duas.",
        ),
        (
            {"responsavel_nome": "   "},
            "responsavel_nome",
            "Escreva o nome de quem responde pela unidade.",
        ),
        (
            {"responsavel_nome": "x" * 101},
            "responsavel_nome",
            "O nome pode ter até 100 letras.",
        ),
        (
            {"celular": "9 1234-5678"},
            "celular",
            "Confira o celular: DDD e número, como (81) 9 1234-5678.",
        ),
        (
            {"celular": "(81) 9 1234-56789"},
            "celular",
            "Confira o celular: DDD e número, como (81) 9 1234-5678.",
        ),
        ({"email": "maria.example.com"}, "email", "Confira o e-mail, ou deixe em branco."),
    ],
)
def test_primeiro_acesso_recusa(mudancas, campo, mensagem):
    with pytest.raises(ValidationError) as erro:
        _primeiro_acesso(**mudancas)
    assert _mensagens(erro)[campo] == mensagem


def test_campo_desconhecido_e_erro():
    with pytest.raises(ValidationError):
        _primeiro_acesso(cpf="000")


@pytest.mark.parametrize("login", ["1101", "5708", "1007"])
def test_entrar_aceita_login_no_padrao(login):
    assert Entrar(login=login, senha="x").login == login


@pytest.mark.parametrize("login", ["101", "11011", "0101", "1801", "abcd", ""])
def test_entrar_recusa_login_fora_do_padrao(login):
    with pytest.raises(ValidationError) as erro:
        Entrar(login=login, senha="x")
    assert _mensagens(erro)["login"] == "Escolha o bloco e escreva o número do apartamento."


def test_entrar_exige_senha():
    with pytest.raises(ValidationError) as erro:
        Entrar(login="1101", senha="")
    assert _mensagens(erro)["senha"] == "Escreva a senha."


def test_trocar_senha_e_dados():
    TrocarSenha(senha_atual="qualquer", senha_nova=SENHA, senha_nova_repetida=SENHA)
    with pytest.raises(ValidationError):
        TrocarSenha(senha_atual="x", senha_nova="mudar123", senha_nova_repetida="mudar123")
    assert DadosDaUnidade(**CONTATO).celular == "81912345678"


@pytest.mark.parametrize("modelo", [ApagarDados, ConfirmarReset])
def test_confirmacao_precisa_ser_verdadeira(modelo):
    assert modelo(confirmo=True).confirmo is True
    for valor in (False, None):
        with pytest.raises(ValidationError):
            modelo(confirmo=valor)


# --- épico C ---------------------------------------------------------------------------------


def test_novo_aviso_normaliza():
    aviso = NovoAviso(
        titulo="  Vistoria  ",
        texto="  Linha 1\r\n\r\nLinha 2  ",
        para_todos=False,
        blocos=[3, 1, 3],
    )
    assert aviso.titulo == "Vistoria"
    assert aviso.texto == "Linha 1\n\nLinha 2"
    assert aviso.blocos == [1, 3]
    assert aviso.fixado is False
    assert NovoAviso(titulo="t", texto="x", para_todos=True, blocos=[2]).blocos == []


@pytest.mark.parametrize(
    ("mudancas", "campo", "mensagem"),
    [
        ({"titulo": " "}, "titulo", "Escreva o título do aviso."),
        ({"titulo": "t" * 121}, "titulo", "O título pode ter até 120 letras."),
        ({"texto": "\n"}, "texto", "Escreva o texto do aviso."),
        ({"texto": "x" * 10_001}, "texto", "O texto pode ter até 10.000 letras."),
        (
            {"para_todos": False, "blocos": []},
            "blocos",
            "Escolha pelo menos um bloco, ou Todos os blocos.",
        ),
    ],
)
def test_novo_aviso_recusa(mudancas, campo, mensagem):
    dados = {"titulo": "Título", "texto": "Texto", "para_todos": True, **mudancas}
    with pytest.raises(ValidationError) as erro:
        NovoAviso(**dados)
    assert _mensagens(erro)[campo] == mensagem


def test_corrigir_aviso_usa_as_mesmas_regras():
    with pytest.raises(ValidationError):
        CorrigirAviso(titulo="", texto="x")


# --- roteadores ------------------------------------------------------------------------------


def test_um_roteador_por_epico_no_app_e_com_csrf():
    from app.rotas import acesso, administracao, avisos, sessao

    # O FastAPI atual guarda cada roteador incluído inteiro (`original_router`).
    incluidos = [getattr(r, "original_router", None) for r in app.routes]
    for modulo in (sessao, acesso, administracao, avisos):
        assert any(r is modulo.rotas for r in incluidos), modulo.__name__
        dependencias = [d.dependency for d in modulo.rotas.dependencies]
        assert exige_cabecalho_portal in dependencias, modulo.__name__
