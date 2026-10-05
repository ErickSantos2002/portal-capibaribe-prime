"""Regras do épico A · Acesso (H-01, H-02, H-03, H-06). Pertence ao épico A.

Spec: `docs/superpowers/specs/m1-acesso.md`. Nada aqui faz commit: a rota decide (mesma regra das
peças comuns), para a ação e o registro no histórico irem juntos na mesma transação.
"""

import math
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.erros_api import ErroApi
from app.esquemas.acesso import (
    Aparelho,
    DadosDaUnidade,
    MinhaUnidade,
    PrimeiroAcesso,
    TrocarSenha,
)
from app.esquemas.comum import Eu, UnidadeRef
from app.modelos import Papel, Sessao, Unidade, UnidadePapel
from app.seguranca.dependencias import PAPEIS_DE_GESTAO, Logado
from app.seguranca.senhas import SENHA_INICIAL, conferir_sem_unidade, gerar_hash, senha_confere
from app.seguranca.sessoes import (
    VALIDADE,
    criar_sessao,
    encerrar_sessao,
    trocar_senha_e_sessao,
)
from app.servicos.historico import Acao, registrar

TENTATIVAS_ATE_BLOQUEAR = 5
TEMPO_DE_BLOQUEIO = timedelta(minutes=15)

MSG_CREDENCIAIS = "Bloco, apartamento ou senha incorretos. Confira e tente de novo."


class ErroEntrar(ErroApi):
    """Recusa de `entrar` que ainda precisa de commit: a tentativa errada e o bloqueio ficam
    gravados mesmo com a resposta de erro. A rota faz o commit e então levanta."""


def papeis_em_vigor(db: Session, unidade_id: int) -> list[Papel]:
    return sorted(
        db.scalars(
            select(UnidadePapel.papel).where(
                UnidadePapel.unidade_id == unidade_id, UnidadePapel.retirado_em.is_(None)
            )
        )
    )


def eu_da_unidade(db: Session, unidade: Unidade) -> Eu:
    papeis = papeis_em_vigor(db, unidade.id)
    return Eu(
        unidade=UnidadeRef.de_login(unidade.login),
        papeis=papeis,
        gestao=bool(PAPEIS_DE_GESTAO.intersection(papeis)),
        admin=Papel.admin in papeis,
        precisa_trocar_senha=unidade.precisa_trocar_senha,
    )


def _mensagem_de_bloqueio(minutos: int) -> str:
    tempo = "1 minuto" if minutos == 1 else f"{minutos} minutos"
    return (
        f"Entrada bloqueada por {tempo} depois de várias senhas erradas. Se não foi você, "
        "avise a administração do Portal no grupo do WhatsApp."
    )


def _erro_bloqueio(bloqueada_ate: datetime, agora: datetime) -> ErroEntrar:
    minutos = max(1, math.ceil((bloqueada_ate - agora).total_seconds() / 60))
    return ErroEntrar(
        423,
        "unidade_bloqueada",
        _mensagem_de_bloqueio(minutos),
        bloqueada_ate=bloqueada_ate.isoformat(),
        minutos_restantes=minutos,
    )


def entrar(db: Session, login: str, senha: str, user_agent: str | None) -> tuple[Eu, str]:
    """Confere login e senha (H-02) com o bloqueio por tentativas (H-03).

    Devolve o `Eu` e o token da sessão nova. Recusa com `ErroEntrar` (401 ou 423); quem chama
    faz commit antes de levantar, para a tentativa contar.
    """
    # A linha fica travada até o commit: tentativas ao mesmo tempo contam uma a uma.
    unidade = db.scalars(
        select(Unidade).where(Unidade.login == login, Unidade.ativa.is_(True)).with_for_update()
    ).one_or_none()
    if unidade is None:
        conferir_sem_unidade(senha)
        raise ErroEntrar(401, "credenciais_invalidas", MSG_CREDENCIAIS)

    agora: datetime = db.scalar(select(func.now()))  # type: ignore[assignment]
    if unidade.bloqueada_ate is not None and unidade.bloqueada_ate > agora:
        raise _erro_bloqueio(unidade.bloqueada_ate, agora)

    if not senha_confere(unidade.senha_hash, senha):
        unidade.tentativas_falhas += 1
        if unidade.tentativas_falhas >= TENTATIVAS_ATE_BLOQUEAR:
            unidade.tentativas_falhas = 0
            unidade.bloqueada_ate = agora + TEMPO_DE_BLOQUEIO
            # Ação do sistema (unidade_id nulo): quem errou pode nem ser da unidade.
            registrar(
                db,
                Acao.unidade_bloqueada,
                unidade_id=None,
                entidade="unidade",
                entidade_id=unidade.id,
            )
        db.flush()
        raise ErroEntrar(401, "credenciais_invalidas", MSG_CREDENCIAIS)

    unidade.tentativas_falhas = 0
    unidade.bloqueada_ate = None
    token = criar_sessao(db, unidade.id, user_agent)
    return eu_da_unidade(db, unidade), token


