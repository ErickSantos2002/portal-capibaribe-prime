"""Épico A do M2 · o canal push (H-13; spec `m2-push.md`, seção 2.2).

`pywebpush.webpush` é trocado por um falso: **nenhum teste fala com um serviço de push de
verdade**. O falso imita o de verdade: devolve a resposta até 202 e levanta
`WebPushException` com a resposta acima disso.
"""

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from itertools import count

import pytest
import requests
from py_vapid import Vapid
from pywebpush import WebPushException
from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from app import configuracao
from app.comandos import gerar_chaves_vapid
from app.modelos import InscricaoPush, Sessao, Unidade
from app.servicos import notificacoes, push
from app.servicos.notificacoes import AvisoParaNotificar, Resultado
from testes.test_avisos_apoio import ADMIN, COMISSAO, COMUM, ativar, publicar

pytestmark = pytest.mark.usefixtures("predio")

P256DH = "B" + "A" * 86
AUTH = "C" * 22
_numero = count(1)


@dataclass
class Resposta:
    status_code: int
    text: str = ""
    reason: str = ""


@dataclass
class PushFalso:
    """`webpush` falso. O status sai do fim do endpoint: `.../410-3` responde 410; `.../rede-4`
    levanta erro de conexão; o resto, 201."""

    chamadas: list[dict] = field(default_factory=list)
    trava: threading.Lock = field(default_factory=threading.Lock)
    atraso: float = 0.0

    def __call__(
        self,
        subscription_info,
        data=None,
        vapid_private_key=None,
        vapid_claims=None,
        ttl=0,
        headers=None,
        timeout=None,
        **resto,
    ):
        # Como o de verdade: grava o `aud` no dicionário recebido.
        if vapid_claims is not None and not vapid_claims.get("aud"):
            endpoint = subscription_info["endpoint"]
            vapid_claims["aud"] = endpoint[: endpoint.index("/", len("https://"))]
        with self.trava:
            self.chamadas.append(
                {
                    "subscription_info": subscription_info,
                    "data": data,
                    "vapid_private_key": vapid_private_key,
                    "vapid_claims": dict(vapid_claims or {}),
                    "ttl": ttl,
                    "headers": dict(headers or {}),
                    "timeout": timeout,
                    **resto,
                }
            )
        if self.atraso:
            time.sleep(self.atraso)
        final = subscription_info["endpoint"].rsplit("/", 1)[-1]
        if final.startswith("rede"):
            raise requests.ConnectionError("sem rede")
        status = int(final.split("-")[0]) if final[:3].isdigit() else 201
        if status > 202:
            raise WebPushException(f"Push failed: {status}", response=Resposta(status))
        return Resposta(status)


@pytest.fixture
def falso(monkeypatch) -> PushFalso:
    falso = PushFalso()
    monkeypatch.setattr(push.pywebpush, "webpush", falso)
    return falso


@pytest.fixture
def vapid(monkeypatch) -> str:
    par = gerar_chaves_vapid.gerar()
    monkeypatch.setenv("PORTAL_VAPID_PRIVADA", par.privada)
    monkeypatch.setenv("PORTAL_VAPID_CONTATO", "mailto:portal@example.com")
    configuracao.limpar_cache()
    yield par.privada
    configuracao.limpar_cache()


@pytest.fixture
def fabrica(engine_app) -> sessionmaker[Session]:
    return sessionmaker(engine_app, expire_on_commit=False)


def inscrito(engine, login: str, endpoint: str) -> int:
    """Uma sessão nova da unidade com inscrição neste endpoint. Devolve o id da sessão."""
    with Session(engine) as db:
        unidade_id = db.scalar(select(Unidade.id).where(Unidade.login == login))
        sessao = Sessao(
            unidade_id=unidade_id, token_hash=f"{next(_numero):064x}", aparelho="Android · Chrome"
        )
        db.add(sessao)
        db.flush()
        db.add(
            InscricaoPush(
                sessao_id=sessao.id, endpoint=endpoint, chave_p256dh=P256DH, chave_auth=AUTH
            )
        )
        db.commit()
        return sessao.id


