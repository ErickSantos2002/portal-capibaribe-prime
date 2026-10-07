"""Dois "salvar senha nova" ao mesmo tempo (revisão do épico B, item 2): com o mesmo link ou
com dois links da mesma unidade, só um passa. O outro recebe 410 `link_invalido`."""

import hashlib
import threading
import time

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.erros_api import ErroApi
from app.esquemas.recuperacao import RedefinirSenha
from app.servicos import recuperacao
from testes.conftest import COMUM

pytestmark = pytest.mark.usefixtures("predio")


def _token(engine, n: int) -> str:
    token = f"token-concorrente-{n}-" + "z" * 24
    with engine.begin() as con:
        con.execute(
            text("update unidade set email = 'm@example.com' where login = :l"), {"l": COMUM}
        )
        con.execute(
            text(
                "insert into token_recuperacao (unidade_id, token_hash)"
                " select id, :h from unidade where login = :l"
            ),
            {"h": hashlib.sha256(token.encode()).hexdigest(), "l": COMUM},
        )
    return token


def _dados(token: str, senha: str) -> RedefinirSenha:
    return RedefinirSenha(token=token, senha_nova=senha, senha_nova_repetida=senha)


def _corrida(engine_app, primeiro: str, segundo: str) -> object:
    """O primeiro redefine e segura a transação aberta; o segundo tenta no meio; o primeiro faz
    o commit. Devolve o que aconteceu com o segundo (o `Eu` ou o erro)."""
    fabrica = sessionmaker(engine_app, expire_on_commit=False)
    resultado: dict[str, object] = {}

    def segundo_aparelho() -> None:
        with fabrica() as db:
            try:
                eu, _ = recuperacao.redefinir(db, _dados(segundo, "senha do segundo"), None)
                db.commit()
                resultado["segundo"] = eu
            except ErroApi as erro:
                resultado["segundo"] = erro

    with fabrica() as db:
        recuperacao.redefinir(db, _dados(primeiro, "senha do primeiro"), None)
        fio = threading.Thread(target=segundo_aparelho)
        fio.start()
        # Dá tempo ao segundo de ler o banco antes do commit do primeiro.
        time.sleep(0.5)
        db.commit()
    fio.join(10)
    return resultado["segundo"]


def _senha_vale(engine_app, senha: str) -> bool:
    from app.modelos import Unidade
    from app.seguranca.senhas import senha_confere

    with Session(engine_app) as db:
        unidade = db.query(Unidade).filter_by(login=COMUM).one()
        return senha_confere(unidade.senha_hash, senha)


def test_o_mesmo_link_duas_vezes_ao_mesmo_tempo(engine_app):
    token = _token(engine_app, 1)
    segundo = _corrida(engine_app, token, token)
    assert isinstance(segundo, ErroApi) and segundo.codigo == "link_invalido"
    assert _senha_vale(engine_app, "senha do primeiro")


def test_dois_links_da_mesma_unidade_ao_mesmo_tempo(engine_app):
    primeiro, outro = _token(engine_app, 1), _token(engine_app, 2)
    segundo = _corrida(engine_app, primeiro, outro)
    assert isinstance(segundo, ErroApi) and segundo.codigo == "link_invalido"
    assert _senha_vale(engine_app, "senha do primeiro")
