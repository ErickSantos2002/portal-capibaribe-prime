"""Regras do épico A · Acesso (H-01, H-02, H-03, H-06). Pertence ao épico A.

Spec: `docs/superpowers/specs/m1-acesso.md`. Nada aqui faz commit: a rota decide (mesma regra das
peças comuns), para a ação e o registro no histórico irem juntos na mesma transação.

O bloqueio por senhas erradas é por (login, IP) e mora em `app/servicos/tentativas.py`
(revisão do M1, C2).
"""

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
from app.modelos import InscricaoPush, Papel, Sessao, Unidade, UnidadePapel
from app.seguranca.dependencias import PAPEIS_DE_GESTAO, Logado
from app.seguranca.senhas import SENHA_INICIAL, conferir_sem_unidade, gerar_hash, senha_confere
from app.seguranca.sessoes import (
    VALIDADE,
    criar_sessao,
    encerrar_sessao,
    trocar_senha_e_sessao,
)
from app.servicos import tentativas
from app.servicos.historico import Acao, registrar
from app.servicos.tentativas import ErroQueConta

MSG_CREDENCIAIS = "Bloco, apartamento ou senha incorretos. Confira e tente de novo."
MSG_SENHA_ATUAL = "A senha atual não confere."

# Recusa de `entrar` (e de "apagar meus dados") que precisa de commit antes de levantar.
ErroEntrar = ErroQueConta


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


def _credenciais_invalidas(restantes: int) -> ErroQueConta:
    return ErroQueConta(
        401,
        "credenciais_invalidas",
        MSG_CREDENCIAIS + tentativas.aviso_de_restantes(restantes),
        tentativas_restantes=restantes,
    )


def entrar(
    db: Session, login: str, senha: str, ip_hash: str, user_agent: str | None
) -> tuple[Eu, str]:
    """Confere login e senha (H-02) com o bloqueio por (login, IP) (H-03).

    Devolve o `Eu` e o token da sessão nova. Recusa com `ErroQueConta` (401 ou 423); quem chama
    faz commit antes de levantar, para a tentativa contar. Login inexistente ou desativado conta
    e bloqueia como os outros: a resposta é a mesma.
    """
    # Trava o par (login, IP): tentativas ao mesmo tempo contam uma a uma.
    tentativa = tentativas.abrir(db, login, ip_hash)
    unidade = db.scalars(
        select(Unidade).where(Unidade.login == login, Unidade.ativa.is_(True))
    ).one_or_none()
    if unidade is None:
        conferir_sem_unidade(senha)
        raise _credenciais_invalidas(tentativas.falhou(db, tentativa, None))
    if not senha_confere(unidade.senha_hash, senha):
        raise _credenciais_invalidas(tentativas.falhou(db, tentativa, unidade.id))
    tentativas.acertou(db, tentativa)
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
    inscrita = select(InscricaoPush.sessao_id).where(InscricaoPush.sessao_id == Sessao.id).exists()
    sessoes = db.execute(
        select(Sessao, inscrita)
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
            notificacoes=notificacoes,
        )
        for s, notificacoes in sessoes
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
        raise ErroApi(400, "senha_atual_incorreta", MSG_SENHA_ATUAL)
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


def apagar_dados(db: Session, logado: Logado, senha: str, ip_hash: str) -> None:
    """H-06 / RF-08: apaga os contatos, volta a senha para `mudar123` e a unidade a "não
    ativada". As linhas de sessão são apagadas (a descrição do aparelho é dado pessoal); votos e
    leituras ficam, porque são da unidade.

    Pede a senha atual (revisão do M1, C1): sem ela, uma sessão esquecida num aparelho bastava
    para tomar a conta (apagar → `mudar123` → primeiro acesso). Senha errada conta para o
    bloqueio daquele IP (`ErroQueConta`: a rota faz commit antes de responder).
    """
    unidade = db.get_one(Unidade, logado.unidade_id, with_for_update=True)
    tentativa = tentativas.abrir(db, logado.login, ip_hash)
    if not senha_confere(unidade.senha_hash, senha):
        restantes = tentativas.falhou(db, tentativa, unidade.id)
        raise ErroQueConta(
            400,
            "senha_atual_incorreta",
            MSG_SENHA_ATUAL + tentativas.aviso_de_restantes(restantes),
            campos=[{"campo": "senha", "mensagem": MSG_SENHA_ATUAL}],
            tentativas_restantes=restantes,
        )
    tentativas.acertou(db, tentativa)
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
    db.flush()
    db.execute(delete(Sessao).where(Sessao.unidade_id == unidade.id))
    registrar(
        db, Acao.dados_apagados, unidade_id=unidade.id, entidade="unidade", entidade_id=unidade.id
    )