def aviso(engine, categoria: str = "geral", titulo: str = "Vistoria da obra") -> AvisoParaNotificar:
    with Session(engine) as db:
        comissao = db.scalar(select(Unidade.id).where(Unidade.login == COMISSAO))
    return AvisoParaNotificar(
        aviso_id=42,
        titulo=titulo,
        texto="Texto longo que não vai na notificação.",
        categoria=categoria,
        publicado_por=comissao,
        para_todos=True,
        blocos=(),
    )


def endpoints(engine) -> set[str]:
    with Session(engine) as db:
        return set(db.scalars(select(InscricaoPush.endpoint)))


def enviar(fabrica, aviso_: AvisoParaNotificar, resultado: Resultado | None = None) -> Resultado:
    resultado = resultado or Resultado()
    with fabrica() as db:
        push.ENVIADOR.enviar(db, aviso_, resultado)
        db.commit()
    return resultado


FCM = "https://fcm.googleapis.com/fcm/send"
APPLE = "https://web.push.apple.com"


# --- ligado ------------------------------------------------------------------------------------


def test_ligado_segue_a_configuracao(monkeypatch, vapid):
    assert push.ENVIADOR.ligado() is True
    monkeypatch.delenv("PORTAL_VAPID_PRIVADA")
    configuracao.limpar_cache()
    assert push.ENVIADOR.ligado() is False


# --- o que vai em cada POST --------------------------------------------------------------------


def test_corpo_so_com_titulo_categoria_e_endereco_do_aviso(engine_app, fabrica, falso, vapid):
    inscrito(engine_app, COMUM, f"{FCM}/a")
    enviar(fabrica, aviso(engine_app))
    (chamada,) = falso.chamadas
    assert json.loads(chamada["data"]) == {
        "aviso_id": 42,
        "titulo": "Vistoria da obra",
        "categoria": "geral",
        "url": "/avisos/42",
    }
    # Sem dado pessoal e sem o texto do aviso (ficaria na tela bloqueada).
    assert "Texto longo" not in chamada["data"]
    assert chamada["subscription_info"] == {
        "endpoint": f"{FCM}/a",
        "keys": {"p256dh": P256DH, "auth": AUTH},
    }


def test_ttl_urgencia_topico_e_tempo_limite(engine_app, fabrica, falso, vapid):
    inscrito(engine_app, COMUM, f"{FCM}/a")
    enviar(fabrica, aviso(engine_app))
    enviar(fabrica, aviso(engine_app, categoria="urgente"))
    normal, urgente = falso.chamadas
    assert normal["ttl"] == 3 * 24 * 60 * 60
    assert normal["timeout"] == 10
    assert normal["headers"] == {"Urgency": "normal", "Topic": "aviso-42"}
    assert urgente["headers"] == {"Urgency": "high", "Topic": "aviso-42"}


def test_vapid_assina_com_o_contato_e_o_aud_de_cada_servico(engine_app, fabrica, falso, vapid):
    # O `webpush` grava o `aud` no dicionário que recebe: reaproveitar o mesmo dicionário
    # assinaria o Apple com o `aud` do Google, e o Apple recusaria.
    inscrito(engine_app, COMUM, f"{FCM}/a")
    inscrito(engine_app, ADMIN, f"{APPLE}/b")
    enviar(fabrica, aviso(engine_app))
    auds = {c["subscription_info"]["endpoint"]: c["vapid_claims"]["aud"] for c in falso.chamadas}
    assert auds == {f"{FCM}/a": "https://fcm.googleapis.com", f"{APPLE}/b": APPLE}
    for chamada in falso.chamadas:
        assert chamada["vapid_claims"]["sub"] == "mailto:portal@example.com"
        chave = chamada["vapid_private_key"]
        assert isinstance(chave, Vapid)
        assert chave.private_key.private_numbers().private_value == (
            Vapid.from_string(vapid).private_key.private_numbers().private_value
        )


# --- o que conta e o que apaga ----------------------------------------------------------------


