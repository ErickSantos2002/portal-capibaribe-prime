"""Exceções não tratadas vão para a tabela `erro`, sem dado pessoal (modelo, seção 3.6)."""

import psycopg
import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app import banco
from app.main import app
from app.servicos.erros import mensagem_segura

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


def test_diagnostico_por_get_nao_dispara(cliente, monkeypatch, engine_dono):
    monkeypatch.setenv("PORTAL_DIAGNOSTICO_SEGREDO", SEGREDO)
    assert cliente.get(ROTA, headers={"X-Portal-Diagnostico": SEGREDO}).status_code in (404, 405)
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


def test_mensagem_comum_fica_so_na_primeira_linha_e_limitada():
    assert mensagem_segura(RuntimeError("linha 1\nlinha 2")) == "linha 1"
    assert len(mensagem_segura(RuntimeError("x" * 5000))) == 500
    assert mensagem_segura(RuntimeError()) == ""


def test_conexao_recusada_nao_leva_a_url():
    with pytest.raises(psycopg.OperationalError) as erro:
        psycopg.connect("postgresql://app:senha-secreta@127.0.0.1:1/nada", connect_timeout=2)
    assert "senha-secreta" not in mensagem_segura(erro.value)
