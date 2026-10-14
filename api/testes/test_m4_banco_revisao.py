"""Regras de banco do M4 que a revisão do contrato mostrou furadas (spec do M4, seção 2.8).

Cada teste aqui falhava antes da correção. Os achados:
1. editar depois do 1º voto passava em REPEATABLE READ e SERIALIZABLE (o voto agora **grava**
   na linha da enquete, `primeiro_voto_em`);
2. o prazo usava `now()` (o início da transação): uma transação aberta antes do prazo reabria a
   enquete ou votava depois dele (agora `clock_timestamp()` em tudo);
3. o `app` mudava `unidade.bloco_id` para votar fora do destino (agora UPDATE só por coluna);
4. o voto gravado antes do prazo e confirmado depois era aceito (agora o commit também confere);
5. as travas de `voto_opcao` e `enquete_opcao` não tinham teste que as derrubasse;
6. o destino do aviso automático podia ser diferente do da enquete.

As corridas usam conexões de verdade (`psycopg`), com o nível de isolamento escolhido antes da
primeira consulta.
"""

import threading
import time

import psycopg
import pytest
from psycopg import IsolationLevel
from psycopg.errors import InsufficientPrivilege, SerializationFailure
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError

from testes.apoio import restricao
from testes.apoio_m4 import criar_enquete, opcoes_da_enquete, votar, votos_da_enquete

pytestmark = pytest.mark.usefixtures("banco_limpo")

NIVEIS = {
    "read committed": IsolationLevel.READ_COMMITTED,
    "repeatable read": IsolationLevel.REPEATABLE_READ,
    "serializable": IsolationLevel.SERIALIZABLE,
}


def _conexao(url: str, nivel: str = "read committed") -> psycopg.Connection:
    con = psycopg.connect(url)
    con.isolation_level = NIVEIS[nivel]
    return con


def _recusa(erro: psycopg.Error) -> str:
    """O motivo da recusa: o nome da regra, ou `serializacao` (o Postgres desistiu da
    transação, que a API traduz em "tente de novo")."""
    if isinstance(erro, SerializationFailure):
        return "serializacao"
    return erro.diag.constraint_name or type(erro).__name__


def _psycopg_votar(con: psycopg.Connection, e: int, u: int, *opcoes: int) -> None:
    con.execute(
        "insert into voto (enquete_id, unidade_id) values (%s, %s) on conflict (enquete_id,"
        " unidade_id) do update set votado_em = excluded.votado_em",
        (e, u),
    )
    con.execute("delete from voto_opcao where enquete_id = %s and unidade_id = %s", (e, u))
    for o in opcoes:
        con.execute("insert into voto_opcao values (%s, %s, %s)", (e, u, o))


def _estado(engine, e: int) -> tuple:
    with engine.connect() as con:
        return con.execute(
            text(
                "select pergunta, multipla_escolha, encerra_em,"
                " (select array_agg(texto order by ordem) from enquete_opcao where enquete_id = :e)"
                " from enquete where id = :e"
            ),
            {"e": e},
        ).one()


def _enquete_curta(engine, ids, segundos: float = 1.5) -> dict[str, int]:
    """Uma enquete que termina daqui a `segundos`."""
    with engine.begin() as con:
        e = criar_enquete(
            con, ids["u"], encerra=f"clock_timestamp() + interval '{segundos} seconds'"
        )
        a, b, c = opcoes_da_enquete(con, e)
    return {**ids, "e": e, "a": a, "b": b, "c": c}


# --- achado 1: editar depois do 1º voto, em qualquer isolamento ----------------------------------

EDICOES = {
    "pergunta": "update enquete set pergunta = 'Mudou depois do voto' where id = %(e)s",
    "prazo": "update enquete set encerra_em = encerra_em + interval '1 day' where id = %(e)s",
    "opcao nova": "insert into enquete_opcao (enquete_id, texto, ordem) values (%(e)s, 'D', 4)",
    "opcao apagada": "delete from enquete_opcao where id = %(c)s",
}


