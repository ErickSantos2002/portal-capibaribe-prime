"""Todo erro que o banco das enquetes pode dar vira resposta 4xx, nunca 500 (revisão do contrato
do M4, achado 6). `app.servicos.enquetes_banco.traduzir` é comum aos dois épicos."""

import re
from pathlib import Path

import psycopg
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.servicos.enquetes_banco import RESTRICOES, traduzir
from testes.apoio_m4 import votar

pytestmark = pytest.mark.usefixtures("banco_limpo")

# As migrações das enquetes: a 0008 e as que mexem nas regras dela (a 0009, voto de unidade
# ativa; ajustes do M4, ponto 4).
VERSOES = Path(__file__).resolve().parents[1] / "migracoes" / "versions"
MIGRACOES = (VERSOES / "0008_enquetes.py", VERSOES / "0009_voto_de_unidade_ativa.py")
TABELAS = ("enquete", "enquete_opcao", "enquete_bloco", "voto", "voto_opcao")


def test_toda_regra_das_triggers_tem_traducao():
    nomes = {
        nome
        for migracao in MIGRACOES
        for nome in re.findall(r"constraint = '(\w+)'", migracao.read_text(encoding="utf-8"))
    }
    assert "voto_de_unidade_inativa" in nomes
    assert nomes, "a leitura da migração não achou nada"
    assert nomes <= set(RESTRICOES), nomes - set(RESTRICOES)


def test_toda_restricao_das_tabelas_tem_traducao(engine_dono):
    with engine_dono.connect() as con:
        nomes = set(
            con.execute(
                text(
                    "select conname from pg_constraint"
                    # `t` são as triggers de restrição: as regras delas têm o próprio nome
                    # (conferido no teste acima).
                    " where conrelid::regclass::text = any(:t) and contype not in ('n', 't')"
                ),
                {"t": list(TABELAS)},
            ).scalars()
        )
    assert len(nomes) > 20
    assert nomes <= set(RESTRICOES), nomes - set(RESTRICOES)


@pytest.mark.parametrize("status", {s for s, _, _ in RESTRICOES.values()})
def test_so_4xx(status):
    assert 400 <= status < 500


def _erro(engine, comando: str, **parametros) -> DBAPIError:
    with pytest.raises(DBAPIError) as erro, engine.begin() as con:
        con.execute(text(comando), parametros)
    return erro.value


def test_traduz_erros_de_verdade(engine_app, votada):
    casos = [
        (
            "update enquete set pergunta = 'Outra' where id = :e",
            (409, "enquete_com_voto"),
        ),
        (
            "insert into voto (enquete_id, unidade_id) values (:e, :u)",
            (409, "voto_mudou_agora"),
        ),
        (
            "insert into voto_opcao values (:e, :u, :b)",
            (409, "voto_mudou_agora"),
        ),
        (
            "insert into voto (enquete_id, unidade_id) values (9999, :u)",
            (404, "enquete_nao_encontrada"),
        ),
    ]
    for comando, esperado in casos:
        traduzido = traduzir(_erro(engine_app, comando, **votada))
        assert traduzido is not None, comando
        assert (traduzido.status, traduzido.codigo) == esperado, comando
        assert traduzido.mensagem


def test_encerramento_vira_422(engine_app, aberta):
    erro = _erro(
        engine_app,
        "update enquete set encerra_em = now() + interval '2 years' where id = :e",
        **aberta,
    )
    traduzido = traduzir(erro)
    assert traduzido is not None
    assert (traduzido.status, traduzido.codigo) == (422, "encerramento_invalido")


def test_serializacao_vira_409_tente_de_novo(engine_app, url_app, aberta):
    editor = psycopg.connect(url_app)
    editor.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
    editor.execute("select 1 from bloco limit 1")
    with engine_app.begin() as con:
        votar(con, aberta["e"], aberta["u"], aberta["a"])
    with pytest.raises(psycopg.Error) as erro:
        editor.execute("update enquete set pergunta = 'X' where id = %s", (aberta["e"],))
    editor.close()
    traduzido = traduzir(DBAPIError("update", {}, erro.value))
    assert traduzido is not None
    assert (traduzido.status, traduzido.codigo) == (409, "tente_de_novo")


def test_erro_que_nao_e_do_banco_das_enquetes_nao_e_traduzido(engine_app):
    assert traduzir(_erro(engine_app, "select 1/0")) is None
