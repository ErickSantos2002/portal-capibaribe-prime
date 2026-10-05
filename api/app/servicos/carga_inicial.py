"""Carga inicial do prédio (modelo de dados, seção 7).

Cria os 5 blocos e as 320 unidades (andares 0 a 7, posições 01 a 08, todas com a senha inicial
`mudar123` em Argon2id). **Não dá papel nenhum** (revisão do M1): uma unidade com `mudar123` e
poder de administrador seria tomada por quem conhece o padrão. O administrador nasce depois, com
`python -m app.comandos.promover_admin <login>`, numa unidade que já fez o primeiro acesso.

Idempotente: só cria o que falta, então pode rodar de novo sem duplicar nada e sem trocar a
senha de quem já ativou a conta. A função não faz commit; quem chama decide.
"""

from dataclasses import dataclass

from argon2 import PasswordHasher
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modelos import Bloco, Historico, Unidade

BLOCOS = range(1, 6)
ANDARES = range(0, 8)  # 0 = térreo
POSICOES = range(1, 9)
SENHA_INICIAL = "mudar123"  # pública por decisão (ADR-0005): a troca é obrigatória no 1º acesso


@dataclass(frozen=True)
class ResumoCarga:
    blocos_criados: int
    unidades_criadas: int


def numeros_planejados() -> list[str]:
    """`001`…`008`, `101`…`108`, …, `701`…`708`."""
    return [f"{andar}{posicao:02d}" for andar in ANDARES for posicao in POSICOES]


def logins_planejados() -> list[str]:
    return [f"{bloco}{numero}" for bloco in BLOCOS for numero in numeros_planejados()]


def carregar(sessao: Session, hasher: PasswordHasher | None = None) -> ResumoCarga:
    hasher = hasher or PasswordHasher()

    # Blocos
    blocos: dict[int, int] = dict(sessao.execute(select(Bloco.numero, Bloco.id)).all())
    blocos_criados = 0
    for numero in BLOCOS:
        if numero not in blocos:
            bloco = Bloco(numero=numero, nome=f"Bloco {numero}")
            sessao.add(bloco)
            sessao.flush()
            blocos[numero] = bloco.id
            blocos_criados += 1

    # Unidades: o login é calculado pelo banco (trigger), aqui só se compara.
    existentes = set(sessao.scalars(select(Unidade.login)).all())
    novas = [
        Unidade(
            bloco_id=blocos[bloco],
            numero=numero,
            andar=int(numero[0]),
            # Um hash por unidade: cada um com o próprio sal.
            senha_hash=hasher.hash(SENHA_INICIAL),
            precisa_trocar_senha=True,
        )
        for bloco in BLOCOS
        for numero in numeros_planejados()
        if f"{bloco}{numero}" not in existentes
    ]
    sessao.add_all(novas)
    sessao.flush()

    # Histórico (ação do sistema: unidade_id nulo)
    if blocos_criados or novas:
        sessao.add(
            Historico(
                acao="carga_inicial",
                detalhes={"blocos": blocos_criados, "unidades": len(novas)},
            )
        )
    sessao.flush()
    return ResumoCarga(
        blocos_criados=blocos_criados,
        unidades_criadas=len(novas),
    )
