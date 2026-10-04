"""Dados fictícios para desenvolvimento e teste (RNF-16), separados da carga real.

Ativa parte das unidades com nomes inventados, celulares `(81) 90000-xxxx` e e-mails em
`@example.com`, e dá o papel de Comissão a duas delas. Determinístico (mesma semente) e
idempotente. Só roda com `PORTAL_AMBIENTE` igual a `local` ou `teste`: em produção, recusa.

Em desenvolvimento as unidades fictícias entram com a senha inicial, já sem a troca obrigatória.
"""

import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modelos import Historico, Papel, Unidade, UnidadePapel

AMBIENTES_PERMITIDOS = {"local", "teste"}
SEMENTE = 2026
PROPORCAO_ATIVADA = 0.4  # meta de adesão de 3 meses (roadmap, seção 6)

NOMES = [
    "Ana", "Bruno", "Carla", "Diego", "Elisa", "Fábio", "Gabriela", "Heitor", "Iara", "João",
    "Karina", "Lucas", "Marina", "Nilton", "Olga", "Paulo", "Quitéria", "Rafael", "Sofia",
    "Tiago", "Úrsula", "Vítor", "Wanda", "Yasmin", "Zeca",
]  # fmt: skip
SOBRENOMES = [
    "Albuquerque", "Barbosa", "Cavalcanti", "Duarte", "Esteves", "Ferraz", "Guedes", "Holanda",
    "Lacerda", "Moura", "Nóbrega", "Pessoa", "Queiroz", "Rangel", "Siqueira", "Tavares",
]  # fmt: skip


class ErroAmbiente(RuntimeError):
    pass


def _sem_acento(texto: str) -> str:
    return texto.lower().translate(str.maketrans("áéíóúâêôãõç", "aeiouaeoaoc"))


def preencher_ficticios(sessao: Session, ambiente: str | None) -> int:
    """Devolve quantas unidades foram ativadas nesta chamada. Não faz commit."""
    if ambiente not in AMBIENTES_PERMITIDOS:
        raise ErroAmbiente(
            "Dados fictícios só rodam com PORTAL_AMBIENTE=local ou PORTAL_AMBIENTE=teste "
            f"(recebido: {ambiente!r}). Nunca em produção."
        )
    unidades = sessao.scalars(select(Unidade).order_by(Unidade.login)).all()
    if not unidades:
        raise ErroAmbiente("Nenhuma unidade no banco: rode a carga inicial antes.")

    sorteio = random.Random(SEMENTE)
    escolhidas = sorted(
        sorteio.sample(range(len(unidades)), int(len(unidades) * PROPORCAO_ATIVADA))
    )
    agora = datetime.now(UTC)
    ativadas = 0
    for posicao, indice in enumerate(escolhidas):
        unidade = unidades[indice]
        nome = f"{sorteio.choice(NOMES)} {sorteio.choice(SOBRENOMES)}"
        dias = sorteio.randint(1, 90)
        com_email = sorteio.random() < 0.5
        if unidade.ativada_em is not None:
            continue  # já preenchida numa rodada anterior: não mexe
        unidade.responsavel_nome = f"{nome} (fictício)"
        unidade.celular = f"(81) 90000-{posicao:04d}"
        unidade.email = (
            f"{_sem_acento(nome).replace(' ', '.')}.{unidade.login}@example.com"
            if com_email
            else None
        )
        unidade.precisa_trocar_senha = False
        unidade.ativada_em = agora - timedelta(days=dias)
        ativadas += 1

    # Comissão fictícia: as duas primeiras unidades sorteadas.
    for indice in escolhidas[:2]:
        unidade = unidades[indice]
        tem = sessao.scalar(
            select(UnidadePapel.id).where(
                UnidadePapel.unidade_id == unidade.id,
                UnidadePapel.papel == Papel.comissao,
                UnidadePapel.retirado_em.is_(None),
            )
        )
        if not tem:
            sessao.add(UnidadePapel(unidade_id=unidade.id, papel=Papel.comissao))

    if ativadas:
        sessao.add(Historico(acao="dados_ficticios", detalhes={"unidades": ativadas}))
    sessao.flush()
    return ativadas
