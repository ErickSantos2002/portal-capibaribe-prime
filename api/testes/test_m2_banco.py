"""Regras de banco do M2 (migração 0005), como o usuário `app`.

- `inscricao_push`: uma por aparelho (sessão), só com dados do padrão Web Push, some quando a
  sessão é encerrada, no máximo 10 por unidade (H-05).
- `token_recuperacao`: só o hash, vale 1 hora contada pelo banco, uso único, só para unidade
  ativada com e-mail, no máximo 3 pedidos por unidade por hora e 6 por dia (H-04).
- `notificacao_envio`: um registro por aviso e canal (não manda duas vezes), situação só anda
  para a frente, só contagens (sem dado pessoal).
"""

import hashlib

import pytest
from psycopg.errors import InsufficientPrivilege
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError, ProgrammingError

from testes.apoio import criar_bloco, criar_unidade, restricao

pytestmark = pytest.mark.usefixtures("banco_limpo")

P256DH = "B" + "A" * 86  # 65 bytes em base64url, sem o "=" do fim
AUTH = "C" * 22  # 16 bytes em base64url


def _hash(n: int) -> str:
    return hashlib.sha256(f"token-{n}".encode()).hexdigest()


@pytest.fixture
def ids(engine_app) -> dict[str, int]:
    """Uma unidade ativada com e-mail (`u`), uma sem e-mail (`s`), uma sessão de cada e um
    aviso para todos."""
    with engine_app.begin() as con:
        b = criar_bloco(con, 1)
        u = criar_unidade(
            con,
            b,
            "101",
            precisa_trocar_senha=False,
            ativada_em="2026-10-01",
            responsavel_nome="Fictício",
            celular="81900000001",
            email="familia@example.com",
        )
        s = criar_unidade(
            con,
            b,
            "102",
            precisa_trocar_senha=False,
            ativada_em="2026-10-01",
            responsavel_nome="Fictício",
            celular="81900000002",
        )
        sessoes = [
            con.execute(
                text("insert into sessao (unidade_id, token_hash) values (:u, :h) returning id"),
                {"u": unidade, "h": _hash(1000 + unidade)},
            ).scalar_one()
            for unidade in (u, s)
        ]
        a = con.execute(
            text(
                "insert into aviso (publicado_por, publicado_como, para_todos)"
                " values (:u, 'comissao', true) returning id"
            ),
            {"u": u},
        ).scalar_one()
        con.execute(
            text(
                "insert into aviso_versao (aviso_id, versao, titulo, texto, criada_por)"
                " values (:a, 1, 'Título', 'Texto', :u)"
            ),
            {"a": a, "u": u},
        )
    return {"u": u, "s": s, "sessao_u": sessoes[0], "sessao_s": sessoes[1], "a": a}


def _nova_sessao(con, unidade: int, n: int) -> int:
    return con.execute(
        text("insert into sessao (unidade_id, token_hash) values (:u, :h) returning id"),
        {"u": unidade, "h": _hash(n)},
    ).scalar_one()


def _inscrever(con, sessao: int, endpoint: str = "https://fcm.googleapis.com/fcm/send/abc"):
    con.execute(
        text(
            "insert into inscricao_push (sessao_id, endpoint, chave_p256dh, chave_auth)"
            " values (:s, :e, :p, :a)"
        ),
        {"s": sessao, "e": endpoint, "p": P256DH, "a": AUTH},
    )


# --- inscricao_push --------------------------------------------------------------------------


def test_inscricao_carimba_a_data_do_banco(engine_app, ids):
    with engine_app.begin() as con:
        _inscrever(con, ids["sessao_u"])
        criada, agora = con.execute(text("select criada_em, now() from inscricao_push")).one()
    assert criada == agora


def test_uma_inscricao_por_aparelho_e_endpoint_unico(engine_app, ids):
    with engine_app.begin() as con:
        _inscrever(con, ids["sessao_u"])
    with pytest.raises(IntegrityError), engine_app.begin() as con:
        _inscrever(con, ids["sessao_u"], "https://fcm.googleapis.com/fcm/send/outro")
    with pytest.raises(IntegrityError), engine_app.begin() as con:
        _inscrever(con, ids["sessao_s"])