@pytest.mark.parametrize("edicao", EDICOES)
@pytest.mark.parametrize("nivel", NIVEIS)
def test_editar_depois_do_voto_recusado_em_qualquer_isolamento(
    engine_app, url_app, aberta, nivel, edicao
):
    antes = _estado(engine_app, aberta["e"])
    editor = _conexao(url_app, nivel)
    editor.execute("select 1 from bloco limit 1")  # a foto da transação é de antes do voto
    with engine_app.begin() as con:
        votar(con, aberta["e"], aberta["u"], aberta["a"])
    with pytest.raises(psycopg.Error) as erro:
        editor.execute(EDICOES[edicao], aberta)
        editor.commit()
    editor.close()
    assert _recusa(erro.value) in {"enquete_com_voto", "serializacao"}
    assert _estado(engine_app, aberta["e"]) == antes


@pytest.mark.parametrize("nivel", ["repeatable read", "serializable"])
def test_so_a_opcao_do_voto_em_outro_celular_recusada(engine_app, url_app, aberta, nivel):
    """Escolha única: um celular com a foto de antes do voto do outro insere só `voto_opcao`."""
    celular = _conexao(url_app, nivel)
    celular.execute("select 1 from bloco limit 1")
    with engine_app.begin() as con:
        votar(con, aberta["e"], aberta["u"], aberta["a"])
    with pytest.raises(psycopg.Error):
        celular.execute(
            "insert into voto_opcao values (%s, %s, %s)", (aberta["e"], aberta["u"], aberta["b"])
        )
        celular.commit()
    celular.close()
    assert votos_da_enquete(engine_app, aberta["e"]) == [(aberta["u"], [aberta["a"]])]


def test_primeiro_voto_fica_gravado_na_enquete(engine_app, aberta):
    with engine_app.begin() as con:
        votar(con, aberta["e"], aberta["u"], aberta["a"])
    with engine_app.begin() as con:
        votar(con, aberta["e"], aberta["u"], aberta["b"])  # trocar não mexe
        primeiro, votado = con.execute(
            text(
                "select e.primeiro_voto_em, v.votado_em from enquete e join voto v"
                " on v.enquete_id = e.id where e.id = :e"
            ),
            {"e": aberta["e"]},
        ).one()
    assert primeiro is not None and primeiro < votado


def test_primeiro_voto_nao_e_forjado(engine_app, engine_dono, aberta):
    # Sem voto, ninguém trava a enquete à toa; com voto, ninguém destrava.
    with pytest.raises(DBAPIError) as erro, engine_dono.begin() as con:
        con.execute(
            text("update enquete set primeiro_voto_em = clock_timestamp() where id = :e"), aberta
        )
    assert restricao(erro.value) == "enquete_primeiro_voto"
    with engine_app.begin() as con:
        votar(con, aberta["e"], aberta["u"], aberta["a"])
    with pytest.raises(DBAPIError) as erro, engine_dono.begin() as con:
        con.execute(text("update enquete set primeiro_voto_em = null where id = :e"), aberta)
    assert restricao(erro.value) == "enquete_com_voto"


# --- achado 2: o prazo pelo relógio, não pelo início da transação --------------------------------


def test_transacao_aberta_antes_do_prazo_nao_reabre_a_enquete(engine_app, url_app, ids):
    curta = _enquete_curta(engine_app, ids)
    comandos = (
        "update enquete set encerra_em = clock_timestamp() + interval '1 day' where id = %(e)s",
        "insert into enquete_opcao (enquete_id, texto, ordem) values (%(e)s, 'D', 4)",
        "delete from enquete_opcao where id = %(c)s",
    )
    editores = [_conexao(url_app) for _ in comandos]
    for editor in editores:
        editor.execute("select 1")  # now() fica no começo da transação, antes do prazo
    time.sleep(1.6)
    for editor, comando in zip(editores, comandos, strict=True):
        with pytest.raises(psycopg.Error) as erro:
            editor.execute(comando, curta)
            editor.commit()
        editor.close()
        assert _recusa(erro.value) == "enquete_encerrada", comando


def test_transacao_aberta_antes_do_prazo_nao_vota_depois(engine_app, url_app, ids):
    curta = _enquete_curta(engine_app, ids)
    celular = _conexao(url_app)
    celular.execute("select 1")  # now() fica no começo da transação, antes do prazo
    time.sleep(1.6)
    with pytest.raises(psycopg.Error) as erro:
        _psycopg_votar(celular, curta["e"], curta["u"], curta["a"])
    celular.close()
    assert _recusa(erro.value) == "enquete_encerrada"
    assert votos_da_enquete(engine_app, curta["e"]) == []


