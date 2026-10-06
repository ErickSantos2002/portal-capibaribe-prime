"""Bloqueio por senhas erradas, por (login, IP) (H-03; revisão do M1, C2).

Regra: 5 senhas erradas do mesmo IP no mesmo login, dentro de 15 minutos, bloqueiam aquele IP
naquele login por 15 minutos. Erros com mais de 15 minutos deixam de contar; a senha certa zera
o contador daquele par. Outro IP não é afetado: o dono, de casa, entra mesmo que alguém esteja
errando a senha dele de outro lugar. Contra tentativa em massa (muitos logins de um IP), a
barreira é o firewall da Vercel (20 logins por IP a cada 10 minutos, ADR-0005).

Conta a entrada (`POST /api/acesso/entrar`) e o "Apagar meus dados", que também pede a senha.
Login inexistente conta igual a um que existe: a resposta não revela se o apartamento existe.

Nada aqui faz commit. A recusa sobe como `ErroQueConta`: a rota faz o commit (a tentativa tem
que ficar gravada) e então levanta.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.erros_api import ErroApi
from app.modelos import EntradaTentativa
from app.servicos.historico import Acao, registrar

TENTATIVAS_ATE_BLOQUEAR = 5
JANELA = timedelta(minutes=15)
# A partir do 3º erro, a mensagem diz quantas tentativas faltam (U3).
AVISAR_A_PARTIR_DE = 3


class ErroQueConta(ErroApi):
    """Recusa que precisa de commit antes de chegar ao cliente: a tentativa errada e o bloqueio
    ficam gravados mesmo com a resposta de erro."""


@dataclass
class Tentativa:
    """O par (login, IP) já travado (`for update`) até o fim da transação."""

    linha: EntradaTentativa
    agora: datetime


def _mensagem_de_bloqueio(minutos: int) -> str:
    tempo = "1 minuto" if minutos == 1 else f"{minutos} minutos"
    return (
        f"Entrada bloqueada por {tempo} depois de várias senhas erradas. Se não foi você, "
        "avise a administração do Portal no grupo do WhatsApp."
    )


def erro_de_bloqueio(bloqueada_ate: datetime, agora: datetime) -> ErroQueConta:
    minutos = max(1, math.ceil((bloqueada_ate - agora).total_seconds() / 60))
    return ErroQueConta(
        423,
        "unidade_bloqueada",
        _mensagem_de_bloqueio(minutos),
        bloqueada_ate=bloqueada_ate.isoformat(),
        minutos_restantes=minutos,
    )


def aviso_de_restantes(restantes: int) -> str:
    """Frase para juntar à mensagem de erro a partir do 3º erro ("" antes disso)."""
    if TENTATIVAS_ATE_BLOQUEAR - restantes < AVISAR_A_PARTIR_DE:
        return ""
    if restantes == 1:
        return " Falta 1 tentativa antes de a entrada ser bloqueada por 15 minutos."
    return f" Faltam {restantes} tentativas antes de a entrada ser bloqueada por 15 minutos."


def abrir(db: Session, login: str, ip_hash: str) -> Tentativa:
    """Apaga as linhas vencidas, trava a linha do par (criando-a se preciso) e recusa com 423
    se o par está bloqueado. Durante o bloqueio, a tentativa não confere senha nem estende o
    prazo."""
    agora: datetime = db.scalars(select(func.now())).one()
    # Faxina: o hash do IP é dado pessoal e não serve para nada depois de vencido.
    db.execute(delete(EntradaTentativa).where(EntradaTentativa.expira_em < agora))
    db.execute(
        insert(EntradaTentativa)
        .values(login=login, ip_hash=ip_hash, expira_em=agora + JANELA)
        .on_conflict_do_nothing(index_elements=["login", "ip_hash"])
    )
    linha = db.scalars(
        select(EntradaTentativa)
        .where(EntradaTentativa.login == login, EntradaTentativa.ip_hash == ip_hash)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one()
    if linha.bloqueada_ate is not None and linha.bloqueada_ate > agora:
        raise erro_de_bloqueio(linha.bloqueada_ate, agora)
    return Tentativa(linha, agora)


def falhou(db: Session, tentativa: Tentativa, unidade_id: int | None) -> int:
    """Conta uma senha errada. Devolve quantas tentativas ainda restam; na 5ª, bloqueia e sobe
    o 423 (com o horário), registrando `unidade_bloqueada` no histórico."""
    linha, agora = tentativa.linha, tentativa.agora
    falhas = [f for f in linha.falhas_em if f > agora - JANELA] + [agora]
    if len(falhas) >= TENTATIVAS_ATE_BLOQUEAR:
        ate = agora + JANELA
        linha.falhas_em = []
        linha.bloqueada_ate = ate
        linha.expira_em = ate
        if unidade_id is not None:
            # Ação do sistema (unidade_id nulo): quem errou pode nem ser da unidade. O IP não
            # vai para o histórico.
            registrar(
                db,
                Acao.unidade_bloqueada,
                unidade_id=None,
                entidade="unidade",
                entidade_id=unidade_id,
            )
        db.flush()
        raise erro_de_bloqueio(ate, agora)
    linha.falhas_em = falhas
    linha.bloqueada_ate = None
    linha.expira_em = agora + JANELA
    db.flush()
    return TENTATIVAS_ATE_BLOQUEAR - len(falhas)


def acertou(db: Session, tentativa: Tentativa) -> None:
    """Senha certa: zera o contador daquele (login, IP)."""
    db.delete(tentativa.linha)
    db.flush()


def esquecer_login(db: Session, login: str) -> None:
    """Reset da unidade (H-08): tira os bloqueios e contadores daquele login."""
    db.execute(delete(EntradaTentativa).where(EntradaTentativa.login == login))


def bloqueada_ate(db: Session, login: str) -> datetime | None:
    """Até quando algum IP está bloqueado naquele login (para a ficha do admin)."""
    return db.scalar(
        select(func.max(EntradaTentativa.bloqueada_ate)).where(
            EntradaTentativa.login == login, EntradaTentativa.bloqueada_ate > func.now()
        )
    )