@pytest.mark.parametrize(
    ("endpoint", "p256dh", "auth"),
    [
        ("http://fcm.googleapis.com/fcm/send/abc", P256DH, AUTH),
        ("https://" + "a" * 2050, P256DH, AUTH),
        ("https://fcm.googleapis.com/fcm/send/abc", "curta", AUTH),
        ("https://fcm.googleapis.com/fcm/send/abc", P256DH, "C" * 21),
        ("https://fcm.googleapis.com/fcm/send/abc", P256DH, "C/" * 11),
    ],
)
def test_inscricao_so_aceita_o_formato_do_web_push(engine_app, ids, endpoint, p256dh, auth):
    with pytest.raises(IntegrityError), engine_app.begin() as con:
        con.execute(
            text(
                "insert into inscricao_push (sessao_id, endpoint, chave_p256dh, chave_auth)"
                " values (:s, :e, :p, :a)"
            ),
            {"s": ids["sessao_u"], "e": endpoint, "p": p256dh, "a": auth},
        )


def test_encerrar_a_sessao_apaga_a_inscricao(engine_app, ids):
    with engine_app.begin() as con:
        _inscrever(con, ids["sessao_u"])
        con.execute(
            text("update sessao set encerrada_em = now() where id = :s"), {"s": ids["sessao_u"]}
        )
        assert con.execute(text("select count(*) from inscricao_push")).scalar_one() == 0


def test_sessao_encerrada_nao_recebe_inscricao(engine_app, ids):
    with engine_app.begin() as con:
        con.execute(
            text("update sessao set encerrada_em = now() where id = :s"), {"s": ids["sessao_u"]}
        )
    with pytest.raises(DBAPIError) as erro, engine_app.begin() as con:
        _inscrever(con, ids["sessao_u"])
    assert restricao(erro.value) == "inscricao_push_sessao_encerrada"


def test_no_maximo_dez_aparelhos_inscritos_por_unidade(engine_app, ids):
    with engine_app.begin() as con:
        _inscrever(con, ids["sessao_u"], "https://fcm.googleapis.com/fcm/send/0")
        for n in range(1, 10):
            sessao = _nova_sessao(con, ids["u"], n)
            _inscrever(con, sessao, f"https://fcm.googleapis.com/fcm/send/{n}")
        decima_primeira = _nova_sessao(con, ids["u"], 99)
    with pytest.raises(DBAPIError) as erro, engine_app.begin() as con:
        _inscrever(con, decima_primeira, "https://fcm.googleapis.com/fcm/send/99")
    assert restricao(erro.value) == "inscricao_push_limite"
    # Outra unidade não é afetada.
    with engine_app.begin() as con:
        _inscrever(con, ids["sessao_s"], "https://fcm.googleapis.com/fcm/send/s")


def test_app_troca_e_apaga_inscricao(engine_app, ids):
    with engine_app.begin() as con:
        _inscrever(con, ids["sessao_u"])
        # Mesmo navegador entrando de novo: a inscrição passa para a sessão nova.
        nova = _nova_sessao(con, ids["u"], 7)
        con.execute(
            text("update inscricao_push set sessao_id = :n where sessao_id = :s"),
            {"n": nova, "s": ids["sessao_u"]},
        )
        con.execute(text("delete from inscricao_push where sessao_id = :n"), {"n": nova})


def test_app_nao_muda_o_endpoint_nem_a_data(engine_app, ids):
    with engine_app.begin() as con:
        _inscrever(con, ids["sessao_u"])
    for sql in (
        "update inscricao_push set endpoint = 'https://fcm.googleapis.com/x'",
        "update inscricao_push set criada_em = now() - interval '1 day'",
    ):
        with pytest.raises(ProgrammingError) as erro, engine_app.begin() as con:
            con.execute(text(sql))
        assert isinstance(erro.value.orig, InsufficientPrivilege)


# --- token_recuperacao -----------------------------------------------------------------------


def _token(con, unidade: int, n: int, **extra) -> int:
    colunas = {"unidade_id": unidade, "token_hash": _hash(n), **extra}
    nomes = ", ".join(colunas)
    valores = ", ".join(f":{c}" for c in colunas)
    return con.execute(
        text(f"insert into token_recuperacao ({nomes}) values ({valores}) returning id"),
        colunas,
    ).scalar_one()


def test_token_vale_uma_hora_contada_pelo_banco(engine_app, ids):
    with engine_app.begin() as con:
        _token(con, ids["u"], 1, expira_em="2099-01-01")
        criado, expira, agora = con.execute(
            text("select criado_em, expira_em, now() from token_recuperacao")
        ).one()
    assert criado == agora
    assert (expira - criado).total_seconds() == 3600