def test_contagens_e_inscricoes_mortas_apagadas(engine_app, fabrica, falso, vapid):
    inscrito(engine_app, COMUM, f"{FCM}/ok-1")
    inscrito(engine_app, COMUM, f"{FCM}/410-2")
    inscrito(engine_app, ADMIN, f"{APPLE}/404-3")
    inscrito(engine_app, ADMIN, f"{FCM}/500-4")
    inscrito(engine_app, ADMIN, f"{FCM}/rede-5")
    resultado = enviar(fabrica, aviso(engine_app))
    assert resultado.contagens() == {
        "destinos": 5,
        "entregues": 1,
        "falhas": 4,
        "removidas": 2,
        "pulados": 0,
        "reservados": 0,
    }
    # 404 e 410: o serviço disse que a inscrição não existe mais. Erro passageiro fica.
    assert endpoints(engine_app) == {f"{FCM}/ok-1", f"{FCM}/500-4", f"{FCM}/rede-5"}


def test_inscricao_que_trocou_de_endpoint_no_meio_nao_e_apagada(
    engine_app, fabrica, falso, vapid, monkeypatch
):
    # O aparelho reativou (endpoint novo) enquanto o envio para o antigo voltava 410: apagar
    # pela sessão sozinha levaria a inscrição nova junto.
    sessao = inscrito(engine_app, COMUM, f"{FCM}/410-velho")
    original = falso.__call__

    def trocar_e_responder(subscription_info, **kwargs):
        with engine_app.begin() as con:
            con.execute(text("delete from inscricao_push where sessao_id = :s"), {"s": sessao})
            con.execute(
                text(
                    "insert into inscricao_push (sessao_id, endpoint, chave_p256dh, chave_auth)"
                    " values (:s, :e, :p, :a)"
                ),
                {"s": sessao, "e": f"{FCM}/novo", "p": P256DH, "a": AUTH},
            )
        return original(subscription_info, **kwargs)

    monkeypatch.setattr(push.pywebpush, "webpush", trocar_e_responder)
    resultado = enviar(fabrica, aviso(engine_app))
    assert resultado.removidas == 1
    assert endpoints(engine_app) == {f"{FCM}/novo"}


def test_sem_destinos_nao_chama_ninguem(engine_app, fabrica, falso, vapid):
    resultado = enviar(fabrica, aviso(engine_app))
    assert resultado.destinos == 0
    assert falso.chamadas == []


def test_enviar_nao_faz_commit(engine_app, fabrica, falso, vapid):
    # Quem chama (`_processar_canal`) commita no fim; o enviador só deixa pronto.
    inscrito(engine_app, COMUM, f"{FCM}/410-1")
    with fabrica() as db:
        push.ENVIADOR.enviar(db, aviso(engine_app), Resultado())
        db.rollback()
    assert endpoints(engine_app) == {f"{FCM}/410-1"}


# --- prazo e progresso ------------------------------------------------------------------------


def test_progresso_salvo_a_cada_lote(engine_app, fabrica, falso, vapid, monkeypatch):
    monkeypatch.setattr(push, "SALVAR_A_CADA", 2)
    for n in range(5):
        inscrito(engine_app, COMUM if n % 2 else ADMIN, f"{FCM}/ok-{n}")
    salvos: list[int] = []
    resultado = Resultado(_salvar=lambda r: salvos.append(r.entregues))
    enviar(fabrica, aviso(engine_app), resultado)
    assert salvos == [2, 4, 5]
    assert resultado.entregues == 5


def test_tempo_esgotado_conta_o_resto_como_pulados(engine_app, fabrica, falso, vapid, monkeypatch):
    monkeypatch.setattr(push, "SALVAR_A_CADA", 2)
    for n in range(5):
        inscrito(engine_app, COMUM, f"{FCM}/ok-{n}")
    resultado = Resultado()
    lotes = iter([False, True])
    monkeypatch.setattr(resultado, "tempo_esgotado", lambda: next(lotes, True))
    enviar(fabrica, aviso(engine_app), resultado)
    assert len(falso.chamadas) == 2
    assert resultado.contagens() | {"reservados": 0} == {
        "destinos": 5,
        "entregues": 2,
        "falhas": 0,
        "removidas": 0,
        "pulados": 3,
        "reservados": 0,
    }


