"""Carga inicial: 5 blocos e 320 unidades (modelo de dados, seção 7).

Desde a revisão do M1, a carga não dá papel nenhum: uma conta de admin com a senha que todo
mundo conhece seria tomada por quem conhece o padrão. O admin vem depois, pelo comando
`promover_admin`, numa unidade que já fez o primeiro acesso (test_promover_admin.py).
"""

import pytest
from argon2 import PasswordHasher
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.comandos import carga_inicial as comando
from app.modelos import Bloco, Historico, Unidade, UnidadePapel
from app.servicos.carga_inicial import carregar, logins_planejados

pytestmark = pytest.mark.usefixtures("banco_limpo")

# Argon2id com custo baixo só para o teste não levar 15 s; a produção usa o padrão.
HASHER_RAPIDO = PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1)


def _carregar(engine):
    with Session(engine) as sessao:
        resumo = carregar(sessao, hasher=HASHER_RAPIDO)
        sessao.commit()
    return resumo


def _contar(engine, modelo) -> int:
    with Session(engine) as sessao:
        return sessao.execute(select(func.count()).select_from(modelo)).scalar_one()


def test_logins_planejados():
    logins = logins_planejados()
    assert len(logins) == 320
    assert logins[:3] == ["1001", "1002", "1003"]
    assert "1008" in logins and "1009" not in logins
    assert "1101" in logins and "1708" in logins and "1801" not in logins
    assert logins[-1] == "5708"


def test_carga_cria_blocos_e_unidades(engine_app):
    resumo = _carregar(engine_app)
    assert (resumo.blocos_criados, resumo.unidades_criadas) == (5, 320)
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


def test_carga_nao_da_papel_nenhum(engine_app):
    _carregar(engine_app)
    assert _contar(engine_app, UnidadePapel) == 0


def test_rodar_duas_vezes_nao_duplica_nem_troca_a_senha(engine_app):
    _carregar(engine_app)
    with Session(engine_app) as sessao:
        hash_antes = sessao.scalar(select(Unidade.senha_hash).where(Unidade.login == "1101"))
    resumo = _carregar(engine_app)
    assert (resumo.blocos_criados, resumo.unidades_criadas) == (0, 0)
    assert _contar(engine_app, Bloco) == 5
    assert _contar(engine_app, Unidade) == 320
    assert _contar(engine_app, UnidadePapel) == 0
    with Session(engine_app) as sessao:
        assert sessao.scalar(select(Unidade.senha_hash).where(Unidade.login == "1101")) == (
            hash_antes
        )


def test_carga_completa_o_que_falta(engine_app, engine_dono):
    _carregar(engine_app)
    with engine_dono.begin() as con:
        con.execute(text("delete from unidade where login in ('5708', '5707')"))
    resumo = _carregar(engine_app)
    assert resumo.unidades_criadas == 2
    assert _contar(engine_app, Unidade) == 320


def test_carga_registra_no_historico(engine_app):
    _carregar(engine_app)
    _carregar(engine_app)
    with Session(engine_app) as sessao:
        registros = sessao.scalars(select(Historico).order_by(Historico.id)).all()
    assert [r.acao for r in registros] == ["carga_inicial"]
    assert registros[0].detalhes == {"blocos": 5, "unidades": 320}


def test_comando_carrega_o_predio(cliente, monkeypatch, capsys):
    # `cliente` já aponta DATABASE_URL para o usuário app. Não precisa de variável de admin.
    monkeypatch.delenv("PORTAL_ADMIN_UNIDADE", raising=False)
    monkeypatch.setattr(comando, "HASHER", HASHER_RAPIDO)
    assert comando.main() == 0
    saida = capsys.readouterr().out
    assert "320 unidades" in saida and "promover_admin" in saida
    assert cliente.get("/api/saude").json() == {"status": "ok", "unidades": 320}
