"""Ponto único "notificar a publicação de um aviso" (H-13; spec do M2, seção 5). Arquivo comum.

Como funciona:

1. `registrar_publicacao(db, aviso_id)`, **na mesma transação** da publicação
   (`app.servicos.avisos.publicar`): uma linha `pendente` em `notificacao_envio` por canal. Se o
   aviso foi gravado, o pedido de notificar também foi (caixa de saída).
2. `agendar(tarefas, aviso_id)`, na rota: depois da resposta, roda `processar(aviso_id)`
   (`app.servicos.segundo_plano`: `wait_until` na Vercel, `BackgroundTasks` fora dela).
3. `processar` reivindica cada canal com um UPDATE `pendente → enviando` (só um processo
   ganha: não manda duas vezes) e chama o enviador do canal. Antes, faz a faxina: o que está
   `enviando` há mais de 10 minutos (a função morreu) ou `pendente` há mais de 24 horas vira
   `interrompido`, e os `pendente` recentes de outros avisos (o trabalho que se perdeu) são
   enviados agora.

Garantia: **no máximo uma vez** por aviso e canal. Se a função morrer no meio, o envio fica
`interrompido` com as contagens até ali e não se repete (avisar duas vezes incomoda mais que
uma notificação a menos, e o mural continua sendo o registro oficial).

Os canais moram em arquivos próprios, um por épico, com a interface `Enviador`:
- `app/servicos/push.py` → `ENVIADOR` (épico A, Web Push);
- `app/servicos/email.py` → `ENVIADOR` (épico B, cópia do aviso por e-mail).

Quem recebe é regra comum (`destinos_push`, `destinos_email`): as unidades ativas do destino do
aviso (todos ou os blocos dele), menos a unidade que publicou (ela já conta como quem leu).
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol

from fastapi import BackgroundTasks
from sqlalchemy import Select, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.banco import fabrica_de_sessoes
from app.modelos import (
    Aviso,
    AvisoBloco,
    AvisoVersao,
    Bloco,
    Canal,
    InscricaoPush,
    NotificacaoEnvio,
    Sessao,
    SituacaoEnvio,
    TokenRecuperacao,
    Unidade,
)
from app.seguranca.sessoes import VALIDADE
from app.servicos import segundo_plano

log = logging.getLogger(__name__)

# Faxina (passo 3): a função dura no máximo 300 s; 10 minutos enviando é função morta.
ENVIANDO_NO_MAXIMO = timedelta(minutes=10)
# Notificação de aviso de ontem não ajuda ninguém: depois disso, não manda mais.
PENDENTE_VALE_POR = timedelta(hours=24)

# Gmail grátis: cerca de 500 destinatários por dia (ADR-0006). Margem de 50, e 50 guardados
# para o "esqueci a senha", que nunca pode ficar sem cota por causa de um aviso grande.
LIMITE_EMAILS_24H = 450
RESERVA_RECUPERACAO = 50


@dataclass(frozen=True)
class AvisoParaNotificar:
    """O que os enviadores precisam saber do aviso (versão em vigor)."""

    aviso_id: int
    titulo: str
    texto: str
    categoria: str
    publicado_por: int
    para_todos: bool
    blocos: tuple[int, ...]  # números dos blocos; vazio se para todos

    @property
    def caminho(self) -> str:
        """Endereço do aviso no Portal: o toque na notificação e o link do e-mail abrem aqui."""
        return f"/avisos/{self.aviso_id}"


@dataclass
class Resultado:
    """Contagens do envio, atualizadas pelo enviador enquanto trabalha (se ele cair no meio,
    o que já contou fica gravado). Mesmas regras do banco: `entregues + falhas + pulados <=
    destinos` e `removidas <= falhas`."""

    destinos: int = 0
    entregues: int = 0
    falhas: int = 0
    removidas: int = 0
    pulados: int = 0


class Enviador(Protocol):
    """Um canal de notificação. `enviar` não faz commit nem levanta por causa de um destino só
    (conta como falha e segue); levantar interrompe o canal inteiro."""

    canal: Canal

    def ligado(self) -> bool:
        """Configurado (variáveis de ambiente) e pronto. Desligado = envio `desligado`."""
        ...

    def enviar(self, db: Session, aviso: AvisoParaNotificar, resultado: Resultado) -> None: ...


def enviadores() -> list[Enviador]:
    """Os canais, na ordem de envio (push primeiro: é o principal e o mais rápido)."""
    from app.servicos import email, push

    return [push.ENVIADOR, email.ENVIADOR]


# --- 1 e 2: registrar e agendar --------------------------------------------------------------


def registrar_publicacao(db: Session, aviso_id: int) -> None:
    """Pede a notificação do aviso, na transação de quem publica. Não faz commit."""
    db.execute(
        insert(NotificacaoEnvio)
        .values([{"aviso_id": aviso_id, "canal": c.value} for c in Canal])
        .on_conflict_do_nothing(constraint="notificacao_envio_unico")
    )


def agendar(tarefas: BackgroundTasks, aviso_id: int) -> None:
    """Na rota, depois do commit da publicação: notifica depois da resposta."""
    segundo_plano.agendar(tarefas, processar, aviso_id)


# --- 3: processar ----------------------------------------------------------------------------


def processar(aviso_id: int, fabrica: Callable[[], Session] | None = None) -> None:
    """Faxina, depois os canais deste aviso e os pendentes que sobraram de outros."""
    abrir = fabrica or fabrica_de_sessoes()
    try:
        outros = _faxina(abrir)
        for aviso in [aviso_id, *(a for a in outros if a != aviso_id)]:
            for enviador in enviadores():
                _processar_canal(abrir, aviso, enviador)
    except Exception:
        # Depois da resposta ninguém vê a exceção; o log da Vercel guarda por 1 hora.
        log.exception("falha ao processar notificações do aviso %s", aviso_id)


def _faxina(abrir: Callable[[], Session]) -> list[int]:
    """Interrompe o que morreu ou venceu; devolve os avisos com envio pendente recente."""
    with abrir() as db:
        agora = db.scalar(select(func.now()))
        db.execute(
            update(NotificacaoEnvio)
            .where(
                (
                    (NotificacaoEnvio.situacao == SituacaoEnvio.enviando)
                    & (NotificacaoEnvio.iniciado_em < agora - ENVIANDO_NO_MAXIMO)
                )
                | (
                    (NotificacaoEnvio.situacao == SituacaoEnvio.pendente)
                    & (NotificacaoEnvio.criado_em < agora - PENDENTE_VALE_POR)
                )
            )
            .values(situacao=SituacaoEnvio.interrompido)
        )
        pendentes = db.scalars(
            select(NotificacaoEnvio.aviso_id)
            .where(NotificacaoEnvio.situacao == SituacaoEnvio.pendente)
            .distinct()
            .order_by(NotificacaoEnvio.aviso_id)
        ).all()
        db.commit()
    return list(pendentes)


def _reivindicar(db: Session, aviso_id: int, canal: Canal, para: SituacaoEnvio) -> int | None:
    return db.scalar(
        update(NotificacaoEnvio)
        .where(
            NotificacaoEnvio.aviso_id == aviso_id,
            NotificacaoEnvio.canal == canal,
            NotificacaoEnvio.situacao == SituacaoEnvio.pendente,
        )
        .values(situacao=para)
        .returning(NotificacaoEnvio.id)
    )


def _processar_canal(abrir: Callable[[], Session], aviso_id: int, enviador: Enviador) -> None:
    with abrir() as db:
        arquivado = db.scalar(select(Aviso.arquivado_em).where(Aviso.id == aviso_id))
        if arquivado is not None:
            # Arquivado antes de sair a notificação: não chama ninguém para um aviso que sumiu.
            para = SituacaoEnvio.interrompido
        elif not enviador.ligado():
            para = SituacaoEnvio.desligado
        else:
            para = SituacaoEnvio.enviando
        envio_id = _reivindicar(db, aviso_id, enviador.canal, para)
        db.commit()
        if envio_id is None or para is not SituacaoEnvio.enviando:
            return

        resultado = Resultado()
        situacao = SituacaoEnvio.concluido
        try:
            enviador.enviar(db, carregar_aviso(db, aviso_id), resultado)
            db.commit()
        except Exception:
            db.rollback()
            situacao = SituacaoEnvio.interrompido
            # Só o tipo: a mensagem de um erro de SMTP pode trazer o e-mail do destinatário.
            log.error("canal %s interrompido no aviso %s", enviador.canal, aviso_id, exc_info=False)
        db.execute(
            update(NotificacaoEnvio)
            .where(NotificacaoEnvio.id == envio_id)
            .values(situacao=situacao, **vars(resultado))
        )
        db.commit()


def carregar_aviso(db: Session, aviso_id: int) -> AvisoParaNotificar:
    aviso = db.get_one(Aviso, aviso_id)
    versao = db.scalars(
        select(AvisoVersao)
        .where(AvisoVersao.aviso_id == aviso_id)
        .order_by(AvisoVersao.versao.desc())
        .limit(1)
    ).one()
    blocos = db.scalars(
        select(Bloco.numero)
        .join(AvisoBloco, AvisoBloco.bloco_id == Bloco.id)
        .where(AvisoBloco.aviso_id == aviso_id)
        .order_by(Bloco.numero)
    ).all()
    return AvisoParaNotificar(
        aviso_id=aviso.id,
        titulo=versao.titulo,
        texto=versao.texto,
        categoria=versao.categoria,
        publicado_por=aviso.publicado_por,
        para_todos=aviso.para_todos,
        blocos=tuple(blocos),
    )


# --- quem recebe (regra comum aos dois canais, H-13) -------------------------------------------


@dataclass(frozen=True)
class DestinoPush:
    sessao_id: int
    endpoint: str
    chave_p256dh: str
    chave_auth: str


@dataclass(frozen=True)
class DestinoEmail:
    unidade_id: int
    login: str
    email: str


def _unidades_do_destino(aviso: AvisoParaNotificar) -> Select[tuple[int]]:
    """Unidades ativas que o aviso alcança, menos quem publicou."""
    consulta = select(Unidade.id).where(Unidade.ativa, Unidade.id != aviso.publicado_por)
    if not aviso.para_todos:
        consulta = consulta.where(
            Unidade.bloco_id.in_(
                select(AvisoBloco.bloco_id).where(AvisoBloco.aviso_id == aviso.aviso_id)
            )
        )
    return consulta


def destinos_push(db: Session, aviso: AvisoParaNotificar) -> list[DestinoPush]:
    """Os aparelhos inscritos das unidades do destino, só de sessões que ainda valem (as mesmas
    regras de `app.seguranca.sessoes.buscar_sessao`) e de unidades com o primeiro acesso feito.
    Os dois celulares do casal são duas sessões: os dois recebem (H-05)."""
    linhas = db.execute(
        select(
            InscricaoPush.sessao_id,
            InscricaoPush.endpoint,
            InscricaoPush.chave_p256dh,
            InscricaoPush.chave_auth,
        )
        .join(Sessao, Sessao.id == InscricaoPush.sessao_id)
        .join(Unidade, Unidade.id == Sessao.unidade_id)
        .where(
            Unidade.id.in_(_unidades_do_destino(aviso)),
            Unidade.precisa_trocar_senha.is_(False),
            Sessao.encerrada_em.is_(None),
            Sessao.ultimo_uso_em > func.now() - VALIDADE,
            Sessao.criada_em >= Unidade.senha_trocada_em,
        )
        .order_by(InscricaoPush.sessao_id)
    ).all()
    return [DestinoPush(*linha) for linha in linhas]


def destinos_email(db: Session, aviso: AvisoParaNotificar) -> list[DestinoEmail]:
    """As unidades do destino que já entraram e informaram e-mail, uma vez cada."""
    linhas = db.execute(
        select(Unidade.id, Unidade.login, Unidade.email)
        .where(
            Unidade.id.in_(_unidades_do_destino(aviso)),
            Unidade.ativada_em.is_not(None),
            Unidade.email.is_not(None),
        )
        .order_by(Unidade.login)
    ).all()
    return [DestinoEmail(*linha) for linha in linhas]


# --- cota do Gmail ---------------------------------------------------------------------------


def emails_nas_ultimas_24h(db: Session) -> int:
    """E-mails já gastos da cota: cópias de aviso tentadas (entregues + falhas) e links de
    recuperação criados (cada token é um e-mail)."""
    desde = func.now() - timedelta(hours=24)
    avisos = db.scalar(
        select(
            func.coalesce(func.sum(NotificacaoEnvio.entregues + NotificacaoEnvio.falhas), 0)
        ).where(NotificacaoEnvio.canal == Canal.email, NotificacaoEnvio.iniciado_em > desde)
    )
    links = db.scalar(select(func.count()).where(TokenRecuperacao.criado_em > desde))
    return int(avisos or 0) + int(links or 0)


def cota_email_avisos(db: Session) -> int:
    """Quantas cópias de aviso ainda cabem agora (sem tocar na reserva do "esqueci a senha").
    O que não couber conta como `pulados`."""
    return max(0, LIMITE_EMAILS_24H - RESERVA_RECUPERACAO - emails_nas_ultimas_24h(db))


def cota_email_recuperacao(db: Session) -> int:
    """Quantos links de recuperação ainda cabem agora (podem usar a reserva)."""
    return max(0, LIMITE_EMAILS_24H - emails_nas_ultimas_24h(db))
