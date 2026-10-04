"""Carga inicial do prédio (modelo de dados, seção 7).

Cria os 5 blocos, as 320 unidades (andares 0 a 7, posições 01 a 08, todas com a senha inicial
`mudar123` em Argon2id) e o papel `admin` na unidade indicada por `PORTAL_ADMIN_UNIDADE`.

Idempotente: só cria o que falta, então pode rodar de novo sem duplicar nada e sem trocar a
senha de quem já ativou a conta. A função não faz commit; quem chama decide.
"""

from dataclasses import dataclass

from argon2 import PasswordHasher
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modelos import Bloco, Historico, Papel, Unidade, UnidadePapel

BLOCOS = range(1, 6)
ANDARES = range(0, 8)  # 0 = térreo
POSICOES = range(1, 9)
SENHA_INICIAL = "mudar123"  # pública por decisão (ADR-0005): a troca é obrigatória no 1º acesso


class ErroCarga(RuntimeError):
    pass


@dataclass(frozen=True)
class ResumoCarga:
    blocos_criados: int
    unidades_criadas: int
    admin_concedido: bool


def numeros_planejados() -> list[str]:
    """`001`…`008`, `101`…`108`, …, `701`…`708`."""
    return [f"{andar}{posicao:02d}" for andar in ANDARES for posicao in POSICOES]


def logins_planejados() -> list[str]:
    return [f"{bloco}{numero}" for bloco in BLOCOS for numero in numeros_planejados()]


def _validar_admin(admin_login: str | None) -> str:
    login = (admin_login or "").strip()
    if not login:
        raise ErroCarga(
            "Defina PORTAL_ADMIN_UNIDADE com o login da unidade do administrador (ex.: 1101)."
        )
    if login not in logins_planejados():
        raise ErroCarga(
            f"PORTAL_ADMIN_UNIDADE={login!r} não é uma unidade do prédio "
            "(bloco 1 a 5 + andar 0 a 7 + posição 01 a 08, ex.: 1101)."
        )
    return login


def carregar(
    sessao: Session, admin_login: str | None, hasher: PasswordHasher | None = None
) -> ResumoCarga:
    admin = _validar_admin(admin_login)
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

    # Admin
    unidade_admin = sessao.scalars(select(Unidade.id).where(Unidade.login == admin)).one()
    tem_admin = sessao.scalar(
        select(UnidadePapel.id).where(
            UnidadePapel.unidade_id == unidade_admin,
            UnidadePapel.papel == Papel.admin,
            UnidadePapel.retirado_em.is_(None),
        )
    )
    if not tem_admin:
        sessao.add(UnidadePapel(unidade_id=unidade_admin, papel=Papel.admin))

    # Histórico (ação do sistema: unidade_id nulo)
    if blocos_criados or novas:
        sessao.add(
            Historico(
                acao="carga_inicial",
                detalhes={"blocos": blocos_criados, "unidades": len(novas)},
            )
        )
    if not tem_admin:
        sessao.add(
            Historico(
                acao="papel_concedido",
                entidade="unidade",
                entidade_id=unidade_admin,
                detalhes={"papel": Papel.admin.value},
            )
        )
    sessao.flush()
    return ResumoCarga(
        blocos_criados=blocos_criados,
        unidades_criadas=len(novas),
        admin_concedido=not tem_admin,
    )
