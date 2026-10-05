"""Sessão por cookie (ADR-0005; spec do M1, seção 3.1)."""

import hashlib
from datetime import timedelta

import pytest
from fastapi import Response
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.modelos import Sessao
from app.seguranca import sessoes
from testes.conftest import COMUM


def _token(engine_app, unidade_id: int) -> str:
    with Session(engine_app) as db:
        token = sessoes.criar_sessao(db, unidade_id, "Mozilla/5.0 (iPhone) Version/17 Safari/604")
        db.commit()
    return token


def test_banco_guarda_so_o_hash_do_token(engine_app, predio):
    token = _token(engine_app, predio[COMUM])
    with Session(engine_app) as db:
        linha = db.scalars(select(Sessao)).one()
    assert len(token) >= 43  # 32 bytes em base64 de URL
    assert linha.token_hash == hashlib.sha256(token.encode()).hexdigest()
    assert token not in linha.token_hash
    assert linha.aparelho == "iPhone · Safari"


def test_busca_a_sessao_pelo_token(engine_app, predio):
    token = _token(engine_app, predio[COMUM])
    with Session(engine_app) as db:
        achada = sessoes.buscar_sessao(db, token)
        assert achada is not None and achada.unidade_id == predio[COMUM]
        assert sessoes.buscar_sessao(db, token + "x") is None
        assert sessoes.buscar_sessao(db, "") is None


def test_sessao_encerrada_nao_vale(engine_app, predio):
    token = _token(engine_app, predio[COMUM])
    with Session(engine_app) as db:
        sessao = sessoes.buscar_sessao(db, token)
        assert sessao is not None
        sessoes.encerrar_sessao(db, sessao.id)
        db.commit()
        assert sessoes.buscar_sessao(db, token) is None


def test_encerrar_todas_menos_uma(engine_app, predio):
    tokens = [_token(engine_app, predio[COMUM]) for _ in range(3)]
    with Session(engine_app) as db:
        fica = sessoes.buscar_sessao(db, tokens[0])
        assert fica is not None
        assert sessoes.encerrar_todas(db, predio[COMUM], exceto=fica.id) == 2
        db.commit()
        assert [sessoes.buscar_sessao(db, t) is not None for t in tokens] == [True, False, False]


def test_sessao_vence_depois_de_180_dias_sem_uso(engine_app, predio):
    token = _token(engine_app, predio[COMUM])
    with Session(engine_app) as db:
        db.execute(update(Sessao).values(ultimo_uso_em=func.now() - timedelta(days=179)))
        db.commit()
        assert sessoes.buscar_sessao(db, token) is not None
        db.execute(update(Sessao).values(ultimo_uso_em=func.now() - timedelta(days=181)))
        db.commit()
        assert sessoes.buscar_sessao(db, token) is None


def test_renova_no_maximo_uma_vez_por_hora(engine_app, predio):
    token = _token(engine_app, predio[COMUM])
    with Session(engine_app) as db:
        sessao = sessoes.buscar_sessao(db, token)
        assert sessao is not None
        assert sessoes.renovar(db, sessao) is False  # acabou de nascer
        db.execute(update(Sessao).values(ultimo_uso_em=func.now() - timedelta(hours=2)))
        db.commit()
        sessao = sessoes.buscar_sessao(db, token)
        assert sessao is not None
        assert sessoes.renovar(db, sessao) is True
        db.commit()
        uso = db.scalars(select(Sessao.ultimo_uso_em)).one()
        agora = db.scalar(select(func.now()))
    assert agora - uso < timedelta(minutes=1)


def test_cookie_com_os_atributos_da_adr():
    resposta = Response()
    sessoes.gravar_cookie(resposta, "abc")
    cookie = resposta.headers["set-cookie"]
    assert cookie.startswith("__Host-sessao=abc;")
    for atributo in ("HttpOnly", "Secure", "SameSite=lax", "Path=/", "Max-Age=15552000"):
        assert atributo in cookie
    assert "Domain" not in cookie


def test_apagar_cookie():
    resposta = Response()
    sessoes.apagar_cookie(resposta)
    cookie = resposta.headers["set-cookie"]
    assert cookie.startswith('__Host-sessao="";') or cookie.startswith("__Host-sessao=;")
    assert "Max-Age=0" in cookie and "Secure" in cookie and "Path=/" in cookie


@pytest.mark.parametrize(
    ("agente", "esperado"),
    [
        ("Mozilla/5.0 (Linux; Android 14; SM-A145M) AppleWebKit Chrome/130 Mobile Safari", "Android · Chrome"),  # noqa: E501
        ("Mozilla/5.0 (Linux; Android 13) SamsungBrowser/25.0 Chrome/121 Mobile Safari", "Android · Samsung Internet"),  # noqa: E501
        ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) Version/17.5 Mobile Safari/604.1", "iPhone · Safari"),  # noqa: E501
        ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) CriOS/130 Mobile Safari", "iPhone · Chrome"),  # noqa: E501
        ("Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) Version/17.5 Safari/604.1", "iPad · Safari"),  # noqa: E501
        ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130 Safari/537.36 Edg/130", "Windows · Edge"),  # noqa: E501
        ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) Version/17.5 Safari/605.1.15", "Mac · Safari"),  # noqa: E501
        ("Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0", "Linux · Firefox"),  # noqa: E501
        ("curl/8.0", "Aparelho desconhecido"),
        ("", "Aparelho desconhecido"),
        (None, "Aparelho desconhecido"),
    ],
)  # fmt: skip
def test_descrever_aparelho(agente, esperado):
    assert sessoes.descrever_aparelho(agente) == esperado