def concluir_primeiro_acesso(
    db: Session, unidade_id: int, dados: PrimeiroAcesso, user_agent: str | None
) -> tuple[Eu, str]:
    """H-01: senha própria e contatos; a unidade passa a "ativada".

    Encerra todas as sessões (inclusive a de quem entrou com `mudar123` antes do morador) e abre
    uma nova para quem concluiu. Devolve o `Eu` liberado e o token novo.
    """
    unidade = db.get_one(Unidade, unidade_id, with_for_update=True)
    if not unidade.precisa_trocar_senha:
        raise ErroApi(
            409, "primeiro_acesso_ja_feito", "O primeiro acesso deste apartamento já foi feito."
        )
    unidade.responsavel_nome = dados.responsavel_nome
    unidade.celular = dados.celular
    unidade.email = dados.email
    unidade.precisa_trocar_senha = False
    unidade.ativada_em = db.scalars(select(func.now())).one()
    token = trocar_senha_e_sessao(db, unidade_id, dados.senha_nova, user_agent)
    registrar(
        db, Acao.primeiro_acesso, unidade_id=unidade_id, entidade="unidade", entidade_id=unidade_id
    )
    return eu_da_unidade(db, unidade), token


# --- Minha unidade (H-06) -------------------------------------------------------------------------


def _aparelhos(db: Session, logado: Logado) -> list[Aparelho]:
    """Sessões em vigor da unidade, pelas mesmas regras de `buscar_sessao`: não encerradas,
    usadas nos últimos 180 dias e abertas depois da última troca de senha."""
    sessoes = db.scalars(
        select(Sessao)
        .join(Unidade, Unidade.id == Sessao.unidade_id)
        .where(
            Sessao.unidade_id == logado.unidade_id,
            Sessao.encerrada_em.is_(None),
            Sessao.ultimo_uso_em > func.now() - VALIDADE,
            Sessao.criada_em >= Unidade.senha_trocada_em,
        )
        .order_by(Sessao.ultimo_uso_em.desc(), Sessao.id.desc())
    )
    return [
        Aparelho(
            id=s.id,
            descricao=s.aparelho or "Aparelho desconhecido",
            criada_em=s.criada_em,
            ultimo_uso_em=s.ultimo_uso_em,
            este_aparelho=s.id == logado.sessao_id,
        )
        for s in sessoes
    ]


def ver_minha_unidade(db: Session, logado: Logado) -> MinhaUnidade:
    unidade = db.get_one(Unidade, logado.unidade_id)
    return MinhaUnidade(
        unidade=UnidadeRef.de_login(unidade.login),
        responsavel_nome=unidade.responsavel_nome,
        celular=unidade.celular,
        email=unidade.email,
        papeis=papeis_em_vigor(db, unidade.id),
        ativada_em=unidade.ativada_em,
        aparelhos=_aparelhos(db, logado),
    )


def salvar_dados(db: Session, logado: Logado, dados: DadosDaUnidade) -> None:
    unidade = db.get_one(Unidade, logado.unidade_id)
    unidade.responsavel_nome = dados.responsavel_nome
    unidade.celular = dados.celular
    unidade.email = dados.email
    db.flush()


def trocar_senha(db: Session, logado: Logado, dados: TrocarSenha, user_agent: str | None) -> str:
    """Pede a senha atual; grava a nova, desconecta os outros aparelhos e devolve o token novo
    deste (dúvida 8 do M1: na conta compartilhada, é o jeito de tirar quem não devia estar lá)."""
    unidade = db.get_one(Unidade, logado.unidade_id, with_for_update=True)
    if not senha_confere(unidade.senha_hash, dados.senha_atual):
        raise ErroApi(400, "senha_atual_incorreta", "A senha atual não confere.")
    token = trocar_senha_e_sessao(db, unidade.id, dados.senha_nova, user_agent)
    registrar(
        db, Acao.senha_trocada, unidade_id=unidade.id, entidade="unidade", entidade_id=unidade.id
    )
    return token


def desconectar_aparelho(db: Session, logado: Logado, sessao_id: int) -> None:
    """Só sessão em vigor da própria unidade. De outra unidade, a mesma resposta de inexistente
    (não revela que existe)."""
    if sessao_id not in {a.id for a in _aparelhos(db, logado)}:
        raise ErroApi(404, "aparelho_nao_encontrado", "Este aparelho já não está conectado.")
    encerrar_sessao(db, sessao_id)
    registrar(
        db,
        Acao.aparelho_desconectado,
        unidade_id=logado.unidade_id,
        entidade="sessao",
        entidade_id=sessao_id,
    )


def apagar_dados(db: Session, logado: Logado) -> None:
    """H-06 / RF-08: apaga os contatos, volta a senha para `mudar123` e a unidade a "não
    ativada". As linhas de sessão são apagadas (a descrição do aparelho é dado pessoal); votos e
    leituras ficam, porque são da unidade."""
    unidade = db.get_one(Unidade, logado.unidade_id, with_for_update=True)
    if papeis_em_vigor(db, unidade.id):
        raise ErroApi(
            409,
            "unidade_com_papel_de_gestao",
            "Este apartamento tem papel de gestão. Peça à administração do Portal para retirar "
            "o papel antes.",
        )
    unidade.responsavel_nome = None
    unidade.celular = None
    unidade.email = None
    unidade.ativada_em = None
    unidade.precisa_trocar_senha = True
    unidade.senha_hash = gerar_hash(SENHA_INICIAL)
    unidade.tentativas_falhas = 0
    db.flush()
    db.execute(delete(Sessao).where(Sessao.unidade_id == unidade.id))
    registrar(
        db, Acao.dados_apagados, unidade_id=unidade.id, entidade="unidade", entidade_id=unidade.id
    )
