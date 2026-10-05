"""Sessão por cookie (ADR-0005; spec do M1, seção 3.1).

- O aparelho guarda um token aleatório de 32 bytes no cookie; o banco guarda só o SHA-256 dele.
- Cookie `__Host-sessao`: `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/`, sem `Domain`. O
  prefixo `__Host-` faz o navegador recusar o cookie se algum desses atributos faltar.
- Vale 180 dias desde o último uso, e só se foi aberta depois da última troca de senha da
  unidade (`unidade.senha_trocada_em`, data do banco): quem entrou com `mudar123` antes do
  morador perde o acesso quando ele conclui o primeiro acesso.
- Trocar a senha (primeiro acesso, "trocar a senha") usa `trocar_senha_e_sessao`: encerra todos
  os aparelhos e abre uma sessão nova só para quem trocou.
- O último uso é regravado no máximo uma vez por hora, para não
  escrever no banco a cada requisição.

Nada aqui faz commit: quem chama decide.
"""

import hashlib
import re
import secrets
from datetime import timedelta

from fastapi import Response
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.modelos import Sessao, Unidade
from app.seguranca.senhas import gerar_hash

NOME_COOKIE = "__Host-sessao"
VALIDADE = timedelta(days=180)
RENOVAR_APOS = timedelta(hours=1)


def hash_do_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def criar_sessao(db: Session, unidade_id: int, user_agent: str | None) -> str:
    """Abre uma sessão para a unidade e devolve o token (que só o cookie conhece)."""
    token = secrets.token_urlsafe(32)
    db.add(
        Sessao(
            unidade_id=unidade_id,
            token_hash=hash_do_token(token),
            aparelho=descrever_aparelho(user_agent),
        )
    )
    db.flush()
    return token


def buscar_sessao(db: Session, token: str | None) -> Sessao | None:
    """A sessão do token, se ainda vale: não encerrada, usada nos últimos 180 dias, aberta depois
    da última troca de senha e de uma unidade ativa."""
    if not token:
        return None
    return db.scalars(
        select(Sessao)
        .join(Unidade, Unidade.id == Sessao.unidade_id)
        .where(
            Sessao.token_hash == hash_do_token(token),
            Sessao.encerrada_em.is_(None),
            Sessao.ultimo_uso_em > func.now() - VALIDADE,
            Sessao.criada_em >= Unidade.senha_trocada_em,
            Unidade.ativa.is_(True),
        )
    ).one_or_none()


def renovar(db: Session, sessao: Sessao) -> bool:
    """Regrava o último uso se faz mais de uma hora. Devolve `True` se regravou (e então o
    cookie também deve ser regravado, para os 180 dias contarem de novo)."""
    renovada = db.execute(
        update(Sessao)
        .where(Sessao.id == sessao.id, Sessao.ultimo_uso_em < func.now() - RENOVAR_APOS)
        .values(ultimo_uso_em=func.now())
    )
    return bool(renovada.rowcount)  # type: ignore[attr-defined]


def encerrar_sessao(db: Session, sessao_id: int) -> None:
    db.execute(
        update(Sessao)
        .where(Sessao.id == sessao_id, Sessao.encerrada_em.is_(None))
        .values(encerrada_em=func.now())
    )


def encerrar_todas(db: Session, unidade_id: int, exceto: int | None = None) -> int:
    """Desconecta os aparelhos da unidade (reset, apagar dados). Devolve quantos."""
    filtros = [Sessao.unidade_id == unidade_id, Sessao.encerrada_em.is_(None)]
    if exceto is not None:
        filtros.append(Sessao.id != exceto)
    resultado = db.execute(update(Sessao).where(*filtros).values(encerrada_em=func.now()))
    return resultado.rowcount  # type: ignore[attr-defined]


def trocar_senha_e_sessao(
    db: Session, unidade_id: int, senha_nova: str, user_agent: str | None
) -> str:
    """Grava a senha nova, encerra **todas** as sessões da unidade e abre uma nova para quem
    trocou. Devolve o token: a rota grava o cookie com `gravar_cookie`.

    Usar no primeiro acesso (H-01) e em "trocar a senha" (H-06). Mesmo sem isto, o banco já
    invalida as sessões antigas (`senha_trocada_em`); aqui elas também ficam marcadas como
    encerradas, para sumirem da lista de aparelhos.
    """
    unidade = db.get_one(Unidade, unidade_id)
    unidade.senha_hash = gerar_hash(senha_nova)
    db.flush()
    encerrar_todas(db, unidade_id)
    return criar_sessao(db, unidade_id, user_agent)


def gravar_cookie(resposta: Response, token: str) -> None:
    resposta.set_cookie(
        NOME_COOKIE,
        token,
        max_age=int(VALIDADE.total_seconds()),
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )


def apagar_cookie(resposta: Response) -> None:
    # Mesmos atributos da gravação: sem eles o navegador recusa (prefixo __Host-).
    resposta.delete_cookie(NOME_COOKIE, path="/", secure=True, httponly=True, samesite="lax")


# --- descrição do aparelho (H-06: "Android · Chrome") ---------------------------------------

_SISTEMAS = [
    ("Android", r"Android"),
    ("iPhone", r"iPhone"),
    ("iPad", r"iPad"),
    ("Windows", r"Windows"),
    ("Mac", r"Macintosh|Mac OS X"),
    ("Linux", r"Linux|X11"),
]
_NAVEGADORES = [
    ("Edge", r"Edg(e|A|iOS)?/"),
    ("Samsung Internet", r"SamsungBrowser/"),
    ("Opera", r"OPR/|Opera"),
    ("Firefox", r"Firefox/|FxiOS/"),
    ("Chrome", r"Chrome/|CriOS/"),
    ("Safari", r"Safari/|Version/"),
]


def descrever_aparelho(user_agent: str | None) -> str:
    """Descrição curta para a unidade reconhecer o aparelho. Nada além de sistema e navegador
    (o User-Agent inteiro identifica demais e não tem uso)."""
    agente = user_agent or ""
    sistema = next((nome for nome, padrao in _SISTEMAS if re.search(padrao, agente)), None)
    navegador = next((nome for nome, padrao in _NAVEGADORES if re.search(padrao, agente)), None)
    if not sistema or not navegador:
        return "Aparelho desconhecido"
    return f"{sistema} · {navegador}"
