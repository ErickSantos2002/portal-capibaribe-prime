"""Dados fictícios para desenvolvimento (RNF-16): só rodam em local, teste ou prévia."""

import pytest
from argon2 import PasswordHasher
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modelos import Unidade, UnidadePapel
from app.servicos.carga_inicial import carregar
from app.servicos.dados_ficticios import ErroAmbiente, preencher_ficticios

pytestmark = pytest.mark.usefixtures("banco_limpo")

HASHER_RAPIDO = PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1)


@pytest.fixture
def carregado(engine_app):
    with Session(engine_app) as sessao:
        carregar(sessao, "1101", hasher=HASHER_RAPIDO)
        sessao.commit()


@pytest.mark.parametrize("ambiente", [None, "", "producao", "Local ", "preview"])
def test_recusa_fora_de_local_e_teste(engine_app, carregado, ambiente):
    with Session(engine_app) as sessao, pytest.raises(ErroAmbiente, match="PORTAL_AMBIENTE"):
        preencher_ficticios(sessao, ambiente)


def test_aceita_o_banco_das_previas(engine_app, carregado):
    # Branch do Neon só de estrutura usado pelas prévias da Vercel (spec do M1, seção 6).
    with Session(engine_app) as sessao:
        assert preencher_ficticios(sessao, "previa") > 0


def test_recusa_sem_carga_inicial(engine_app):
    with Session(engine_app) as sessao, pytest.raises(ErroAmbiente, match="carga inicial"):
        preencher_ficticios(sessao, "local")


def test_preenche_so_dado_ficticio(engine_app, carregado):
    with Session(engine_app) as sessao:
        alteradas = preencher_ficticios(sessao, "local")
        sessao.commit()
        ativas = sessao.scalars(select(Unidade).where(Unidade.ativada_em.is_not(None))).all()
    assert alteradas == len(ativas) > 0
    assert len(ativas) < 320  # parte do prédio continua "não ativada", como na vida real
    for u in ativas:
        assert u.responsavel_nome
        assert u.celular is not None and u.celular.startswith("8190000") and len(u.celular) == 11
        assert u.email is None or u.email.endswith("@example.com")
        assert not u.precisa_trocar_senha


def test_da_papel_de_comissao_ficticio(engine_app, carregado):
    with Session(engine_app) as sessao:
        preencher_ficticios(sessao, "teste")
        sessao.commit()
        papeis = sessao.scalars(select(UnidadePapel.papel)).all()
    assert sorted(p.value for p in papeis).count("comissao") >= 1


def test_rodar_de_novo_nao_muda_nada(engine_app, carregado):
    with Session(engine_app) as sessao:
        preencher_ficticios(sessao, "local")
        sessao.commit()
        antes = sessao.execute(
            select(Unidade.login, Unidade.responsavel_nome).order_by(Unidade.login)
        ).all()
        n_papeis = len(sessao.scalars(select(UnidadePapel)).all())
    with Session(engine_app) as sessao:
        assert preencher_ficticios(sessao, "local") == 0
        sessao.commit()
        depois = sessao.execute(
            select(Unidade.login, Unidade.responsavel_nome).order_by(Unidade.login)
        ).all()
        assert len(sessao.scalars(select(UnidadePapel)).all()) == n_papeis
    assert antes == depois
