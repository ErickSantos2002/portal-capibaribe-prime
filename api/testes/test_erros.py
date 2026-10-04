"""Exceções não tratadas vão para a tabela `erro`, sem dado pessoal (modelo, seção 3.6)."""

import logging

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app import banco
from app.main import app
from app.servicos.erros import ErroDoPortal, RegistroDeErros, mensagem_segura

pytestmark = pytest.mark.usefixtures("banco_limpo")

SEGREDO = "segredo-de-teste-123"
ROTA = "/api/diagnostico/erro"


def _erros(engine_dono) -> list[tuple]:
    with engine_dono.connect() as con:
        return [
            tuple(linha)
            for linha in con.execute(text("select rota, tipo, mensagem, unidade_id from erro"))
        ]


# --- rota de diagnóstico ------------------------------------------------------------------


def test_diagnostico_sem_variavel_configurada_e_404(cliente, monkeypatch, engine_dono):
    monkeypatch.delenv("PORTAL_DIAGNOSTICO_SEGREDO", raising=False)
    resposta = cliente.post(ROTA, headers={"X-Portal-Diagnostico": SEGREDO})
    assert resposta.status_code == 404
    assert _erros(engine_dono) == []


@pytest.mark.parametrize("cabecalho", [None, "", "errado", SEGREDO + "x", SEGREDO[:-1]])
def test_diagnostico_com_segredo_errado_e_404(cliente, monkeypatch, engine_dono, cabecalho):
    monkeypatch.setenv("PORTAL_DIAGNOSTICO_SEGREDO", SEGREDO)
    headers = {} if cabecalho is None else {"X-Portal-Diagnostico": cabecalho}
    resposta = cliente.post(ROTA, headers=headers)
    assert resposta.status_code == 404
    # Igual a uma rota que não existe: não revela que ela está ali.
    assert resposta.json() == cliente.post("/api/nao-existe").json()
    assert _erros(engine_dono) == []


def test_diagnostico_com_variavel_vazia_e_404(cliente, monkeypatch):
    monkeypatch.setenv("PORTAL_DIAGNOSTICO_SEGREDO", "")
    assert cliente.post(ROTA, headers={"X-Portal-Diagnostico": ""}).status_code == 404


