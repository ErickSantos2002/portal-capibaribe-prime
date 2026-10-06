"""Categoria e evento do aviso, na versão (avisos com formatação, categoria e evento).

Revisão: 0004
Anterior: 0003
Criada em: 2026-10-06

Escrita à mão, no mesmo padrão da 0002/0003. Spec:
`docs/superpowers/specs/2026-10-06-avisos-visual-design.md`, seção 3.2.

- `aviso_versao.categoria`: `geral` (padrão), `obra`, `reuniao`, `financeiro` ou `urgente`. Fica
  na versão, não no aviso: corrigir pode mudar a categoria, e o "ver como era antes" mostra a
  antiga. As linhas que já existem ficam `geral`.
- `aviso_versao.evento_quando` e `evento_onde`: o "Quando / Onde" do aviso que é um evento.
  Local é opcional; local sem data não existe (evento sem data não é evento). O local tem o mesmo
  limite do título (1 a 120 letras, sem espaço só).
- O texto continua em `aviso_versao.texto`, agora com as marcas do Markdown restrito; o banco não
  muda nada nele (o renderizador é da tela).
- O `app` continua sem UPDATE em `aviso_versao` (correção é versão nova); o grant de `select,
  insert` da 0002 cobre as colunas novas e é repetido aqui só para deixar isso explícito.
- A trigger de versão da 0003 (aviso arquivado não recebe versão) não muda.
"""

from collections.abc import Sequence

from alembic import context, op
from sqlalchemy import text

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _papel_app() -> str:
    """Mesmo cuidado da 0001 a 0003: o papel `app` precisa existir e entra como identificador."""
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


CATEGORIA_E_EVENTO = """
alter table aviso_versao
    add column categoria text not null default 'geral'
        constraint aviso_versao_categoria check (
            categoria in ('geral', 'obra', 'reuniao', 'financeiro', 'urgente')),
    add column evento_quando timestamptz,
    add column evento_onde text
        constraint aviso_versao_evento_onde_tamanho check (
            char_length(btrim(evento_onde)) between 1 and 120
            and char_length(evento_onde) <= 120),
    add constraint aviso_versao_evento_completo check (
        evento_onde is null or evento_quando is not null);
"""

PERMISSOES = """
grant select, insert on aviso_versao to {app};
"""


def upgrade() -> None:
    app = _papel_app()
    op.execute(CATEGORIA_E_EVENTO)
    op.execute(PERMISSOES.format(app=app))


def downgrade() -> None:
    # O grant de select/insert é da 0002 e continua valendo; só as colunas saem.
    op.execute(
        """
        alter table aviso_versao
            drop constraint aviso_versao_evento_completo,
            drop column evento_onde,
            drop column evento_quando,
            drop column categoria;
        """
    )