def test_token_so_guarda_hash(engine_app, ids):
    with pytest.raises(IntegrityError), engine_app.begin() as con:
        con.execute(
            text("insert into token_recuperacao (unidade_id, token_hash) values (:u, 'texto')"),
            {"u": ids["u"]},
        )


def test_token_so_para_unidade_ativada_com_email(engine_app, ids):
    with pytest.raises(DBAPIError) as erro, engine_app.begin() as con:
        _token(con, ids["s"], 1)
    assert restricao(erro.value) == "token_recuperacao_sem_email"


def test_tres_pedidos_por_hora(engine_app, ids):
    with engine_app.begin() as con:
        for n in range(3):
            _token(con, ids["u"], n)
    with pytest.raises(DBAPIError) as erro, engine_app.begin() as con:
        _token(con, ids["u"], 3)
    assert restricao(erro.value) == "token_recuperacao_limite_hora"


def _envelhecer(engine_superusuario, horas: int) -> None:
    """Empurra os tokens para o passado (só o superusuário pula as regras)."""
    with engine_superusuario.begin() as con:
        con.execute(text("set local session_replication_role = replica"))
        con.execute(
            text(
                "update token_recuperacao set criado_em = criado_em - make_interval(hours => :h),"
                " expira_em = expira_em - make_interval(hours => :h)"
            ),
            {"h": horas},
        )


def test_seis_pedidos_por_dia(engine_app, engine_superusuario, ids):
    with engine_app.begin() as con:
        for n in range(3):
            _token(con, ids["u"], n)
    _envelhecer(engine_superusuario, 2)
    with engine_app.begin() as con:
        for n in range(3, 6):
            _token(con, ids["u"], n)
    _envelhecer(engine_superusuario, 2)
    with pytest.raises(DBAPIError) as erro, engine_app.begin() as con:
        _token(con, ids["u"], 6)
    assert restricao(erro.value) == "token_recuperacao_limite_dia"
    # Depois de 24 horas, os antigos deixam de contar.
    _envelhecer(engine_superusuario, 21)
    with engine_app.begin() as con:
        _token(con, ids["u"], 7)


def test_usar_carimba_a_data_e_so_uma_vez(engine_app, ids):
    with engine_app.begin() as con:
        t = _token(con, ids["u"], 1)
        con.execute(
            text("update token_recuperacao set usado_em = '2000-01-01' where id = :t"), {"t": t}
        )
        usado, agora = con.execute(
            text("select usado_em, now() from token_recuperacao where id = :t"), {"t": t}
        ).one()
    assert usado == agora
    with pytest.raises(DBAPIError) as erro, engine_app.begin() as con:
        con.execute(text("update token_recuperacao set usado_em = now() where id = :t"), {"t": t})
    assert restricao(erro.value) == "token_recuperacao_usado"
    with pytest.raises(DBAPIError) as erro, engine_app.begin() as con:
        con.execute(text("update token_recuperacao set usado_em = null where id = :t"), {"t": t})
    assert restricao(erro.value) == "token_recuperacao_usado"


def test_token_vencido_nao_e_usado(engine_app, engine_superusuario, ids):
    with engine_app.begin() as con:
        t = _token(con, ids["u"], 1)
    _envelhecer(engine_superusuario, 2)
    with pytest.raises(DBAPIError) as erro, engine_app.begin() as con:
        con.execute(text("update token_recuperacao set usado_em = now() where id = :t"), {"t": t})
    assert restricao(erro.value) == "token_recuperacao_vencido"


def test_token_morre_quando_a_senha_muda_depois_do_pedido(engine_app, ids):
    with engine_app.begin() as con:
        t = _token(con, ids["u"], 1)
    with engine_app.begin() as con:
        con.execute(text("update unidade set senha_hash = 'outra' where id = :u"), {"u": ids["u"]})
    with pytest.raises(DBAPIError) as erro, engine_app.begin() as con:
        con.execute(text("update token_recuperacao set usado_em = now() where id = :t"), {"t": t})
    assert restricao(erro.value) == "token_recuperacao_vencido"


def test_usar_o_token_e_depois_trocar_a_senha_na_mesma_transacao(engine_app, ids):
    # A ordem que a rota de redefinir segue (spec do M2, seção 4.3).
    with engine_app.begin() as con:
        t = _token(con, ids["u"], 1)
    with engine_app.begin() as con:
        con.execute(text("update token_recuperacao set usado_em = now() where id = :t"), {"t": t})
        con.execute(text("update unidade set senha_hash = 'nova' where id = :u"), {"u": ids["u"]})