def test_votado_em_e_a_hora_da_gravacao(engine_app, url_app, aberta):
    celular = _conexao(url_app)
    inicio = celular.execute("select now()").fetchone()[0]
    time.sleep(0.3)
    _psycopg_votar(celular, aberta["e"], aberta["u"], aberta["a"])
    celular.commit()
    celular.close()
    with engine_app.connect() as con:
        votado = con.execute(text("select votado_em from voto")).scalar_one()
    assert (votado - inicio).total_seconds() >= 0.3


def test_rr_aberta_antes_do_voto_e_do_prazo_nao_prorroga(engine_app, url_app, ids):
    curta = _enquete_curta(engine_app, ids, segundos=1.0)
    editor = _conexao(url_app, "repeatable read")
    editor.execute("select 1 from bloco limit 1")
    with engine_app.begin() as con:
        votar(con, curta["e"], curta["u"], curta["a"])
    time.sleep(1.2)
    with pytest.raises(psycopg.Error) as erro:
        editor.execute(
            "update enquete set encerra_em = clock_timestamp() + interval '1 day' where id = %s",
            (curta["e"],),
        )
        editor.commit()
    editor.close()
    assert _recusa(erro.value) in {"enquete_com_voto", "enquete_encerrada", "serializacao"}


# --- achado 4: commit depois do prazo -------------------------------------------------------------


def test_voto_gravado_antes_do_prazo_e_confirmado_depois_recusado(engine_app, url_app, ids):
    curta = _enquete_curta(engine_app, ids, segundos=1.0)
    celular = _conexao(url_app)
    _psycopg_votar(celular, curta["e"], curta["u"], curta["a"])
    time.sleep(1.2)
    with pytest.raises(psycopg.Error) as erro:
        celular.commit()
    celular.close()
    assert _recusa(erro.value) == "enquete_encerrada"
    assert votos_da_enquete(engine_app, curta["e"]) == []


# --- achado 3: o app não muda o bloco nem o número da unidade ------------------------------------


@pytest.mark.parametrize("coluna", ["bloco_id", "numero", "andar", "login", "senha_trocada_em"])
def test_app_nao_muda_onde_a_unidade_fica(engine_app, ids, coluna):
    with pytest.raises(ProgrammingError) as erro, engine_app.begin() as con:
        con.execute(text(f"update unidade set {coluna} = {coluna} where id = :v"), ids)
    assert isinstance(erro.value.orig, InsufficientPrivilege)


def test_voto_fora_do_destino_trocando_o_bloco_da_unidade(engine_app, ids):
    with engine_app.begin() as con:
        e = criar_enquete(con, ids["u"], blocos=(ids["b1"],))
        [a, *_] = opcoes_da_enquete(con, e)
    with pytest.raises(ProgrammingError), engine_app.begin() as con:
        con.execute(
            text("update unidade set bloco_id = :b, numero = '177' where id = :v"),
            {"b": ids["b1"], "v": ids["v"]},
        )
        votar(con, e, ids["v"], a)
    assert votos_da_enquete(engine_app, e) == []


def test_app_nao_renumera_o_bloco(engine_app, ids):
    with pytest.raises(ProgrammingError) as erro, engine_app.begin() as con:
        con.execute(text("update bloco set numero = 7 where id = :b2"), ids)
    assert isinstance(erro.value.orig, InsufficientPrivilege)
    with engine_app.begin() as con:
        con.execute(text("update bloco set nome = 'Bloco Dois', ativo = true where id = :b2"), ids)


def test_dono_ainda_corrige_a_unidade(engine_dono, ids):
    # H-10 (M5): a correção de blocos e unidades é do dono, fora da API.
    with engine_dono.begin() as con:
        login = con.execute(
            text("update unidade set numero = '108' where id = :u2 returning login"), ids
        ).scalar_one()
    assert login == "1108"


