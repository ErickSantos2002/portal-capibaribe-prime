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

Os canais de um aviso rodam **em paralelo** (o e-mail, lento, não atrasa o push), com um prazo
comum (`TEMPO_MAXIMO`, dentro dos 300 s da função): o que não couber no tempo vira `pulados`.

**Cota do Gmail** (revisão do contrato, achado 2): o e-mail **reserva** a cota antes de mandar
(`Resultado.reservar`), numa transação própria, com trava (`pg_advisory_xact_lock`): a reserva
vale na hora, mesmo se a função morrer depois, e dois envios ao mesmo tempo não leem a mesma
sobra. O banco não aceita e-mail tentado além do reservado. No fim, a sobra da reserva volta. As
contagens também vão para o banco aos poucos (`Resultado.salvar`).

Os canais moram em arquivos próprios, um por épico, com a interface `Enviador`:
- `app/servicos/push.py` → `ENVIADOR` (épico A, Web Push);
- `app/servicos/email.py` → `ENVIADOR` (épico B, cópia do aviso por e-mail).

Quem recebe é regra comum (`destinos_push`, `destinos_email`): as unidades ativas do destino do
aviso (todos ou os blocos dele), menos a unidade que publicou (ela já conta como quem leu).
"""

import logging
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
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
# Trava (advisory lock) de quem mexe na cota: reserva de cópia de aviso e link de recuperação.
TRAVA_COTA_EMAIL = 0x504F_5254_4D32  # "PORTM2"
# Prazo de um processamento inteiro (todos os canais e avisos): a função tem 300 s; sobra
# tempo para gravar o fim. Os enviadores param ao chegar nele (`Resultado.tempo_esgotado`).
TEMPO_MAXIMO = timedelta(seconds=240)
# Sugestão para os enviadores: gravar o progresso (`Resultado.salvar`) a cada tantos destinos.
SALVAR_A_CADA = 25


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
    """Contagens do envio, atualizadas pelo enviador enquanto trabalha. Mesmas regras do banco:
    `entregues + falhas + pulados <= destinos`, `removidas <= falhas` e, no e-mail,
    `entregues + falhas <= reservados`.

    - `reservar(n)`: separa até `n` e-mails da cota do Gmail **antes** de mandar e devolve
      quantos couberam (o resto é `pulados`). Grava na hora, com trava. Só o e-mail usa.
    - `salvar()`: grava as contagens agora (transação própria), para não sumirem se a função
      morrer. Chamar a cada `SALVAR_A_CADA` destinos.
    - `tempo_esgotado()`: passou do prazo; parar e contar o que faltou como `pulados`.
    """

    destinos: int = 0
    entregues: int = 0
    falhas: int = 0
    removidas: int = 0
    pulados: int = 0
    reservados: int = 0
    # `time.monotonic()` do fim do prazo; nulo = sem prazo.
    prazo: float | None = None
    _reservar: Callable[[int], int] | None = field(default=None, repr=False, compare=False)
    _salvar: Callable[["Resultado"], None] | None = field(default=None, repr=False, compare=False)

    def reservar(self, quantidade: int) -> int:
        if self._reservar is None or quantidade <= 0:
            return 0
        concedidos = self._reservar(quantidade)
        self.reservados += concedidos
        return concedidos

    def salvar(self) -> None:
        if self._salvar is not None:
            self._salvar(self)

    def tempo_esgotado(self) -> bool:
        return self.prazo is not None and time.monotonic() >= self.prazo

    def contagens(self) -> dict[str, int]:
        return {
            "destinos": self.destinos,
            "entregues": self.entregues,
            "falhas": self.falhas,
            "removidas": self.removidas,
            "pulados": self.pulados,
            "reservados": self.reservados,
        }


class Enviador(Protocol):
    """Um canal de notificação. `enviar` não faz commit em `db` (reserva e progresso vão por
    `resultado`, em transação própria) nem levanta por causa de um destino só (conta como
    falha e segue); levantar interrompe o canal inteiro. Respeita `resultado.tempo_esgotado()`.
    Roda numa thread própria, em paralelo com o outro canal."""

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
    """Faxina, depois os canais deste aviso e os pendentes que sobraram de outros. Os canais de
    cada aviso rodam em paralelo, cada um com a própria sessão de banco."""
    abrir = fabrica or fabrica_de_sessoes()
    prazo = time.monotonic() + TEMPO_MAXIMO.total_seconds()
    try:
        outros = _faxina(abrir)
        canais = enviadores()
        for aviso in [aviso_id, *(a for a in outros if a != aviso_id)]:
            with ThreadPoolExecutor(max_workers=len(canais)) as fios:
                tarefas = [
                    fios.submit(_processar_canal, abrir, aviso, enviador, prazo)
                    for enviador in canais
                ]
                for tarefa in tarefas:
                    tarefa.result()
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


def reservar_cota_email(abrir: Callable[[], Session], envio_id: int, quantidade: int) -> int:
    """Separa até `quantidade` e-mails da cota para o envio, com a trava da cota, e grava na
    hora (transação própria). Devolve quantos couberam."""
    with abrir() as db:
        db.execute(select(func.pg_advisory_xact_lock(TRAVA_COTA_EMAIL)))
        concedidos = min(quantidade, cota_email_avisos(db))
        if concedidos > 0:
            db.execute(
                update(NotificacaoEnvio)
                .where(NotificacaoEnvio.id == envio_id)
                .values(reservados=NotificacaoEnvio.reservados + concedidos)
            )
        db.commit()
    return concedidos


def reservar_email_recuperacao(db: Session) -> bool:
    """Para o "esqueci a senha": pega a trava da cota **na transação de quem chama** e diz se
    ainda cabe um e-mail. Quem chama cria o token (que conta na cota) e faz o commit, que
    solta a trava. Assim, pedidos e avisos ao mesmo tempo não passam juntos da cota."""
    db.execute(select(func.pg_advisory_xact_lock(TRAVA_COTA_EMAIL)))
    return cota_email_recuperacao(db) > 0


def _gravar(abrir: Callable[[], Session], envio_id: int, resultado: Resultado) -> None:
    with abrir() as db:
        db.execute(
            update(NotificacaoEnvio)
            .where(NotificacaoEnvio.id == envio_id)
            .values(**resultado.contagens())
        )
        db.commit()


def _processar_canal(
    abrir: Callable[[], Session], aviso_id: int, enviador: Enviador, prazo: float | None = None
) -> None:
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

        resultado = Resultado(
            prazo=prazo,
            _reservar=lambda n: reservar_cota_email(abrir, envio_id, n),
            _salvar=lambda r: _gravar(abrir, envio_id, r),
        )
        situacao = SituacaoEnvio.concluido
        try:
            enviador.enviar(db, carregar_aviso(db, aviso_id), resultado)
            db.commit()
            # A sobra da reserva (o que não foi tentado) volta para a cota.
            resultado.reservados = min(resultado.reservados, resultado.entregues + resultado.falhas)
        except Exception as erro:
            db.rollback()
            situacao = SituacaoEnvio.interrompido
            # Só o tipo: a mensagem de um erro de SMTP pode trazer o e-mail do destinatário. A
            # reserva fica inteira (não se sabe quantos saíram).
            log.error(
                "canal %s interrompido no aviso %s (%s)",
                enviador.canal,
                aviso_id,
                type(erro).__name__,
            )
        db.execute(
            update(NotificacaoEnvio)
            .where(NotificacaoEnvio.id == envio_id)
            .values(situacao=situacao, **resultado.contagens())
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
    """E-mails já gastos da cota: cópias de aviso **reservadas** (separadas antes de mandar; a
    sobra volta quando o envio termina) e links de recuperação criados (cada token é um
    e-mail)."""
    desde = func.now() - timedelta(hours=24)
    avisos = db.scalar(
        select(func.coalesce(func.sum(NotificacaoEnvio.reservados), 0)).where(
            NotificacaoEnvio.canal == Canal.email, NotificacaoEnvio.iniciado_em > desde
        )
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
