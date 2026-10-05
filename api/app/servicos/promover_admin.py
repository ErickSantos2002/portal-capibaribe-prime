"""Primeiro administrador do Portal (spec do M1, seção 2.5).

A carga inicial não dá papel nenhum. Em produção: deploy → o Erick faz o primeiro acesso na
unidade dele (senha própria, fora de `mudar123`) → roda-se o comando `promover_admin` com o
login dela. A unidade real nunca aparece no repositório: vai só na linha de comando.

Depois disso, novos admins e a Comissão são dados pela tela de administração (H-09).
Idempotente. Não faz commit.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modelos import Papel, Unidade, UnidadePapel
from app.servicos.erros import ErroDoPortal
from app.servicos.historico import Acao, registrar


class ErroPromocao(ErroDoPortal):
    pass


def promover_admin(db: Session, login: str) -> bool:
    """Dá o papel `admin` à unidade. Devolve `False` se ela já era admin."""
    unidade = db.scalars(select(Unidade).where(Unidade.login == login.strip())).one_or_none()
    if unidade is None or not unidade.ativa:
        raise ErroPromocao(f"A unidade {login!r} não existe ou está desativada.")
    if unidade.ativada_em is None or unidade.precisa_trocar_senha:
        raise ErroPromocao(
            f"A unidade {login} ainda não fez o primeiro acesso. Entre com ela, troque a senha "
            "e rode o comando de novo."
        )
    ja_e = db.scalar(
        select(UnidadePapel.id).where(
            UnidadePapel.unidade_id == unidade.id,
            UnidadePapel.papel == Papel.admin,
            UnidadePapel.retirado_em.is_(None),
        )
    )
    if ja_e:
        return False
    db.add(UnidadePapel(unidade_id=unidade.id, papel=Papel.admin))
    registrar(
        db,
        Acao.papel_concedido,
        unidade_id=None,
        entidade="unidade",
        entidade_id=unidade.id,
        detalhes={"papel": Papel.admin.value, "origem": "promover_admin"},
    )
    return True