@pytest.mark.parametrize(
    "coluna",
    [
        "senha_hash",
        "precisa_trocar_senha",
        "ativada_em",
        "responsavel_nome",
        "celular",
        "email",
        "receber_avisos_email",
        "ativa",
    ],
)
def test_app_continua_mudando_o_que_a_api_muda(engine_app, ids, coluna):
    with engine_app.begin() as con:
        con.execute(text(f"update unidade set {coluna} = {coluna} where id = :u"), ids)


# --- achado 5: as travas que os testes não derrubavam ---------------------------------------------


def test_troca_que_insere_antes_de_apagar_espera_a_outra(engine_app, url_app, votada):
    """Sem o `on conflict` na frente: um celular troca o voto (apaga e insere, sem confirmar);
    o outro insere a opção dele e depois apaga as outras. A trava da linha do voto em
    `voto_opcao` faz o segundo esperar o primeiro e apagar o que ele gravou: um voto, inteiro."""
    e, u = votada["e"], votada["u"]
    primeiro = _conexao(url_app)
    primeiro.execute("delete from voto_opcao where enquete_id = %s and unidade_id = %s", (e, u))
    primeiro.execute("insert into voto_opcao values (%s, %s, %s)", (e, u, votada["c"]))
    erros: list[BaseException] = []

    def segundo() -> None:
        try:
            with _conexao(url_app) as con:
                con.execute("insert into voto_opcao values (%s, %s, %s)", (e, u, votada["b"]))
                con.execute(
                    "delete from voto_opcao where enquete_id = %s and unidade_id = %s"
                    " and opcao_id <> %s",
                    (e, u, votada["b"]),
                )
        except BaseException as erro:  # noqa: BLE001
            erros.append(erro)

    fio = threading.Thread(target=segundo)
    fio.start()
    time.sleep(0.4)
    primeiro.commit()
    primeiro.close()
    fio.join()
    assert erros == []
    assert votos_da_enquete(engine_app, e) == [(u, [votada["b"]])]


@pytest.mark.parametrize("edicao", ["opcao nova", "opcao apagada"])
def test_mexer_na_opcao_com_voto_em_andamento_espera_e_e_recusado(
    engine_app, url_app, aberta, edicao
):
    celular = _conexao(url_app)
    _psycopg_votar(celular, aberta["e"], aberta["u"], aberta["a"])  # sem confirmar
    resultado: list[str] = []

    def editar() -> None:
        try:
            with _conexao(url_app) as con:
                con.execute(EDICOES[edicao], aberta)
            resultado.append("passou")
        except psycopg.Error as erro:
            resultado.append(_recusa(erro))

    fio = threading.Thread(target=editar)
    fio.start()
    time.sleep(0.4)
    assert resultado == []  # esperando o voto
    celular.commit()
    celular.close()
    fio.join()
    assert resultado == ["enquete_com_voto"]
    with engine_app.connect() as con:
        assert (
            con.execute(
                text("select count(*) from enquete_opcao where enquete_id = :e"), aberta
            ).scalar_one()
            == 3
        )


# --- achado 6: o destino do aviso automático é o da enquete --------------------------------------


@pytest.mark.parametrize(
    ("blocos", "aviso_blocos"),
    [(("b1",), ()), ((), ("b1",)), (("b1",), ("b2",)), (("b1",), ("b1", "b2"))],
)
def test_aviso_com_outro_destino_recusado(engine_app, ids, blocos, aviso_blocos):
    with pytest.raises(DBAPIError) as erro, engine_app.begin() as con:
        criar_enquete(
            con,
            ids["u"],
            blocos=tuple(ids[b] for b in blocos),
            aviso_blocos=tuple(ids[b] for b in aviso_blocos),
            para_todos=not blocos,
        )
    assert restricao(erro.value) == "enquete_destino_do_aviso"


def test_aviso_da_enquete_nao_ganha_bloco_depois(engine_app, ids):
    with engine_app.begin() as con:
        e = criar_enquete(con, ids["u"], blocos=(ids["b1"],))
        aviso = con.execute(text("select aviso_id from enquete where id = :e"), {"e": e}).scalar()
    with pytest.raises(DBAPIError) as erro, engine_app.begin() as con:
        con.execute(
            text("insert into aviso_bloco (aviso_id, bloco_id) values (:a, :b)"),
            {"a": aviso, "b": ids["b2"]},
        )
    assert restricao(erro.value) == "enquete_destino_do_aviso"