@pytest.mark.parametrize("metodo", ["GET", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
@pytest.mark.parametrize("com_segredo", [False, True])
def test_diagnostico_por_outro_metodo_e_404_identico(
    cliente, monkeypatch, engine_dono, metodo, com_segredo
):
    # 405 revelaria que a rota existe: qualquer outro método responde igual a rota inexistente.
    monkeypatch.setenv("PORTAL_DIAGNOSTICO_SEGREDO", SEGREDO)
    headers = {"X-Portal-Diagnostico": SEGREDO} if com_segredo else {}
    resposta = cliente.request(metodo, ROTA, headers=headers)
    inexistente = cliente.request(metodo, "/api/diagnostico/nao-existe", headers=headers)
    assert resposta.status_code == inexistente.status_code == 404
    assert resposta.content == inexistente.content
    assert "allow" not in resposta.headers
    assert _erros(engine_dono) == []


def test_erro_forcado_grava_na_tabela_erro(cliente, monkeypatch, engine_dono):
    monkeypatch.setenv("PORTAL_DIAGNOSTICO_SEGREDO", SEGREDO)
    resposta = cliente.post(ROTA, headers={"X-Portal-Diagnostico": SEGREDO})
    assert resposta.status_code == 500
    assert resposta.json() == {"detail": "Erro interno"}
    [(rota, tipo, mensagem, unidade_id)] = _erros(engine_dono)
    assert rota == "POST /api/diagnostico/erro"
    assert tipo == "ErroDiagnostico"
    assert "forçado" in mensagem
    assert unidade_id is None


def test_banco_fora_do_ar_ainda_responde_500_limpo(monkeypatch):
    monkeypatch.setenv("PORTAL_DIAGNOSTICO_SEGREDO", SEGREDO)
    monkeypatch.setenv("DATABASE_URL", "postgresql://app:x@127.0.0.1:1/nada")
    banco.obter_engine.cache_clear()
    try:
        cliente = TestClient(app, raise_server_exceptions=False)
        resposta = cliente.post(ROTA, headers={"X-Portal-Diagnostico": SEGREDO})
        assert resposta.status_code == 500
        assert resposta.json() == {"detail": "Erro interno"}
    finally:
        banco.obter_engine.cache_clear()


# --- mensagem sem dado pessoal ------------------------------------------------------------


def test_mensagem_de_erro_do_banco_nao_leva_valores(engine_app):
    with engine_app.begin() as con:
        b = con.execute(
            text("insert into bloco (numero, nome) values (1, 'Bloco 1') returning id")
        ).scalar_one()
    inserir = text(
        "insert into unidade (bloco_id, numero, andar, senha_hash, email)"
        " values (:b, '101', 1, 'h', :email)"
    )
    with engine_app.begin() as con:
        con.execute(inserir, {"b": b, "email": "fulano@example.com"})
    with pytest.raises(IntegrityError) as erro, engine_app.begin() as con:
        con.execute(inserir, {"b": b, "email": "fulano@example.com"})

    mensagem = mensagem_segura(erro.value)
    assert "fulano" not in mensagem
    assert "DETAIL" not in mensagem
    assert "101" not in mensagem
    assert "UniqueViolation" in mensagem
    assert "23505" in mensagem


def test_mensagem_de_conversao_invalida_nao_leva_o_valor(engine_app):
    with pytest.raises(Exception) as erro, engine_app.connect() as con:
        con.execute(text("select cast(:v as integer)"), {"v": "fulano@example.com"})
    assert "fulano" not in mensagem_segura(erro.value)


def test_mensagem_de_validacao_nao_leva_o_valor():
    class Contato(BaseModel):
        idade: int

    with pytest.raises(ValidationError) as erro:
        Contato(idade="fulano@example.com")
    mensagem = mensagem_segura(erro.value)
    assert "fulano" not in mensagem
    assert "idade" in mensagem


def test_mensagem_do_portal_fica_so_na_primeira_linha_e_limitada():
    assert mensagem_segura(ErroDoPortal("linha 1\nlinha 2")) == "linha 1"
    assert len(mensagem_segura(ErroDoPortal("x" * 5000))) == 500
    assert mensagem_segura(ErroDoPortal()) == ""


def _levantar(funcao):
    try:
        funcao()
    except Exception as exc:  # noqa: BLE001
        return exc
    raise AssertionError("não levantou")


def test_value_error_de_conversao_nao_leva_o_que_foi_digitado():
    exc = _levantar(lambda: int("81 99876-5432"))
    mensagem = mensagem_segura(exc)
    assert "99876" not in mensagem
    assert mensagem.startswith("ValueError em ")
    assert "test_erros.py:" in mensagem  # onde aconteceu, para achar no código


def test_key_error_nao_leva_a_chave():
    exc = _levantar(lambda: {}["joao.silva@gmail.com"])
    mensagem = mensagem_segura(exc)
    assert "joao" not in mensagem
    assert mensagem.startswith("KeyError em ")


def test_excecao_generica_com_dado_na_mensagem_nao_leva_o_dado():
    def falhar():
        raise RuntimeError("cadastro de Maria Souza, celular (81) 99876-5432")

    mensagem = mensagem_segura(_levantar(falhar))
    assert "Maria" not in mensagem and "99876" not in mensagem
    assert mensagem.startswith("RuntimeError em ")


def test_excecao_generica_sem_traceback_fica_so_com_o_tipo():
    assert mensagem_segura(ValueError("joao.silva@gmail.com")) == "ValueError"


# --- o log do servidor também não leva dado pessoal ----------------------------------------


@pytest.fixture
def cliente_com_falhas(cliente):
    """Uma API mínima com o mesmo tratamento de erro da principal e rotas que falham."""
    falhas = FastAPI()
    falhas.add_middleware(RegistroDeErros)

    @falhas.post("/api/falha/{tipo}")
    def falhar(tipo: str):
        if tipo == "conversao":
            int("81 99876-5432")
        if tipo == "chave":
            _ = {}["joao.silva@gmail.com"]
        with banco.fabrica_de_sessoes()() as sessao:
            # IntegrityError do Postgres: DETAIL leva o valor duplicado.
            sessao.execute(text("insert into bloco (numero, nome) values (1, 'joao.silva')"))
            sessao.execute(text("insert into bloco (numero, nome) values (1, 'joao.silva')"))

    return TestClient(falhas, raise_server_exceptions=True)


@pytest.mark.parametrize("tipo", ["conversao", "chave", "integridade"])
def test_excecao_nao_e_relancada_e_o_log_nao_leva_dado(
    cliente_com_falhas, engine_dono, caplog, tipo
):
    caplog.set_level(logging.DEBUG)
    # raise_server_exceptions=True: se a exceção fosse relançada (e chegasse ao log do
    # servidor com o traceback), o TestClient a levantaria aqui.
    resposta = cliente_com_falhas.post(f"/api/falha/{tipo}")
    assert resposta.status_code == 500
    assert resposta.json() == {"detail": "Erro interno"}
    assert "99876" not in caplog.text
    assert "joao" not in caplog.text
    assert "Erro não tratado em POST /api/falha/{tipo}" in caplog.text
    [(rota, _tipo, mensagem, _u)] = _erros(engine_dono)
    assert rota == "POST /api/falha/{tipo}"
    assert "joao" not in mensagem and "99876" not in mensagem


def test_api_principal_nao_relanca_a_excecao(cliente, monkeypatch):
    monkeypatch.setenv("PORTAL_DIAGNOSTICO_SEGREDO", SEGREDO)
    estrita = TestClient(app, raise_server_exceptions=True)
    resposta = estrita.post(ROTA, headers={"X-Portal-Diagnostico": SEGREDO})
    assert resposta.status_code == 500


def test_conexao_recusada_nao_leva_a_url():
    with pytest.raises(psycopg.OperationalError) as erro:
        psycopg.connect("postgresql://app:senha-secreta@127.0.0.1:1/nada", connect_timeout=2)
    assert "senha-secreta" not in mensagem_segura(erro.value)
