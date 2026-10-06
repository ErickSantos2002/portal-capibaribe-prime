"""Web Push (H-05, H-13; ADR-0006). **Pertence ao épico A** do M2.

Contrato: `docs/superpowers/specs/m2-contrato.md`, seções 4.2 e 5; detalhes do épico em
`docs/superpowers/specs/m2-push.md`, seção 2.

- Inscrição por aparelho (`estado`, `inscrever`, `remover`): a inscrição é da **sessão** que
  fez a requisição; some sozinha quando a sessão é encerrada (trigger da migração 0005).
- `ENVIADOR`: o canal push de `app.servicos.notificacoes`. Manda em paralelo, em lotes; as
  threads só fazem o POST e devolvem o resultado; contar, apagar inscrição morta e gravar o
  progresso é na thread principal (a sessão do banco não é segura entre threads).
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

import pywebpush
from py_vapid import Vapid
from sqlalchemy import delete, exists, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.configuracao import config_push
from app.erros_api import ErroApi
from app.esquemas.push import EstadoNotificacoes, PushAviso
from app.esquemas.push import InscricaoPush as DadosInscricao
from app.modelos import Canal, InscricaoPush
from app.servicos.notificacoes import (
    SALVAR_A_CADA,
    AvisoParaNotificar,
    DestinoPush,
    Resultado,
    destinos_push,
)

log = logging.getLogger(__name__)

MSG_DESLIGADAS = "As notificações ainda não estão ligadas no Portal."
MSG_LIMITE = "Este apartamento já tem 10 aparelhos com notificação. Desative em algum deles."
MSG_SEM_SESSAO = "Entre de novo com o bloco, o apartamento e a senha."

# Aviso de três dias atrás ainda interessa a quem estava com o celular desligado; depois disso
# o serviço de push pode descartar (o mural continua lá).
TTL_SEGUNDOS = 3 * 24 * 60 * 60
TEMPO_LIMITE_SEGUNDOS = 10
# Cada POST espera a rede; 10 ao mesmo tempo dão conta de 320 apartamentos em poucos segundos.
THREADS = 10


# --- inscrição deste aparelho (rotas) ----------------------------------------------------------


def estado(db: Session, sessao_id: int) -> EstadoNotificacoes:
    config = config_push()
    inscrito = db.scalar(select(exists().where(InscricaoPush.sessao_id == sessao_id)))
    return EstadoNotificacoes(
        disponivel=config is not None,
        chave_publica=config.chave_publica if config else None,
        este_aparelho=bool(inscrito),
    )


def inscrever(db: Session, sessao_id: int, dados: DadosInscricao) -> None:
    """Guarda a inscrição na sessão deste aparelho e faz o commit.

    O `app` não pode mudar o `endpoint` de uma linha (só `sessao_id` e as chaves): a inscrição
    antiga desta sessão com outro endpoint é apagada, e o endpoint que já estava em outra sessão
    (o navegador entrou de novo) passa para esta.
    """
    if config_push() is None:
        raise ErroApi(503, "notificacoes_desligadas", MSG_DESLIGADAS)
    db.execute(
        delete(InscricaoPush).where(
            InscricaoPush.sessao_id == sessao_id, InscricaoPush.endpoint != dados.endpoint
        )
    )
    novo = insert(InscricaoPush).values(
        sessao_id=sessao_id,
        endpoint=dados.endpoint,
        chave_p256dh=dados.p256dh,
        chave_auth=dados.auth,
    )
    try:
        db.execute(
            novo.on_conflict_do_update(
                index_elements=[InscricaoPush.endpoint],
                set_={
                    "sessao_id": novo.excluded.sessao_id,
                    "chave_p256dh": novo.excluded.chave_p256dh,
                    "chave_auth": novo.excluded.chave_auth,
                },
            )
        )
        db.commit()
    except IntegrityError as erro:
        db.rollback()
        restricao = getattr(getattr(erro.orig, "diag", None), "constraint_name", None)
        if restricao == "inscricao_push_limite":
            raise ErroApi(409, "limite_de_aparelhos", MSG_LIMITE) from None
        if restricao == "inscricao_push_sessao_encerrada":
            raise ErroApi(401, "sem_sessao", MSG_SEM_SESSAO) from None
        raise


def remover(db: Session, sessao_id: int) -> None:
    """Desativa neste aparelho. Idempotente; funciona com o push desligado."""
    db.execute(delete(InscricaoPush).where(InscricaoPush.sessao_id == sessao_id))
    db.commit()


# --- envio (canal push) ------------------------------------------------------------------------


class Saida(Enum):
    entregue = "entregue"
    removida = "removida"  # 404 ou 410: o serviço diz que a inscrição não existe mais
    falha = "falha"  # outro status, rede, tempo esgotado: tenta de novo no próximo aviso


def _mandar(
    destino: DestinoPush, corpo: str, chave: Vapid, contato: str, urgencia: str, topico: str
) -> Saida:
    """Um POST. Roda numa thread: não toca no banco e não loga o endpoint (identifica o
    aparelho)."""
    try:
        pywebpush.webpush(
            subscription_info={
                "endpoint": destino.endpoint,
                "keys": {"p256dh": destino.chave_p256dh, "auth": destino.chave_auth},
            },
            data=corpo,
            vapid_private_key=chave,
            # Dicionário novo a cada POST: o `webpush` grava nele o `aud` do endpoint.
            vapid_claims={"sub": contato},
            ttl=TTL_SEGUNDOS,
            headers={"Urgency": urgencia, "Topic": topico},
            timeout=TEMPO_LIMITE_SEGUNDOS,
        )
    except pywebpush.WebPushException as erro:
        return Saida.removida if erro.status_code in (404, 410) else Saida.falha
    except Exception:  # noqa: BLE001 - rede, tempo, resposta estranha: conta e segue
        return Saida.falha
    return Saida.entregue


class EnviadorPush:
    canal = Canal.push

    def ligado(self) -> bool:
        return config_push() is not None

    def enviar(self, db: Session, aviso: AvisoParaNotificar, resultado: Resultado) -> None:
        config = config_push()
        if config is None:
            raise RuntimeError("push desligado no meio do envio")
        destinos = destinos_push(db, aviso)
        resultado.destinos = len(destinos)
        if not destinos:
            return
        corpo = json.dumps(
            PushAviso(
                aviso_id=aviso.aviso_id,
                titulo=aviso.titulo,
                categoria=aviso.categoria,
                url=aviso.caminho,
            ).model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        chave = Vapid.from_string(config.chave_privada)
        urgencia = "high" if aviso.categoria == "urgente" else "normal"
        topico = f"aviso-{aviso.aviso_id}"
        lote = max(1, SALVAR_A_CADA)
        with ThreadPoolExecutor(max_workers=min(THREADS, len(destinos))) as fios:
            for inicio in range(0, len(destinos), lote):
                if resultado.tempo_esgotado():
                    resultado.pulados = len(destinos) - inicio
                    break
                parte = destinos[inicio : inicio + lote]
                saidas = list(
                    fios.map(
                        lambda d: _mandar(d, corpo, chave, config.contato, urgencia, topico),
                        parte,
                    )
                )
                # Daqui para baixo, só a thread principal: contar e apagar as mortas.
                for destino, saida in zip(parte, saidas, strict=True):
                    if saida is Saida.entregue:
                        resultado.entregues += 1
                        continue
                    resultado.falhas += 1
                    if saida is Saida.removida:
                        resultado.removidas += 1
                        # Pela sessão **e** pelo endpoint: se o aparelho reativou no meio
                        # (endpoint novo), a inscrição nova fica.
                        db.execute(
                            delete(InscricaoPush).where(
                                InscricaoPush.sessao_id == destino.sessao_id,
                                InscricaoPush.endpoint == destino.endpoint,
                            )
                        )
                resultado.salvar()
        log.info(
            "push do aviso %s: %s destinos, %s entregues, %s falhas (%s removidas), %s pulados",
            aviso.aviso_id,
            resultado.destinos,
            resultado.entregues,
            resultado.falhas,
            resultado.removidas,
            resultado.pulados,
        )


ENVIADOR = EnviadorPush()
