"""Dados fictícios para desenvolvimento e teste (RNF-16), separados da carga real.

Ativa parte das unidades com nomes inventados, celulares `8190000xxxx` e e-mails em
`@example.com`; em local e teste, dá o papel de admin a uma e o de Comissão a duas.
Determinístico (mesma semente) e idempotente. Só roda com `PORTAL_AMBIENTE` igual a `local`,
`teste` ou `previa`; em produção, recusa.

Em desenvolvimento as unidades fictícias entram com a senha inicial, já sem a troca obrigatória.
"""

import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modelos import Historico, Papel, Unidade, UnidadePapel

# `previa`: o branch do Neon só de estrutura usado pelas prévias da Vercel (spec do M1, seção 6).
AMBIENTES_PERMITIDOS = {"local", "teste", "previa"}
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
            "Dados fictícios só rodam com PORTAL_AMBIENTE=local, teste ou previa "
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
        # Só dígitos, como o banco exige (migração 0002); a tela formata.
        unidade.celular = f"8190000{posicao:04d}"
        unidade.email = (
            f"{_sem_acento(nome).replace(' ', '.')}.{unidade.login}@example.com"
            if com_email
            else None
        )
        unidade.precisa_trocar_senha = False
        unidade.ativada_em = agora - timedelta(days=dias)
        ativadas += 1

    # Papéis fictícios, só em local e teste: a primeira unidade sorteada é admin e as duas
    # seguintes são da Comissão (todas já ativadas acima). Na prévia, nenhum papel: ela fica na
    # internet (atrás da proteção da Vercel) e quem revisa faz o primeiro acesso e roda
    # `promover_admin`, como em produção (spec do M1, seção 6).
    if ambiente != "previa":
        sessao.flush()
        papeis = [Papel.admin, Papel.comissao, Papel.comissao]
        for indice, papel in zip(escolhidas[:3], papeis, strict=True):
            unidade = unidades[indice]
            tem = sessao.scalar(
                select(UnidadePapel.id).where(
                    UnidadePapel.unidade_id == unidade.id,
                    UnidadePapel.papel == papel,
                    UnidadePapel.retirado_em.is_(None),
                )
            )
            if not tem:
                sessao.add(UnidadePapel(unidade_id=unidade.id, papel=papel))

    if ativadas:
        sessao.add(Historico(acao="dados_ficticios", detalhes={"unidades": ativadas}))
    sessao.flush()
    return ativadas