def test_manda_em_paralelo(engine_app, fabrica, falso, vapid):
    falso.atraso = 0.2
    for n in range(10):
        inscrito(engine_app, COMUM, f"{FCM}/ok-{n}")
    inicio = time.monotonic()
    enviar(fabrica, aviso(engine_app))
    assert time.monotonic() - inicio < 1.0  # em série seriam 2 s


def test_log_nao_mostra_endpoint(engine_app, fabrica, falso, vapid, caplog):
    inscrito(engine_app, COMUM, f"{FCM}/500-segredo")
    inscrito(engine_app, COMUM, f"{FCM}/rede-segredo")
    with caplog.at_level(logging.DEBUG):
        enviar(fabrica, aviso(engine_app))
    assert "segredo" not in caplog.text
    assert "fcm.googleapis" not in caplog.text


# --- de ponta a ponta: publicar com o push ligado ---------------------------------------------


def test_publicar_manda_push_ao_bloco_e_mede(logar, engine_app, falso, vapid):
    inscrito(engine_app, COMUM, f"{FCM}/ok-bloco1")  # Bloco 1
    inscrito(engine_app, COMUM, f"{FCM}/410-bloco1")
    comissao = logar(COMISSAO)
    criado = publicar(comissao, para_todos=False, blocos=[1])
    itens = comissao.get(f"/api/avisos/{criado['id']}/envios").json()["itens"]
    assert itens[0]["canal"] == "push"
    assert {
        k: itens[0][k] for k in ("situacao", "destinos", "entregues", "falhas", "removidas")
    } == {
        "situacao": "concluido",
        "destinos": 2,
        "entregues": 1,
        "falhas": 1,
        "removidas": 1,
    }
    assert json.loads(falso.chamadas[0]["data"])["url"] == f"/avisos/{criado['id']}"
    assert endpoints(engine_app) == {f"{FCM}/ok-bloco1"}


def test_unidade_de_outro_bloco_nao_recebe(logar, engine_app, falso, vapid):
    inscrito(engine_app, ADMIN, f"{FCM}/ok-bloco1")
    ativar(engine_app, "3101")
    inscrito(engine_app, "3101", f"{FCM}/ok-bloco3")
    publicar(logar(COMISSAO), para_todos=False, blocos=[1])
    assert [c["subscription_info"]["endpoint"] for c in falso.chamadas] == [f"{FCM}/ok-bloco1"]


def test_processar_com_o_enviador_de_verdade(engine_app, fabrica, falso, vapid):
    # A orquestração comum chama este enviador e grava o fim.
    inscrito(engine_app, COMUM, f"{FCM}/ok-1")
    with fabrica() as db:
        comissao = db.scalar(select(Unidade.id).where(Unidade.login == COMISSAO))
        aviso_id = db.execute(
            text(
                "insert into aviso (publicado_por, publicado_como, para_todos)"
                " values (:u, 'comissao', true) returning id"
            ),
            {"u": comissao},
        ).scalar_one()
        db.execute(
            text(
                "insert into aviso_versao (aviso_id, versao, titulo, texto, criada_por)"
                " values (:a, 1, 'Falta de água', 'Texto', :u)"
            ),
            {"a": aviso_id, "u": comissao},
        )
        notificacoes.registrar_publicacao(db, aviso_id)
        db.commit()
    notificacoes.processar(aviso_id, fabrica)
    with engine_app.connect() as con:
        situacao, entregues = con.execute(
            text(
                "select situacao, entregues from notificacao_envio"
                " where aviso_id = :a and canal = 'push'"
            ),
            {"a": aviso_id},
        ).one()
    assert (situacao, entregues) == ("concluido", 1)
    assert json.loads(falso.chamadas[0]["data"])["titulo"] == "Falta de água"
