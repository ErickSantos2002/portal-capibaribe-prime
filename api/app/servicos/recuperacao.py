"""Esqueci a senha (H-04). **Pertence ao épico B** do M2.

Contrato: `docs/superpowers/specs/m2-contrato.md`, seção 4.3; spec do épico:
`docs/superpowers/specs/m2-email.md`, seção 2.5.

**`processar_pedido(login)` roda depois da resposta** (`segundo_plano.agendar`, revisão do
contrato, achado 3): a rota não abre o banco, então o tempo de resposta é o mesmo para qualquer
apartamento. Abre a própria sessão e:

1. unidade ativa pelo login (não existe: nada, nem histórico); sem primeiro acesso ou sem
   e-mail: `motivo = "sem_email"`;
2. `config_email()` ligada, senão `motivo = "desligado"`;
3. `reservar_email_recuperacao(db)` (trava da cota), senão `motivo = "cota"`;
4. INSERT do token (`secrets.token_urlsafe(32)`, guardado como SHA-256) num *savepoint*; as
   restrições `token_recuperacao_limite_hora`/`_dia` viram `motivo = "limite"`;
5. histórico `recuperacao_pedida` (ação do sistema, entidade `unidade`, `{"enviado",
   "motivo"}`) no máximo uma vez por unidade por hora (`registrado_recentemente`);
6. commit (solta a trava) e, só então, o e-mail com o link (token em texto só na memória).

Nada aqui levanta para fora: erro vira log só com o tipo (nem login, nem e-mail, nem token).
"""

import logging
import secrets
from collections.abc import Callable
from datetime import timedelta
from email.message import EmailMessage

import psycopg
from sqlalchemy import insert, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.banco import fabrica_de_sessoes
from app.configuracao import ConfigEmail, config_email
from app.esquemas.comum import UnidadeRef
from app.modelos import TokenRecuperacao, Unidade
from app.seguranca.sessoes import hash_do_token
from app.servicos import email
from app.servicos.historico import Acao, registrado_recentemente, registrar
from app.servicos.notificacoes import reservar_email_recuperacao

log = logging.getLogger(__name__)

# Um registro de pedido por unidade por hora no histórico (contrato, 4.3, passo 5).
JANELA_DO_HISTORICO = timedelta(hours=1)
_LIMITES = {"token_recuperacao_limite_hora", "token_recuperacao_limite_dia"}


def processar_pedido(login: str, fabrica: Callable[[], Session] | None = None) -> None:
    """Pedido de link de recuperação, depois da resposta. Nunca levanta."""
    try:
        abrir = fabrica or fabrica_de_sessoes()
        pronto = _registrar_pedido(abrir, login)
        if pronto is not None:
            config, mensagem = pronto
            email.enviar_uma(config, mensagem)
    except Exception as erro:  # noqa: BLE001 - depois da resposta ninguém veria a exceção
        log.error("pedido de recuperação não terminou (%s)", type(erro).__name__)


def _registrar_pedido(
    abrir: Callable[[], Session], login: str
) -> tuple[ConfigEmail, EmailMessage] | None:
    """Passos 1 a 6 menos o envio. Devolve o e-mail a mandar, se houver."""
    with abrir() as db:
        unidade = db.scalars(
            select(Unidade).where(Unidade.login == login, Unidade.ativa.is_(True))
        ).one_or_none()
        if unidade is None:
            return None
        config = config_email()
        token: str | None = None
        if unidade.ativada_em is None or not unidade.email:
            motivo: str | None = "sem_email"
        elif config is None:
            motivo = "desligado"
        elif not reservar_email_recuperacao(db):
            motivo = "cota"
        else:
            token = secrets.token_urlsafe(32)
            motivo = _gravar_token(db, unidade.id, token)
            if motivo is not None:
                token = None
        if not registrado_recentemente(
            db,
            Acao.recuperacao_pedida,
            entidade="unidade",
            entidade_id=unidade.id,
            janela=JANELA_DO_HISTORICO,
        ):
            registrar(
                db,
                Acao.recuperacao_pedida,
                unidade_id=None,
                entidade="unidade",
                entidade_id=unidade.id,
                detalhes={"enviado": token is not None, "motivo": motivo},
            )
        mensagem = None
        if token is not None and config is not None and unidade.email:
            ref = UnidadeRef.de_login(unidade.login)
            mensagem = email.mensagem_de_recuperacao(ref, token, unidade.email, config)
        db.commit()
    return (config, mensagem) if mensagem is not None and config is not None else None


def _gravar_token(db: Session, unidade_id: int, token: str) -> str | None:
    """INSERT do token num *savepoint*. Devolve o motivo se o banco recusou."""
    try:
        with db.begin_nested():
            db.execute(
                insert(TokenRecuperacao).values(
                    unidade_id=unidade_id, token_hash=hash_do_token(token)
                )
            )
    except DBAPIError as erro:
        restricao = erro.orig.diag.constraint_name if isinstance(erro.orig, psycopg.Error) else None
        if restricao in _LIMITES:
            return "limite"
        if restricao == "token_recuperacao_sem_email":
            return "sem_email"
        raise
    return None
