"""Formato de erro da API (spec do M1, seção 3.4): `codigo` estável e `mensagem` em português."""

from typing import Annotated

import pytest
from fastapi import FastAPI, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field, field_validator

from app.erros_api import ErroApi, instalar_tratadores


class Corpo(BaseModel):
    senha: str = Field(min_length=1)
    idade: int = 0

    @field_validator("senha")
    @classmethod
    def senha_forte(cls, valor: str) -> str:
        if len(valor) < 8:
            raise ValueError("A senha nova precisa ter pelo menos 8 letras ou números.")
        return valor


@pytest.fixture
def cliente() -> TestClient:
    app = FastAPI()
    instalar_tratadores(app)

    @app.get("/erro")
    def erro():
        raise ErroApi(423, "unidade_bloqueada", "Entrada bloqueada.", minutos_restantes=12)

    @app.post("/corpo")
    def corpo(dados: Corpo):
        return {"ok": True}

    @app.get("/consulta")
    def consulta(situacao: Annotated[str, Query(pattern="^(todas|ativadas)$")] = "todas"):
        return {"ok": True}

    return TestClient(app)


def test_erro_api_vira_codigo_e_mensagem(cliente):
    resposta = cliente.get("/erro")
    assert resposta.status_code == 423
    assert resposta.json() == {
        "codigo": "unidade_bloqueada",
        "mensagem": "Entrada bloqueada.",
        "minutos_restantes": 12,
    }


def test_validacao_usa_a_mensagem_do_validador(cliente):
    resposta = cliente.post("/corpo", json={"senha": "curta"})
    assert resposta.status_code == 422
    assert resposta.json() == {
        "codigo": "dados_invalidos",
        "mensagem": "A senha nova precisa ter pelo menos 8 letras ou números.",
        "campos": [
            {
                "campo": "senha",
                "mensagem": "A senha nova precisa ter pelo menos 8 letras ou números.",
            }
        ],
    }


def test_validacao_nunca_devolve_o_que_foi_digitado(cliente):
    resposta = cliente.post("/corpo", json={"senha": "segredo1", "idade": "vinte e dois"})
    assert resposta.status_code == 422
    assert "vinte e dois" not in resposta.text
    assert "segredo1" not in resposta.text
    assert resposta.json()["campos"] == [{"campo": "idade", "mensagem": "Valor inválido."}]


def test_campo_faltando(cliente):
    resposta = cliente.post("/corpo", json={})
    assert resposta.json()["campos"] == [{"campo": "senha", "mensagem": "Preencha este campo."}]


def test_corpo_que_nao_e_json(cliente):
    resposta = cliente.post(
        "/corpo", content=b"senha=abc", headers={"Content-Type": "application/json"}
    )
    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "dados_invalidos"
    assert "senha=abc" not in resposta.text


def test_parametro_de_consulta_invalido(cliente):
    resposta = cliente.get("/consulta", params={"situacao": "outra"})
    assert resposta.status_code == 422
    assert resposta.json()["campos"] == [{"campo": "situacao", "mensagem": "Valor inválido."}]


def test_rota_inexistente_mantem_o_formato_padrao(cliente):
    # A rota de diagnóstico do M0 precisa continuar idêntica a uma rota inexistente.
    assert cliente.get("/nao-existe").json() == {"detail": "Not Found"}
