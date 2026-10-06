"""Épico A do M2 · rotas de notificação no aparelho (H-05; spec `m2-push.md`, seção 2.1).

Sessão, CSRF e validação do corpo já são conferidos em `test_m2_rotas.py`; aqui fica o que as
rotas fazem.
"""

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app import configuracao
from app.comandos import gerar_chaves_vapid
from app.modelos import InscricaoPush, Sessao, Unidade
from app.seguranca.sessoes import NOME_COOKIE, hash_do_token
from testes.conftest import ADMIN, COMUM

pytestmark = pytest.mark.usefixtures("predio")

P256DH = "B" + "A" * 86
AUTH = "C" * 22
CAMINHO = "/api/notificacoes/este-aparelho"


def inscricao(n: int = 1) -> dict[str, str]:
    return {"endpoint": f"https://fcm.googleapis.com/fcm/send/{n}", "p256dh": P256DH, "auth": AUTH}


@pytest.fixture
def vapid(monkeypatch) -> str:
    """Push ligado, com um par novo (nunca uma chave de verdade). Devolve a chave pública."""
    par = gerar_chaves_vapid.gerar()
    monkeypatch.setenv("PORTAL_VAPID_PRIVADA", par.privada)
    monkeypatch.setenv("PORTAL_VAPID_CONTATO", "mailto:portal@example.com")
    configuracao.limpar_cache()
    yield par.publica
    configuracao.limpar_cache()


@pytest.fixture
def sem_vapid(monkeypatch):
    monkeypatch.delenv("PORTAL_VAPID_PRIVADA", raising=False)
    monkeypatch.delenv("PORTAL_VAPID_CONTATO", raising=False)
    configuracao.limpar_cache()
    yield
    configuracao.limpar_cache()


def sessao_de(cliente, engine) -> int:
    token = cliente.cookies.get(NOME_COOKIE)
    with Session(engine) as db:
        return db.scalars(select(Sessao.id).where(Sessao.token_hash == hash_do_token(token))).one()


def inscricoes(engine) -> dict[int, str]:
    with Session(engine) as db:
        return dict(db.execute(select(InscricaoPush.sessao_id, InscricaoPush.endpoint)).all())


# --- GET /api/notificacoes ---------------------------------------------------------------------


def test_estado_sem_vapid_esconde_a_oferta(logar, sem_vapid):
    resposta = logar(COMUM).get("/api/notificacoes")
    assert resposta.status_code == 200
    assert resposta.json() == {"disponivel": False, "chave_publica": None, "este_aparelho": False}


def test_estado_com_vapid_entrega_a_chave_publica(logar, vapid):
    resposta = logar(COMUM).get("/api/notificacoes")
    assert resposta.json() == {"disponivel": True, "chave_publica": vapid, "este_aparelho": False}


def test_estado_diz_se_este_aparelho_esta_inscrito(logar, vapid):
    celular = logar(COMUM)
    outro = logar(COMUM)
    assert celular.put(CAMINHO, json=inscricao()).status_code == 204
    assert celular.get("/api/notificacoes").json()["este_aparelho"] is True
    # O outro celular da casa é outra sessão: ainda não ativou.
    assert outro.get("/api/notificacoes").json()["este_aparelho"] is False


# --- PUT /api/notificacoes/este-aparelho -------------------------------------------------------


def test_inscrever_sem_vapid_responde_503(logar, sem_vapid, engine_app):
    resposta = logar(COMUM).put(CAMINHO, json=inscricao())
    assert resposta.status_code == 503
    assert resposta.json() == {
        "codigo": "notificacoes_desligadas",
        "mensagem": "As notificações ainda não estão ligadas no Portal.",
    }
    assert inscricoes(engine_app) == {}


def test_inscrever_guarda_na_sessao_deste_aparelho(logar, vapid, engine_app):
    celular = logar(COMUM)
    assert celular.put(CAMINHO, json=inscricao(1)).status_code == 204
    assert inscricoes(engine_app) == {
        sessao_de(celular, engine_app): "https://fcm.googleapis.com/fcm/send/1"
    }


