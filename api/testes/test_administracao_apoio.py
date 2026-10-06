"""Apoio dos testes do épico B (administração). Sem testes aqui: só funções usadas pelos outros
arquivos `test_administracao_*.py`."""

from typing import Any

from sqlalchemy import Engine, text

from testes.conftest import ADMIN, COMISSAO, COMUM, NAO_ATIVADA

__all__ = ["ADMIN", "COMISSAO", "COMUM", "NAO_ATIVADA", "contar", "fotografia", "linhas"]


def linhas(engine: Engine, sql: str, **parametros: Any) -> list[dict[str, Any]]:
    with engine.connect() as con:
        return [dict(r._mapping) for r in con.execute(text(sql), parametros)]


def contar(engine: Engine, sql: str, **parametros: Any) -> int:
    with engine.connect() as con:
        return con.execute(text(sql), parametros).scalar_one()


def fotografia(engine: Engine) -> dict[str, Any]:
    """Tudo o que uma rota de administração poderia alterar, para provar que nada mudou."""
    return {
        "historico": contar(engine, "select count(*) from historico"),
        "papeis": linhas(engine, "select * from unidade_papel order by id"),
        "unidades": linhas(
            engine,
            "select id, senha_hash, precisa_trocar_senha, ativada_em, responsavel_nome, celular,"
            " email from unidade order by id",
        ),
        "sessoes_abertas": contar(engine, "select count(*) from sessao where encerrada_em is null"),
    }