def test_app_nao_muda_hash_nem_validade(engine_app, ids):
    with engine_app.begin() as con:
        _token(con, ids["u"], 1)
    for sql in (
        "update token_recuperacao set expira_em = now() + interval '1 day'",
        "update token_recuperacao set token_hash = repeat('a', 64)",
        "update token_recuperacao set unidade_id = unidade_id",
    ):
        with pytest.raises(ProgrammingError) as erro, engine_app.begin() as con:
            con.execute(text(sql))
        assert isinstance(erro.value.orig, InsufficientPrivilege)


def test_app_apaga_token_velho(engine_app, ids):
    with engine_app.begin() as con:
        _token(con, ids["u"], 1)
        con.execute(text("delete from token_recuperacao"))


# --- notificacao_envio ------------------------------------------------------------------------


def _envio(con, aviso: int, canal: str) -> int:
    return con.execute(
        text("insert into notificacao_envio (aviso_id, canal) values (:a, :c) returning id"),
        {"a": aviso, "c": canal},
    ).scalar_one()


def _mudar(con, envio: int, **valores) -> None:
    sets = ", ".join(f"{c} = :{c}" for c in valores)
    con.execute(
        text(f"update notificacao_envio set {sets} where id = :id"), {**valores, "id": envio}
    )


def test_um_envio_por_aviso_e_canal(engine_app, ids):
    with engine_app.begin() as con:
        _envio(con, ids["a"], "push")
        _envio(con, ids["a"], "email")
    with pytest.raises(IntegrityError), engine_app.begin() as con:
        _envio(con, ids["a"], "push")
    with pytest.raises(IntegrityError), engine_app.begin() as con:
        _envio(con, ids["a"], "sms")


def test_envio_nasce_pendente_e_anda_para_a_frente(engine_app, ids):
    with engine_app.begin() as con:
        e = _envio(con, ids["a"], "push")
        _mudar(con, e, situacao="enviando")
        _mudar(con, e, destinos=3, entregues=1)
        _mudar(con, e, situacao="concluido", entregues=2, falhas=1, removidas=1)
        linha = con.execute(
            text(
                "select criado_em, iniciado_em, concluido_em, now() from notificacao_envio"
                " where id = :e"
            ),
            {"e": e},
        ).one()
    assert linha[0] == linha[1] == linha[2] == linha[3]
    with pytest.raises(DBAPIError) as erro, engine_app.begin() as con:
        _mudar(con, e, situacao="enviando")
    assert restricao(erro.value) == "notificacao_envio_situacao"


def test_envio_desligado_e_final(engine_app, ids):
    with engine_app.begin() as con:
        e = _envio(con, ids["a"], "email")
        _mudar(con, e, situacao="desligado")
    with pytest.raises(DBAPIError) as erro, engine_app.begin() as con:
        _mudar(con, e, situacao="enviando")
    assert restricao(erro.value) == "notificacao_envio_situacao"


def test_envio_nao_nasce_adiantado(engine_app, ids):
    with pytest.raises(DBAPIError) as erro, engine_app.begin() as con:
        con.execute(
            text(
                "insert into notificacao_envio (aviso_id, canal, situacao)"
                " values (:a, 'push', 'concluido')"
            ),
            {"a": ids["a"]},
        )
    assert restricao(erro.value) == "notificacao_envio_situacao"


@pytest.mark.parametrize(
    "valores",
    [
        {"destinos": 1, "entregues": 2},
        {"destinos": 2, "falhas": 1, "removidas": 2},
        {"destinos": -1},
        {"destinos": 2, "entregues": 1, "falhas": 1, "pulados": 1},
    ],
)
def test_contagens_coerentes(engine_app, ids, valores):
    with engine_app.begin() as con:
        e = _envio(con, ids["a"], "push")
        _mudar(con, e, situacao="enviando")
    with pytest.raises(IntegrityError), engine_app.begin() as con:
        _mudar(con, e, **valores)


def test_app_nao_apaga_envio(engine_app, ids):
    with engine_app.begin() as con:
        _envio(con, ids["a"], "push")
    with pytest.raises(ProgrammingError) as erro, engine_app.begin() as con:
        con.execute(text("delete from notificacao_envio"))
    assert isinstance(erro.value.orig, InsufficientPrivilege)
