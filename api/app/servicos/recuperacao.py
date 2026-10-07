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

`conferir(db, token)` e `redefinir(db, dados, user_agent)`: o link do e-mail. Token desconhecido,
usado, vencido ou de senha já trocada dão a mesma resposta (410 `link_invalido`).
"""

import logging
import secrets
from collections.abc import Callable
from datetime import timedelta
from email.message import EmailMessage

import psycopg
from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.banco import fabrica_de_sessoes
from app.configuracao import ConfigEmail, config_email
from app.erros_api import ErroApi
from app.esquemas.comum import Eu, UnidadeRef
from app.esquemas.recuperacao import RedefinirSenha
from app.modelos import TokenRecuperacao, Unidade
from app.seguranca.sessoes import hash_do_token, trocar_senha_e_sessao
from app.servicos import email, tentativas
from app.servicos.acesso import eu_da_unidade
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
            config, mensagem, token_hash = pronto
            try:
                email.enviar_uma(config, mensagem)
            except email.NadaSaiu:
                # Nem conectou (senha de app errada, Gmail fora): o link nunca chegou a ninguém.
                # Apagá-lo devolve a cota do dia e um dos 3 pedidos da hora.
                _apagar_token(abrir, token_hash)
                raise
    except Exception as erro:  # noqa: BLE001 - depois da resposta ninguém veria a exceção
        causa = erro.__cause__ if isinstance(erro, email.NadaSaiu) and erro.__cause__ else erro
        log.error("pedido de recuperação não terminou (%s)", type(causa).__name__)


def _registrar_pedido(
    abrir: Callable[[], Session], login: str
) -> tuple[ConfigEmail, EmailMessage, str] | None:
    """Passos 1 a 6 menos o envio. Devolve o e-mail a mandar e o hash do token, se houver."""
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
    if mensagem is None or config is None or token is None:
        return None
    return config, mensagem, hash_do_token(token)


def _apagar_token(abrir: Callable[[], Session], token_hash: str) -> None:
    with abrir() as db:
        db.execute(delete(TokenRecuperacao).where(TokenRecuperacao.token_hash == token_hash))
        db.commit()


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
        restricao = _restricao(erro)
        if restricao in _LIMITES:
            return "limite"
        if restricao == "token_recuperacao_sem_email":
            return "sem_email"
        raise
    return None


def _restricao(erro: DBAPIError) -> str | None:
    """Nome da restrição (CHECK ou trigger com `constraint =`) que o banco recusou."""
    return erro.orig.diag.constraint_name if isinstance(erro.orig, psycopg.Error) else None


# --- conferir e usar o link (contrato, 4.3) ----------------------------------------------------

MSG_LINK_INVALIDO = (
    'Este link venceu ou já foi usado. Peça outro em "Esqueci minha senha". '
    "Se você já criou a senha nova, é só entrar com ela."
)
_RECUSAS_DO_TOKEN = {"token_recuperacao_usado", "token_recuperacao_vencido"}


def link_invalido() -> ErroApi:
    """A mesma resposta para token desconhecido, usado, vencido ou de senha já trocada."""
    return ErroApi(410, "link_invalido", MSG_LINK_INVALIDO)


def _token_que_vale(db: Session, token: str, travar: bool = False) -> tuple[int, Unidade]:
    """O id do token e a unidade dele, se o link ainda vale (as mesmas regras do banco: não
    usado, dentro da hora, pedido depois da última troca de senha, unidade ativa e ativada)."""
    consulta = (
        select(TokenRecuperacao.id, Unidade)
        .join(Unidade, Unidade.id == TokenRecuperacao.unidade_id)
        .where(
            TokenRecuperacao.token_hash == hash_do_token(token),
            TokenRecuperacao.usado_em.is_(None),
            TokenRecuperacao.expira_em > func.now(),
            TokenRecuperacao.criado_em >= Unidade.senha_trocada_em,
            Unidade.ativa.is_(True),
            Unidade.ativada_em.is_not(None),
        )
    )
    if travar:
        # Trava o token **e a unidade**: dois "salvar" ao mesmo tempo, com o mesmo link ou com
        # dois links da mesma unidade, ficam em fila; o segundo relê a unidade com a senha já
        # trocada e não acha mais link que valha (revisão do épico B, item 2).
        consulta = consulta.with_for_update(of=[TokenRecuperacao, Unidade])
    achado = db.execute(consulta).one_or_none()
    if achado is None:
        raise link_invalido()
    return achado[0], achado[1]


def conferir(db: Session, token: str) -> UnidadeRef:
    """O link vale? Devolve a placa da unidade. Não gasta o link."""
    _, unidade = _token_que_vale(db, token)
    return UnidadeRef.de_login(unidade.login)


def redefinir(db: Session, dados: RedefinirSenha, user_agent: str | None) -> tuple[Eu, str]:
    """Usa o link: marca o token como usado **antes** de gravar a senha (o banco considera
    vencido todo link pedido antes da troca, então usar um mata os outros), grava a senha nova,
    desconecta todos os aparelhos e abre uma sessão para quem redefiniu. Devolve o `Eu` e o
    token da sessão nova. Não faz commit."""
    token_id, unidade = _token_que_vale(db, dados.token, travar=True)
    try:
        with db.begin_nested():
            db.execute(
                update(TokenRecuperacao)
                .where(TokenRecuperacao.id == token_id)
                .values(usado_em=func.now())
            )
    except DBAPIError as erro:
        if _restricao(erro) in _RECUSAS_DO_TOKEN:
            raise link_invalido() from None
        raise
    sessao = trocar_senha_e_sessao(db, unidade.id, dados.senha_nova, user_agent)
    tentativas.esquecer_login(db, unidade.login)
    registrar(
        db, Acao.senha_redefinida, unidade_id=unidade.id, entidade="unidade", entidade_id=unidade.id
    )
    return eu_da_unidade(db, unidade), sessao