def test_inscrever_de_novo_com_outro_endpoint_troca(logar, vapid, engine_app):
    celular = logar(COMUM)
    celular.put(CAMINHO, json=inscricao(1))
    assert celular.put(CAMINHO, json=inscricao(2)).status_code == 204
    assert inscricoes(engine_app) == {
        sessao_de(celular, engine_app): "https://fcm.googleapis.com/fcm/send/2"
    }


def test_inscrever_de_novo_igual_nao_duplica(logar, vapid, engine_app):
    celular = logar(COMUM)
    celular.put(CAMINHO, json=inscricao(1))
    assert celular.put(CAMINHO, json={**inscricao(1), "auth": "D" * 22}).status_code == 204
    with Session(engine_app) as db:
        assert db.scalars(select(InscricaoPush.chave_auth)).all() == ["D" * 22]


def test_endpoint_de_outra_sessao_passa_para_esta(logar, vapid, engine_app):
    # O mesmo navegador entrou de novo (ou outra unidade usou este navegador): o endpoint é
    # do navegador, então segue a sessão nova.
    antes = logar(COMUM)
    antes.put(CAMINHO, json=inscricao(1))
    depois = logar(ADMIN)
    assert depois.put(CAMINHO, json=inscricao(1)).status_code == 204
    assert inscricoes(engine_app) == {
        sessao_de(depois, engine_app): "https://fcm.googleapis.com/fcm/send/1"
    }


def test_decimo_primeiro_aparelho_recebe_409(logar, vapid, engine_app):
    for n in range(10):
        assert logar(COMUM).put(CAMINHO, json=inscricao(n)).status_code == 204
    resposta = logar(COMUM).put(CAMINHO, json=inscricao(99))
    assert resposta.status_code == 409
    assert resposta.json() == {
        "codigo": "limite_de_aparelhos",
        "mensagem": "Este apartamento já tem 10 aparelhos com notificação. "
        "Desative em algum deles.",
    }
    assert len(inscricoes(engine_app)) == 10


def test_sessao_encerrada_no_meio_vira_sem_sessao(logar, vapid, engine_app, monkeypatch):
    # Corrida: a sessão é encerrada (outro aparelho trocou a senha) entre a conferência da sessão
    # e o INSERT. O banco recusa (`inscricao_push_sessao_encerrada`) e a tela leva para entrar.
    from app.servicos import push

    celular = logar(COMUM)
    sessao_id = sessao_de(celular, engine_app)
    original = push.inscrever

    def encerrar_antes(db, sessao, dados):
        with engine_app.begin() as con:
            con.execute(
                text("update sessao set encerrada_em = now() where id = :s"), {"s": sessao_id}
            )
        return original(db, sessao, dados)

    monkeypatch.setattr(push, "inscrever", encerrar_antes)
    resposta = celular.put(CAMINHO, json=inscricao())
    assert (resposta.status_code, resposta.json()["codigo"]) == (401, "sem_sessao")
    assert inscricoes(engine_app) == {}


# --- DELETE /api/notificacoes/este-aparelho ----------------------------------------------------


def test_remover_apaga_so_a_deste_aparelho(logar, vapid, engine_app):
    celular, outro = logar(COMUM), logar(COMUM)
    celular.put(CAMINHO, json=inscricao(1))
    outro.put(CAMINHO, json=inscricao(2))
    assert celular.delete(CAMINHO).status_code == 204
    assert inscricoes(engine_app) == {
        sessao_de(outro, engine_app): "https://fcm.googleapis.com/fcm/send/2"
    }


def test_remover_sem_inscricao_e_idempotente(logar, sem_vapid):
    # Funciona mesmo com o push desligado: desativar nunca pode falhar.
    celular = logar(COMUM)
    assert celular.delete(CAMINHO).status_code == 204
    assert celular.delete(CAMINHO).status_code == 204


def test_sessao_que_sai_leva_a_inscricao(logar, vapid, engine_app):
    celular = logar(COMUM)
    celular.put(CAMINHO, json=inscricao())
    assert celular.post("/api/acesso/sair").status_code == 204
    assert inscricoes(engine_app) == {}
    with Session(engine_app) as db:
        assert db.scalar(select(Unidade.id).where(Unidade.login == COMUM))
