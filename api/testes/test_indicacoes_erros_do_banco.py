"""Todo erro que o banco das indicações pode dar vira resposta 4xx, nunca 500 (no padrão de
`test_m4_erros_do_banco.py`). `app.servicos.indicacoes_banco.traduzir` é o tradutor."""

import re
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.servicos.indicacoes_banco import RESTRICOES, traduzir
from testes.apoio_indicacoes import criar_prestador

pytestmark = pytest.mark.usefixtures("banco_limpo")

MIGRACAO = Path(__file__).resolve().parents[1] / "migracoes" / "versions" / "0010_indicacoes.py"
TABELAS = ("categoria_servico", "prestador", "opiniao_servico", "aviso_servico")


def test_toda_regra_das_triggers_tem_traducao():
    nomes = set(re.findall(r"constraint = '(\w+)'", MIGRACAO.read_text(encoding="utf-8")))
    assert {"prestador_limite_dia", "opiniao_escondida", "aviso_servico_fixo"} <= nomes
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
    assert {"aviso_servico_aberto", "categoria_servico_nome_unico"} <= indices
    nomes = restricoes | indices
    assert len(nomes) > 15
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
        p = criar_prestador(con, ids["u"])
    casos = [
        (
            "insert into opiniao_servico (prestador_id, unidade_id, recomenda)"
            " values (:p, :u, true)",
            (409, "tente_de_novo"),
        ),
        (
            "insert into categoria_servico (nome, ordem) values ('ELETRICISTA', 1)",
            (409, "categoria_ja_existe"),
        ),
        (
            "insert into prestador (categoria_id, nome, nome_busca, telefone, criado_por)"
            " values (1, 'Outro', 'outro', '81999990001', :u)",
            (409, "prestador_ja_existe"),
        ),
        (
            "insert into opiniao_servico (prestador_id, unidade_id, recomenda)"
            " values (99999, :u, true)",
            (409, "tente_de_novo"),
        ),
    ]
    for comando, esperado in casos:
        traduzido = traduzir(_erro(engine_app, comando, p=p, u=ids["u"]))
        assert traduzido is not None, comando
        assert (traduzido.status, traduzido.codigo) == esperado, comando
        assert traduzido.mensagem


def test_erro_que_nao_e_das_indicacoes_nao_e_traduzido(engine_app):
    assert traduzir(_erro(engine_app, "select 1/0")) is None
