"""Carga inicial: 5 blocos, 320 unidades e o admin (modelo de dados, seção 7)."""

import pytest
from argon2 import PasswordHasher
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.comandos import carga_inicial as comando
from app.modelos import Bloco, Historico, Unidade, UnidadePapel
from app.servicos.carga_inicial import ErroCarga, carregar, logins_planejados

pytestmark = pytest.mark.usefixtures("banco_limpo")

# Argon2id com custo baixo só para o teste não levar 15 s; a produção usa o padrão.
HASHER_RAPIDO = PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1)
ADMIN = "1101"  # unidade fictícia; a real vem de PORTAL_ADMIN_UNIDADE em produção


def _carregar(engine, admin=ADMIN):
    with Session(engine) as sessao:
        resumo = carregar(sessao, admin, hasher=HASHER_RAPIDO)
        sessao.commit()
    return resumo


def _contar(engine, modelo) -> int:
    with Session(engine) as sessao:
        return sessao.scalar(select(func.count()).select_from(modelo))


def test_logins_planejados():
    logins = logins_planejados()
    assert len(logins) == 320
    assert logins[:3] == ["1001", "1002", "1003"]
    assert "1008" in logins and "1009" not in logins
    assert "1101" in logins and "1708" in logins and "1801" not in logins
    assert logins[-1] == "5708"


def test_carga_cria_blocos_e_unidades(engine_app):
    resumo = _carregar(engine_app)
    assert (resumo.blocos_criados, resumo.unidades_criadas, resumo.admin_concedido) == (
        5,
        320,
        True,
    )
    with Session(engine_app) as sessao:
        assert sessao.scalars(select(Bloco.nome).order_by(Bloco.numero)).all() == [
            f"Bloco {n}" for n in range(1, 6)
        ]
        logins = sessao.scalars(select(Unidade.login).order_by(Unidade.login)).all()
        assert logins == logins_planejados()
        terreo = sessao.scalars(select(Unidade).where(Unidade.login == "3007")).one()
        assert (terreo.numero, terreo.andar) == ("007", 0)


def test_unidades_nascem_com_senha_inicial_e_nao_ativadas(engine_app):
    _carregar(engine_app)
    with Session(engine_app) as sessao:
        unidades = sessao.scalars(select(Unidade)).all()
    assert all(u.precisa_trocar_senha and u.ativada_em is None for u in unidades)
    assert all(u.responsavel_nome is None and u.email is None for u in unidades)
    assert all(u.senha_hash.startswith("$argon2id$") for u in unidades)
    assert PasswordHasher().verify(unidades[0].senha_hash, "mudar123")
    # Cada unidade tem o próprio sal: hashes iguais denunciariam senhas iguais.
    assert len({u.senha_hash for u in unidades}) == 320


def test_admin_na_unidade_da_variavel(engine_app):
    _carregar(engine_app, admin="2304")
    with Session(engine_app) as sessao:
        papeis = sessao.execute(
            select(Unidade.login, UnidadePapel.papel).join(
                Unidade, Unidade.id == UnidadePapel.unidade_id
            )
        ).all()
    assert [(login, papel.value) for login, papel in papeis] == [("2304", "admin")]


def test_rodar_duas_vezes_nao_duplica_nem_troca_a_senha(engine_app):
    _carregar(engine_app)
    with Session(engine_app) as sessao:
        hash_antes = sessao.scalar(select(Unidade.senha_hash).where(Unidade.login == "1101"))
    resumo = _carregar(engine_app)
    assert (resumo.blocos_criados, resumo.unidades_criadas, resumo.admin_concedido) == (
        0,
        0,
        False,
    )
    assert _contar(engine_app, Bloco) == 5
    assert _contar(engine_app, Unidade) == 320
    assert _contar(engine_app, UnidadePapel) == 1
    with Session(engine_app) as sessao:
        assert sessao.scalar(select(Unidade.senha_hash).where(Unidade.login == "1101")) == (
            hash_antes
        )


def test_carga_completa_o_que_falta(engine_app, engine_dono):
    _carregar(engine_app)
    with engine_dono.begin() as con:
        con.execute(text("delete from unidade_papel"))
        con.execute(text("delete from unidade where login in ('5708', '5707')"))
    resumo = _carregar(engine_app)
    assert (resumo.unidades_criadas, resumo.admin_concedido) == (2, True)
    assert _contar(engine_app, Unidade) == 320


@pytest.mark.parametrize("admin", [None, "", "  ", "9999", "1009", "6101", "abcd", "11011"])
def test_admin_invalido_falha_sem_gravar_nada(engine_app, admin):
    with pytest.raises(ErroCarga, match="PORTAL_ADMIN_UNIDADE"):
        _carregar(engine_app, admin=admin)
    assert _contar(engine_app, Bloco) == 0
    assert _contar(engine_app, Unidade) == 0


def test_carga_registra_no_historico(engine_app):
    _carregar(engine_app)
    _carregar(engine_app)
    with Session(engine_app) as sessao:
        registros = sessao.scalars(select(Historico).order_by(Historico.id)).all()
    assert [r.acao for r in registros] == ["carga_inicial", "papel_concedido"]
    assert registros[0].detalhes == {"blocos": 5, "unidades": 320}
    assert registros[1].detalhes == {"papel": "admin"}
    assert registros[1].entidade == "unidade"


def test_comando_usa_a_variavel_de_ambiente(cliente, monkeypatch, capsys):
    # `cliente` já aponta DATABASE_URL para o usuário app.
    monkeypatch.setenv("PORTAL_ADMIN_UNIDADE", ADMIN)
    monkeypatch.setattr(comando, "HASHER", HASHER_RAPIDO)
    assert comando.main() == 0
    assert "320 unidades" in capsys.readouterr().out
    assert cliente.get("/api/saude").json() == {"status": "ok", "unidades": 320}


def test_comando_sem_variavel_explica_e_sai_com_erro(cliente, monkeypatch, capsys):
    monkeypatch.delenv("PORTAL_ADMIN_UNIDADE", raising=False)
    assert comando.main() == 1
    assert "PORTAL_ADMIN_UNIDADE" in capsys.readouterr().err
