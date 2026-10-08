"""Configuração do bucket de arquivos por variável de ambiente (spec do M3, seção 6).

Sem as variáveis, os arquivos ficam desligados e o resto do Portal funciona igual. A chave da
API nunca aponta para o bucket de backups (ADR-0009). Nenhum segredo aparece em `repr` nem em
log.
"""

import logging

import pytest

from app import configuracao

VARIAVEIS = [
    "PORTAL_ARQUIVOS_ENDPOINT",
    "PORTAL_ARQUIVOS_BUCKET",
    "PORTAL_ARQUIVOS_CHAVE_ID",
    "PORTAL_ARQUIVOS_CHAVE_SECRETA",
    "PORTAL_ARQUIVOS_REGIAO",
]
SEGREDO = "segredo-de-teste-que-nao-pode-vazar"


@pytest.fixture(autouse=True)
def ambiente_limpo(monkeypatch):
    for nome in VARIAVEIS:
        monkeypatch.delenv(nome, raising=False)
    configuracao.limpar_cache()
    yield
    configuracao.limpar_cache()


def _ligar(monkeypatch, **trocas: str) -> None:
    valores = {
        "PORTAL_ARQUIVOS_ENDPOINT": "https://conta-ficticia.r2.cloudflarestorage.com",
        "PORTAL_ARQUIVOS_BUCKET": "portal-capibaribe-arquivos",
        "PORTAL_ARQUIVOS_CHAVE_ID": "id-de-teste",
        "PORTAL_ARQUIVOS_CHAVE_SECRETA": SEGREDO,
        **trocas,
    }
    for nome, valor in valores.items():
        monkeypatch.setenv(nome, valor)


def test_sem_variaveis_arquivos_desligados_sem_aviso(caplog):
    with caplog.at_level(logging.WARNING):
        assert configuracao.config_arquivos() is None
    assert caplog.records == []


def test_ligado_com_regiao_padrao(monkeypatch):
    _ligar(monkeypatch, PORTAL_ARQUIVOS_ENDPOINT="https://conta-ficticia.r2.cloudflarestorage.com/")
    config = configuracao.config_arquivos()
    assert config is not None
    assert config.endpoint == "https://conta-ficticia.r2.cloudflarestorage.com"
    assert config.bucket == "portal-capibaribe-arquivos"
    assert config.chave_id == "id-de-teste"
    assert config.chave_secreta == SEGREDO
    assert config.regiao == "auto"


def test_regiao_trocavel(monkeypatch):
    _ligar(monkeypatch, PORTAL_ARQUIVOS_REGIAO="us-east-1")
    assert configuracao.config_arquivos().regiao == "us-east-1"


def test_segredo_fora_do_repr(monkeypatch):
    _ligar(monkeypatch)
    assert SEGREDO not in repr(configuracao.config_arquivos())


@pytest.mark.parametrize("faltando", VARIAVEIS[:4])
def test_pela_metade_desliga_com_aviso_sem_valor(monkeypatch, caplog, faltando):
    _ligar(monkeypatch)
    monkeypatch.delenv(faltando)
    with caplog.at_level(logging.WARNING):
        assert configuracao.config_arquivos() is None
    assert "arquivos desligados" in caplog.text
    assert SEGREDO not in caplog.text


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://conta.r2.cloudflarestorage.com",
        "ftp://conta.r2.cloudflarestorage.com",
        "https://conta.r2.cloudflarestorage.com/caminho",
        "https://usuario@conta.r2.cloudflarestorage.com",
        "conta.r2.cloudflarestorage.com",
    ],
)
def test_endpoint_so_https_sem_caminho(monkeypatch, caplog, endpoint):
    _ligar(monkeypatch, PORTAL_ARQUIVOS_ENDPOINT=endpoint)
    with caplog.at_level(logging.WARNING):
        assert configuracao.config_arquivos() is None
    assert "PORTAL_ARQUIVOS_ENDPOINT" in caplog.text


@pytest.mark.parametrize("endpoint", ["http://127.0.0.1:9000", "http://localhost:4566"])
def test_endpoint_local_vale_em_desenvolvimento(monkeypatch, endpoint):
    _ligar(monkeypatch, PORTAL_ARQUIVOS_ENDPOINT=endpoint)
    assert configuracao.config_arquivos().endpoint == endpoint


@pytest.mark.parametrize("bucket", ["portal-capibaribe-backups", "meus-backups", "BACKUP-x"])
def test_nunca_o_bucket_de_backups(monkeypatch, caplog, bucket):
    _ligar(monkeypatch, PORTAL_ARQUIVOS_BUCKET=bucket)
    with caplog.at_level(logging.WARNING):
        assert configuracao.config_arquivos() is None
    assert "backup" in caplog.text


@pytest.mark.parametrize("bucket", ["ab", "Maiusculas", "com_sublinhado", "-comeca", "a" * 64])
def test_nome_de_bucket_no_padrao(monkeypatch, bucket):
    _ligar(monkeypatch, PORTAL_ARQUIVOS_BUCKET=bucket)
    assert configuracao.config_arquivos() is None


def test_le_de_novo_quando_a_variavel_muda(monkeypatch):
    _ligar(monkeypatch)
    assert configuracao.config_arquivos() is not None
    monkeypatch.delenv("PORTAL_ARQUIVOS_BUCKET")
    assert configuracao.config_arquivos() is None
