"""Indicações de serviços: categorias, prestador, opinião e aviso à gestão.

Revisão: 0010
Anterior: 0009
Criada em: 2026-10-18

Escrita à mão, no mesmo padrão da 0002 a 0009. Spec:
`docs/superpowers/specs/2026-10-18-indicacoes-design.md`, seções 4 e 5.

As regras ficam aqui, não na API:
- **uma opinião por unidade e prestador**: `opiniao_servico_unica`;
- **telefone único entre todos os prestadores**, escondidos inclusive: `prestador_telefone_unico`
  (esconder não libera o número);
- **um aviso aberto por unidade e prestador**: o índice único parcial `aviso_servico_aberto`;
- o `app` não apaga prestador nem categoria.
"""

from collections.abc import Sequence

from alembic import context, op
from sqlalchemy import text

revision: str = "0010"
down_revision: str | Sequence[str] | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _papel_app() -> str:
    """Mesmo cuidado da 0001 a 0008: o papel `app` precisa existir e entra como identificador."""
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


TABELAS = """
-- Fixas, com a carga abaixo. A administração acrescenta e renomeia; nunca apaga.
create table categoria_servico (
    id         bigint generated always as identity primary key,
    nome       text not null constraint categoria_servico_nome_tamanho check (
                   char_length(nome) between 2 and 40 and nome = btrim(nome)),
    ordem      smallint not null,
    criada_em  timestamptz not null default now()
);
-- "Eletricista" e "eletricista" são a mesma.
create unique index categoria_servico_nome_unico on categoria_servico (lower(nome));

-- Quem foi indicado. Nasce com a primeira opinião (na mesma transação, pela API). Nunca é
-- apagado: escondido, sai da lista e o telefone continua ocupado.
create table prestador (
    id             bigint generated always as identity primary key,
    categoria_id   bigint not null references categoria_servico (id),
    nome           text not null constraint prestador_nome_tamanho check (
                       char_length(nome) between 2 and 80 and nome = btrim(nome)),
    -- Sem acento, minúsculo, espaços juntos: gravado pela API (`normalizar`).
    nome_busca     text not null constraint prestador_nome_busca check (
                       char_length(nome_busca) > 0),
    -- Só dígitos: DDD sem zero e 8 ou 9 dígitos; com 11, o terceiro é 9 (celular).
    telefone       text not null constraint prestador_telefone_formato check (
                       telefone ~ '^[1-9]{2}[0-9]{8,9}$'
                       and (char_length(telefone) = 10 or substr(telefone, 3, 1) = '9')),
    -- Sem o @.
    instagram      text constraint prestador_instagram_formato check (
                       instagram ~ '^[A-Za-z0-9._]{1,30}$'),
    -- Vira nulo em "apagar meus dados" e no reset: o próximo morador não herda o direito de
    -- corrigir.
    criado_por     bigint references unidade (id),
    criado_em      timestamptz not null default now(),
    editado_em     timestamptz,
    escondido_em   timestamptz,
    escondido_por  bigint references unidade (id),
    constraint prestador_telefone_unico unique (telefone)
);
create index prestador_categoria on prestador (categoria_id);

-- Recomendo ou não recomendo. Apagar é de verdade (a própria unidade, "apagar meus dados", o
-- reset); esconder é da gestão e trava a opinião.
create table opiniao_servico (
    id             bigint generated always as identity primary key,
    prestador_id   bigint not null references prestador (id),
    unidade_id     bigint not null references unidade (id),
    recomenda      boolean not null,
    comentario     text constraint opiniao_servico_comentario_tamanho check (
                       comentario is null or (char_length(btrim(comentario)) between 1 and 500
                       and char_length(comentario) <= 500)),
    criada_em      timestamptz not null default now(),
    editada_em     timestamptz,
    escondida_em   timestamptz,
    escondida_por  bigint references unidade (id),
    constraint opiniao_servico_unica unique (prestador_id, unidade_id)
);
-- O limite do dia conta por unidade e data.
create index opiniao_servico_unidade on opiniao_servico (unidade_id, criada_em);

-- "Tem algo errado aqui?": só a gestão vê, sem a placa de quem avisou.
create table aviso_servico (
    id                 bigint generated always as identity primary key,
    prestador_id       bigint not null references prestador (id),
    unidade_id         bigint not null references unidade (id),
    motivo             text constraint aviso_servico_motivo_tamanho check (
                           motivo is null or (char_length(btrim(motivo)) between 1 and 300
                           and char_length(motivo) <= 300)),
    criado_em          timestamptz not null default now(),
    resolvido_em       timestamptz,
    resolvido_por      bigint references unidade (id),
    -- E-mails do primeiro aviso reservados na cota do Gmail (`emails_nas_ultimas_24h`).
    emails_reservados  smallint not null default 0
);
create unique index aviso_servico_aberto on aviso_servico (prestador_id, unidade_id)
    where resolvido_em is null;
"""

# A mesma lista de `app.modelos.indicacoes.CATEGORIAS_INICIAIS` (congelada aqui; o teste
# `test_carga_da_migracao_igual_a_constante` confere). "Outros" fica sempre por último.
CARGA = """
insert into categoria_servico (nome, ordem) values
    ('Móveis planejados', 10),
    ('Ar-condicionado', 20),
    ('Cortinas e persianas', 30),
    ('Mudança', 40),
    ('Eletricista', 50),
    ('Encanador', 60),
    ('Pintura', 70),
    ('Gesso', 80),
    ('Vidraçaria e box', 90),
    ('Diarista', 100),
    ('Outros', 999);
"""

# Padrão da 0007 e da 0008: só as colunas que a API escreve. Nada de DELETE em prestador nem em
# categoria.
PERMISSOES = """
grant select, insert on categoria_servico, prestador, opiniao_servico, aviso_servico to {app};
grant update (nome) on categoria_servico to {app};
grant update (categoria_id, nome, nome_busca, telefone, instagram, criado_por, escondido_em,
              escondido_por) on prestador to {app};
grant update (recomenda, comentario, escondida_em, escondida_por), delete
    on opiniao_servico to {app};
grant update (resolvido_em, resolvido_por, emails_reservados), delete on aviso_servico to {app};
"""


def upgrade() -> None:
    app = _papel_app()
    op.execute(TABELAS)
    op.execute(CARGA)
    op.execute(PERMISSOES.format(app=app))


def downgrade() -> None:
    # As permissões saem com as tabelas.
    op.execute("drop table aviso_servico, opiniao_servico, prestador, categoria_servico;")
