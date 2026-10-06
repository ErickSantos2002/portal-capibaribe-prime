"""Configuração de push e e-mail por variável de ambiente (spec do M2, seção 6).

Sem as variáveis, push e e-mail ficam desligados e nada quebra. Nenhum segredo aparece em
`repr` nem em log.
"""

import logging

import pytest
from py_vapid import Vapid

from app import configuracao
from app.comandos import gerar_chaves_vapid

VARIAVEIS = [
    "PORTAL_VAPID_PRIVADA",
    "PORTAL_VAPID_CONTATO",
    "PORTAL_SMTP_USUARIO",
    "PORTAL_SMTP_SENHA_APP",
    "PORTAL_SMTP_HOST",
    "PORTAL_SMTP_PORTA",
    "PORTAL_URL_BASE",
]


@pytest.fixture(autouse=True)
def ambiente_limpo(monkeypatch):
    for nome in VARIAVEIS:
        monkeypatch.delenv(nome, raising=False)
    configuracao.limpar_cache()
    yield
    configuracao.limpar_cache()


def _chave_privada() -> str:
    return gerar_chaves_vapid.gerar().privada


def _ligar_push(monkeypatch, privada: str | None = None) -> str:
    privada = privada or _chave_privada()
    monkeypatch.setenv("PORTAL_VAPID_PRIVADA", privada)
    monkeypatch.setenv("PORTAL_VAPID_CONTATO", "mailto:portal@example.com")
    return privada


def _ligar_email(monkeypatch) -> None:
    monkeypatch.setenv("PORTAL_SMTP_USUARIO", "portal@example.com")
    monkeypatch.setenv("PORTAL_SMTP_SENHA_APP", "abcd efgh ijkl mnop")
    monkeypatch.setenv("PORTAL_URL_BASE", "https://portal.example.com/")


# --- push -------------------------------------------------------------------------------------


def test_sem_variaveis_push_e_email_desligados():
    assert configuracao.config_push() is None
    assert configuracao.config_email() is None
    assert configuracao.url_base() is None


def test_push_ligado_deriva_a_chave_publica(monkeypatch):
    privada = _ligar_push(monkeypatch)
    config = configuracao.config_push()
    assert config is not None
    assert config.contato == "mailto:portal@example.com"
    # Chave pública: ponto P-256 não comprimido (65 bytes), em base64url sem "=".
    assert len(config.chave_publica) == 87 and "=" not in config.chave_publica
    esperada = Vapid.from_string(privada).public_key
    assert config.chave_publica == gerar_chaves_vapid.publica_de(esperada)


@pytest.mark.parametrize(
    "faltando", ["PORTAL_VAPID_PRIVADA", "PORTAL_VAPID_CONTATO"], ids=["privada", "contato"]
)
def test_push_pela_metade_fica_desligado(monkeypatch, faltando, caplog):
    _ligar_push(monkeypatch)
    monkeypatch.setenv(faltando, "  ")
    with caplog.at_level(logging.WARNING):
        assert configuracao.config_push() is None
    assert "push desligado" in caplog.text


@pytest.mark.parametrize(
    ("privada", "contato"),
    [
        ("nao-e-chave", "mailto:portal@example.com"),
        (None, "portal@example.com"),
        (None, "http://example.com"),
    ],
)
def test_push_com_valor_invalido_fica_desligado_sem_mostrar_a_chave(
    monkeypatch, caplog, privada, contato
):
    _ligar_push(monkeypatch, privada)
    monkeypatch.setenv("PORTAL_VAPID_CONTATO", contato)
    with caplog.at_level(logging.WARNING):
        assert configuracao.config_push() is None
    assert "nao-e-chave" not in caplog.text


def test_chave_privada_nao_aparece_no_repr(monkeypatch):
    privada = _ligar_push(monkeypatch)
    assert privada not in repr(configuracao.config_push())


# --- e-mail -----------------------------------------------------------------------------------


def test_email_ligado_com_padroes_do_gmail(monkeypatch):
    _ligar_email(monkeypatch)
    config = configuracao.config_email()
    assert config is not None
    assert (config.host, config.porta) == ("smtp.gmail.com", 465)
    assert config.usuario == "portal@example.com"
    assert config.url_base == "https://portal.example.com"
    assert config.remetente_nome == "Portal Capibaribe Prime"
    assert "abcd" not in repr(config)


@pytest.mark.parametrize(
    "faltando", ["PORTAL_SMTP_USUARIO", "PORTAL_SMTP_SENHA_APP", "PORTAL_URL_BASE"]
)
def test_email_pela_metade_fica_desligado(monkeypatch, faltando, caplog):
    _ligar_email(monkeypatch)
    monkeypatch.delenv(faltando)
    with caplog.at_level(logging.WARNING):
        assert configuracao.config_email() is None
    assert "e-mail desligado" in caplog.text


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (
            "https://portal-capibaribe-prime.vercel.app",
            "https://portal-capibaribe-prime.vercel.app",
        ),
        ("https://portal.example.com///", "https://portal.example.com"),
        ("http://localhost:5173", "http://localhost:5173"),
        ("http://127.0.0.1:5173/", "http://127.0.0.1:5173"),
        ("http://portal.example.com", None),
        ("https://portal.example.com/caminho", None),
        ("https://portal.example.com?x=1", None),
        ("javascript:alert(1)", None),
        ("", None),
    ],
)
def test_url_base_so_https_ou_maquina_local(monkeypatch, valor, esperado):
    monkeypatch.setenv("PORTAL_URL_BASE", valor)
    assert configuracao.url_base() == esperado


def test_porta_invalida_desliga_o_email(monkeypatch):
    _ligar_email(monkeypatch)
    monkeypatch.setenv("PORTAL_SMTP_PORTA", "quatro")
    assert configuracao.config_email() is None
    monkeypatch.setenv("PORTAL_SMTP_PORTA", "587")
    configuracao.limpar_cache()
    assert configuracao.config_email().porta == 587


# --- comando de gerar as chaves ---------------------------------------------------------------


def test_comando_gera_par_que_a_configuracao_aceita(monkeypatch, capsys):
    gerar_chaves_vapid.main()
    saida = capsys.readouterr().out
    linhas = dict(
        linha.split("=", 1) for linha in saida.splitlines() if linha.startswith("PORTAL_")
    )
    _ligar_push(monkeypatch, linhas["PORTAL_VAPID_PRIVADA"])
    assert configuracao.config_push().chave_publica in saida
    # Cada execução gera um par novo: nada fixo no repositório.
    assert gerar_chaves_vapid.gerar().privada != gerar_chaves_vapid.gerar().privada
