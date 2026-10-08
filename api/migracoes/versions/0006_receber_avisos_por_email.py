"""Opção "Receber os avisos por e-mail" da unidade (ajustes do M2).

Revisão: 0006
Anterior: 0005
Criada em: 2026-10-07

Escrita à mão, no mesmo padrão da 0002 a 0005. Plano: `docs/superpowers/plans/m2-ajustes.md`;
decisão: resposta do Erick ao item 7 de `docs/superpowers/duvidas-m2.md`.

- `unidade.receber_avisos_email`: `true` (padrão) manda a cópia dos avisos para o e-mail
  cadastrado; `false` para as cópias. O e-mail continua cadastrado e o "esqueci a senha" não olha
  esta opção. As unidades que já existem ficam ligadas (é o que valia na 1.2.0).
- O `app` já tem UPDATE na tabela `unidade` inteira (0001); o grant é repetido só para deixar
  explícito que a coluna nova é alterada pela API.
"""

from collections.abc import Sequence

from alembic import context, op
from sqlalchemy import text

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _papel_app() -> str:
    """Mesmo cuidado da 0001 a 0005: o papel `app` precisa existir e entra como identificador."""
    nome = context.get_x_argument(as_dictionary=True).get("papel_app", "app")
    existe = (
        op.get_bind()
        .execute(text("select 1 from pg_roles where rolname = :n"), {"n": nome})
        .scalar()
    )
    if not existe:
        raise RuntimeError(
            f'O papel "{nome}" não existe no banco. Crie-o antes de migrar, como superusuário '
            f"ou dono do banco: CREATE ROLE {nome} LOGIN PASSWORD '<senha fora do repositório>';"
        )
    return '"' + nome.replace('"', '""') + '"'


RECEBER_AVISOS_EMAIL = """
alter table unidade
    add column receber_avisos_email boolean not null default true;
"""

PERMISSOES = """
grant select, update (receber_avisos_email) on unidade to {app};
"""


def upgrade() -> None:
    app = _papel_app()
    op.execute(RECEBER_AVISOS_EMAIL)
    op.execute(PERMISSOES.format(app=app))


def downgrade() -> None:
    # O grant de tabela da 0001 continua valendo; a coluna sai com o grant dela.
    op.execute("alter table unidade drop column receber_avisos_email;")
