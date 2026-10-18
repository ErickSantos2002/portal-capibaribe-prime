"""Regras de banco das indicações (migração 0010), com SQL direto: as tentativas de burlar.

Spec: `docs/superpowers/specs/2026-10-18-indicacoes-design.md`, seções 4 e 5. Cada tentativa
roda como `app` (o que a API usa), e as que dependem das triggers também como `dono`.
"""

import pytest
from psycopg.errors import InsufficientPrivilege
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError, ProgrammingError

from app.modelos.indicacoes import CATEGORIAS_INICIAIS
from testes.apoio import restricao
from testes.apoio_indicacoes import categoria_id, criar_prestador, opinar

pytestmark = pytest.mark.usefixtures("banco_limpo")


def _recusado(engine: Engine, nome: str, comando: str, **parametros) -> None:
    with pytest.raises(DBAPIError) as erro, engine.begin() as con:
        con.execute(text(comando), parametros)
    assert restricao(erro.value) == nome, erro.value


# --- tabelas, categorias e permissões (Tarefa 1) ------------------------------------------------


def test_categorias_iniciais_na_ordem(engine_app):
    with engine_app.connect() as con:
        nomes = con.execute(text("select nome from categoria_servico order by ordem")).scalars()
        nomes = list(nomes)
    assert nomes == [n for n, _ in CATEGORIAS_INICIAIS]
    assert nomes[0] == "Móveis planejados" and nomes[-1] == "Outros"


def test_segunda_opiniao_da_mesma_unidade_e_recusada(engine_app, ids):
    with engine_app.begin() as con:
        p = criar_prestador(con, ids["u"])
    with pytest.raises(IntegrityError, match="opiniao_servico_unica"), engine_app.begin() as con:
        opinar(con, p, ids["u"])


def test_telefone_repetido_e_recusado_mesmo_escondido(engine_app, engine_dono, ids):
    with engine_app.begin() as con:
        p = criar_prestador(con, ids["u"])
    with engine_dono.begin() as con:
        con.execute(
            text("update prestador set escondido_em = now(), escondido_por = :v where id = :p"),
            {"p": p, "v": ids["v"]},
        )
    with pytest.raises(IntegrityError, match="prestador_telefone_unico"), engine_app.begin() as con:
        criar_prestador(con, ids["v"], nome="Outra marcenaria")


@pytest.mark.parametrize("telefone", ["0812345678", "8112345678x", "81812345678", "123"])
def test_telefone_fora_do_formato(engine_app, ids, telefone):
    erro = pytest.raises(IntegrityError, match="prestador_telefone_formato")
    with erro, engine_app.begin() as con:
        criar_prestador(con, ids["u"], telefone=telefone)


@pytest.mark.parametrize("instagram", ["", "com espaço", "@arroba", "a" * 31])
def test_instagram_fora_do_formato(engine_app, ids, instagram):
    erro = pytest.raises(IntegrityError, match="prestador_instagram_formato")
    with erro, engine_app.begin() as con:
        p = criar_prestador(con, ids["u"])
        con.execute(
            text("update prestador set instagram = :i where id = :p"),
            {"i": instagram, "p": p},
        )


@pytest.mark.parametrize("nome", ["X", " Marcenaria", "a" * 81])
def test_nome_fora_do_tamanho(engine_app, ids, nome):
    erro = pytest.raises(IntegrityError, match="prestador_nome_tamanho")
    with erro, engine_app.begin() as con:
        criar_prestador(con, ids["u"], nome=nome)


def test_comentario_com_501_letras_e_recusado(engine_app, ids):
    erro = pytest.raises(IntegrityError, match="opiniao_servico_comentario_tamanho")
    with erro, engine_app.begin() as con:
        criar_prestador(con, ids["u"], comentario="a" * 501)


def test_app_nao_apaga_prestador_nem_categoria(engine_app, ids):
    with engine_app.begin() as con:
        criar_prestador(con, ids["u"])
    for tabela in ("prestador", "categoria_servico"):
        with pytest.raises(ProgrammingError) as erro, engine_app.begin() as con:
            con.execute(text(f"delete from {tabela}"))
        assert isinstance(erro.value.orig, InsufficientPrivilege)


def test_segundo_aviso_aberto_da_mesma_unidade_e_recusado(engine_app, ids):
    with engine_app.begin() as con:
        p = criar_prestador(con, ids["u"])
        con.execute(
            text("insert into aviso_servico (prestador_id, unidade_id) values (:p, :u)"),
            {"p": p, "u": ids["v"]},
        )
    with pytest.raises(IntegrityError, match="aviso_servico_aberto"), engine_app.begin() as con:
        con.execute(
            text("insert into aviso_servico (prestador_id, unidade_id) values (:p, :u)"),
            {"p": p, "u": ids["v"]},
        )


def test_categorias_iguais_sem_diferenciar_maiuscula(engine_app):
    _recusado(
        engine_app,
        "categoria_servico_nome_unico",
        "insert into categoria_servico (nome, ordem) values ('eletricista', 500)",
    )


def test_apoio_acha_a_categoria(engine_app):
    with engine_app.connect() as con:
        assert categoria_id(con, "Outros") > 0
