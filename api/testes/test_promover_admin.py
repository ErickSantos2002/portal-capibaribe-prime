"""Comando `promover_admin`: o primeiro administrador nasce numa unidade já ativada.

Sequência de produção (spec do M1, seção 2.5): deploy → o Erick faz o primeiro acesso na
unidade dele → `python -m app.comandos.promover_admin <login>`.
"""

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.comandos import promover_admin as comando
from app.modelos import Historico, Papel, Unidade, UnidadePapel
from app.servicos.carga_inicial import carregar
from app.servicos.promover_admin import ErroPromocao, promover_admin

pytestmark = pytest.mark.usefixtures("banco_limpo")


@pytest.fixture
def carregado(engine_app, hasher_rapido) -> None:
    with Session(engine_app) as db:
        carregar(db, hasher=hasher_rapido)
        db.execute(
            update(Unidade)
            .where(Unidade.login == "1101")
            .values(
                ativada_em=func.now(),
                precisa_trocar_senha=False,
                responsavel_nome="Administração (fictícia)",
                celular="81900000000",
            )
        )
        db.commit()


def _admins(engine_app) -> list[str]:
    with Session(engine_app) as db:
        return list(
            db.scalars(
                select(Unidade.login)
                .join(UnidadePapel, UnidadePapel.unidade_id == Unidade.id)
                .where(UnidadePapel.papel == Papel.admin, UnidadePapel.retirado_em.is_(None))
            )
        )


def test_promove_unidade_ativada_e_registra(engine_app, carregado):
    with Session(engine_app) as db:
        assert promover_admin(db, "1101") is True
        db.commit()
        registro = db.scalars(select(Historico).where(Historico.acao == "papel_concedido")).one()
    assert _admins(engine_app) == ["1101"]
    assert registro.unidade_id is None  # ação do sistema (comando), não de uma unidade
    assert registro.entidade == "unidade"
    assert registro.detalhes == {"papel": "admin", "origem": "promover_admin"}


def test_idempotente(engine_app, carregado):
    with Session(engine_app) as db:
        promover_admin(db, "1101")
        db.commit()
        assert promover_admin(db, "1101") is False
        db.commit()
        quantos = db.scalar(select(func.count()).select_from(Historico))
    assert _admins(engine_app) == ["1101"]
    assert quantos == 2  # carga_inicial + um papel_concedido


def test_recusa_unidade_nao_ativada(engine_app, carregado):
    with Session(engine_app) as db, pytest.raises(ErroPromocao, match="primeiro acesso"):
        promover_admin(db, "2304")
    assert _admins(engine_app) == []


@pytest.mark.parametrize("login", ["", "9999", "abcd"])
def test_recusa_unidade_inexistente(engine_app, carregado, login):
    with Session(engine_app) as db, pytest.raises(ErroPromocao, match="não existe"):
        promover_admin(db, login)


def test_comando(cliente, carregado, engine_app, capsys):
    assert comando.main(["1101"]) == 0
    assert "1101" in capsys.readouterr().out
    assert comando.main(["1101"]) == 0
    assert "já" in capsys.readouterr().out
    assert comando.main(["2304"]) == 1
    assert "primeiro acesso" in capsys.readouterr().err
    assert comando.main([]) == 2
    assert _admins(engine_app) == ["1101"]
