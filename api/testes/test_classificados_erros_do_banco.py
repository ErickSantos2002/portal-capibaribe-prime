"""Todo erro que o banco dos classificados pode dar vira resposta 4xx, nunca 500 (no padrão de
`test_indicacoes_erros_do_banco.py`)."""

import re
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.servicos.classificados_banco import RESTRICOES, traduzir
from testes.apoio_classificados import criar_anuncio

pytestmark = pytest.mark.usefixtures("banco_limpo")

MIGRACAO = Path(__file__).resolve().parents[1] / "migracoes" / "versions" / "0011_classificados.py"
TABELAS = ("categoria_classificado", "anuncio", "anuncio_foto", "aviso_anuncio")


def test_toda_regra_das_triggers_tem_traducao():
    nomes = set(re.findall(r"constraint = '(\w+)'", MIGRACAO.read_text(encoding="utf-8")))
    assert {"anuncio_limite_dia", "anuncio_limite_fotos", "aviso_anuncio_fixo"} <= nomes
    assert nomes <= set(RESTRICOES), nomes - set(RESTRICOES)


def test_toda_restricao_e_indice_unico_das_tabelas_tem_traducao(engine_dono):
    with engine_dono.connect() as con:
        restricoes = set(
            con.execute(
                text(
                    "select conname from pg_constraint"
                    " where conrelid::regclass::text = any(:t) and contype not in ('n', 't')"
                ),
                {"t": list(TABELAS)},
            ).scalars()
        )
        indices = set(
            con.execute(
                text(
                    "select c.relname from pg_index i join pg_class c on c.oid = i.indexrelid"
                    " where i.indrelid::regclass::text = any(:t) and i.indisunique"
                ),
                {"t": list(TABELAS)},
            ).scalars()
        )
    assert {"aviso_anuncio_aberto", "categoria_classificado_nome_unico"} <= indices
    nomes = restricoes | indices
    assert len(nomes) > 20
    assert nomes <= set(RESTRICOES), nomes - set(RESTRICOES)


@pytest.mark.parametrize("status", {s for s, _, _ in RESTRICOES.values()})
def test_so_4xx(status):
    assert 400 <= status < 500


def _erro(engine, comando: str, **parametros) -> DBAPIError:
    with pytest.raises(DBAPIError) as erro, engine.begin() as con:
        con.execute(text(comando), parametros)
    return erro.value


def test_traduz_erros_de_verdade(engine_app, ids):
    with engine_app.begin() as con:
        a = criar_anuncio(con, ids["u"])
        con.execute(
            text(
                "update anuncio set situacao = 'encerrado', motivo_encerramento = 'vendi'"
                " where id = :a"
            ),
            {"a": a},
        )
    casos = [
        ("update anuncio set titulo = 'Outro' where id = :a", (409, "anuncio_encerrado")),
        (
            "insert into categoria_classificado (nome, ordem) values ('MÓVEIS', 1)",
            (409, "categoria_ja_existe"),
        ),
        (
            "insert into anuncio (unidade_id, categoria_id, tipo, titulo, contato)"
            " values (:u, 99999, 'troca', 'Bicicleta', '81999990001')",
            (422, "categoria_inexistente"),
        ),
    ]
    for comando, esperado in casos:
        traduzido = traduzir(_erro(engine_app, comando, a=a, u=ids["u"]))
        assert traduzido is not None, comando
        assert (traduzido.status, traduzido.codigo) == esperado, comando
        assert traduzido.mensagem


def test_erro_que_nao_e_dos_classificados_nao_e_traduzido(engine_app):
    assert traduzir(_erro(engine_app, "select 1/0")) is None
