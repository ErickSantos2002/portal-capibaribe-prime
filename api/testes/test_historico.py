"""Registro no histórico (H-11, RNF-14): função comum que os épicos chamam."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modelos import Historico
from app.servicos.erros import ErroDoPortal
from app.servicos.historico import Acao, registrar
from testes.apoio import criar_bloco, criar_unidade

pytestmark = pytest.mark.usefixtures("banco_limpo")


@pytest.fixture
def unidade(engine_app) -> int:
    with engine_app.begin() as con:
        return criar_unidade(con, criar_bloco(con, 1), "101")


def test_registra_acao_com_detalhes(engine_app, unidade):
    with Session(engine_app) as db:
        registrar(
            db,
            Acao.papel_concedido,
            unidade_id=unidade,
            entidade="unidade",
            entidade_id=unidade,
            detalhes={"papel": "comissao", "blocos": [1, 2], "fixado": True, "nada": None},
        )
        db.commit()
        linha = db.scalars(select(Historico)).one()
    assert (linha.acao, linha.unidade_id, linha.entidade, linha.entidade_id) == (
        "papel_concedido",
        unidade,
        "unidade",
        unidade,
    )
    assert linha.detalhes == {"papel": "comissao", "blocos": [1, 2], "fixado": True, "nada": None}


def test_acao_do_sistema_sem_unidade(engine_app):
    with Session(engine_app) as db:
        registrar(db, Acao.unidade_bloqueada, unidade_id=None)
        db.commit()
        linha = db.scalars(select(Historico)).one()
    assert linha.unidade_id is None
    assert linha.detalhes == {}


@pytest.mark.parametrize(
    "chave", ["senha", "senha_nova", "celular", "email", "responsavel_nome", "nome", "token"]
)
def test_recusa_dado_pessoal_nos_detalhes(engine_app, chave):
    with Session(engine_app) as db, pytest.raises(ErroDoPortal, match="pessoal"):
        registrar(db, Acao.dados_apagados, unidade_id=None, detalhes={chave: "x"})


def test_recusa_valor_aninhado(engine_app):
    with Session(engine_app) as db, pytest.raises(ErroDoPortal, match="simples"):
        registrar(db, Acao.aviso_publicado, unidade_id=None, detalhes={"a": {"celular": "8"}})


def test_acoes_do_m1():
    assert {a.value for a in Acao} >= {
        "primeiro_acesso",
        "unidade_bloqueada",
        "unidade_resetada",
        "papel_concedido",
        "papel_retirado",
        "aviso_publicado",
        "aviso_corrigido",
        "aviso_arquivado",
        "dados_apagados",
    }
