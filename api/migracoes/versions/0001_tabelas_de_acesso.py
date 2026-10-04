"""Tabelas de acesso (bloco, unidade, unidade_papel, sessao, historico, erro) e permissões.

Revisão: 0001
Anterior: nenhuma
Criada em: 2026-10-04

Escrita à mão, em SQL, porque o que importa aqui (trigger do login, índice parcial, GRANT e
REVOKE) é do banco e não do ORM. Base: `docs/04-modelo-de-dados.md`, seções 3.1, 3.6 e 4.

Permissões: a migração roda como `dono` (dono das tabelas). O papel `app`, que a API usa, NÃO é
criado aqui: em produção ele nasce por SQL, com a senha fora do repositório. Se ele não existir,
a migração para com uma mensagem clara. O nome pode ser trocado com `-x papel_app=<nome>`.
"""

from collections.abc import Sequence

from alembic import context, op
from sqlalchemy import text

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _papel_app() -> str:
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
    # Aspas duplas: o nome entra no SQL como identificador, nunca como código.
    return '"' + nome.replace('"', '""') + '"'


TABELAS = """
create type papel as enum ('admin', 'comissao', 'sindico', 'conselho');

-- Os 5 blocos (H-10). Bloco não é apagado, só desativado.
create table bloco (
    id      bigint generated always as identity primary key,
    numero  smallint not null unique check (numero between 1 and 9),
    nome    text not null,
    ativo   boolean not null default true
);

-- Uma linha por apartamento e a conta de acesso dele (RF-01, RF-03).
create table unidade (
    id                    bigint generated always as identity primary key,
    bloco_id              bigint not null references bloco (id),
    numero                text not null check (numero ~ '^[0-9]{3}$'),
    andar                 smallint not null check (andar between 0 and 7),
    -- Bloco 1-9 + andar 0-7 + posição: 4 dígitos, começando por 1-9 (RF-03).
    login                 text not null unique check (login ~ '^[1-9][0-7][0-9]{2}$'),
    ativa                 boolean not null default true,
    senha_hash            text not null,
    precisa_trocar_senha  boolean not null default true,
    ativada_em            timestamptz,
    responsavel_nome      text,
    celular               text,
    email                 text,
    tentativas_falhas     smallint not null default 0,
    bloqueada_ate         timestamptz,
    unique (bloco_id, numero)
);

-- Login = número do bloco + número do apartamento ('1' + '101' = '1101'). O banco calcula e
-- ignora o que a aplicação mandar, então nenhum login sai do padrão (RF-03).
-- Toda função de trigger fixa o search_path (pg_temp por último) e usa nomes qualificados:
-- sem isso, uma tabela temporária chamada "bloco" seria lida no lugar da verdadeira.
create function public.unidade_definir_login() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
begin
    select b.numero::text || new.numero into new.login
      from public.bloco b where b.id = new.bloco_id;
    return new;
end;
$$;

create trigger unidade_login
    before insert or update on unidade
    for each row execute function public.unidade_definir_login();

-- Se o número do bloco mudar (H-10), os logins das unidades acompanham.
create function public.bloco_atualizar_logins() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
begin
    update public.unidade set numero = numero where bloco_id = new.id;
    return null;
end;
$$;

create trigger bloco_logins
    after update of numero on bloco
    for each row when (old.numero is distinct from new.numero)
    execute function public.bloco_atualizar_logins();

-- Papel de gestão (RF-09, H-09). Retirar preenche retirado_em; a linha fica.
create table unidade_papel (
    id             bigint generated always as identity primary key,
    unidade_id     bigint not null references unidade (id),
    papel          papel not null,
    concedido_em   timestamptz not null default now(),
    concedido_por  bigint references unidade (id),
    retirado_em    timestamptz,
    retirado_por   bigint references unidade (id)
);

-- Um papel em vigor por tipo por unidade.
create unique index unidade_papel_em_vigor
    on unidade_papel (unidade_id, papel) where retirado_em is null;

-- Cada aparelho conectado (H-02, H-06). Só o hash do token.
create table sessao (
    id             bigint generated always as identity primary key,
    unidade_id     bigint not null references unidade (id),
    token_hash     text not null unique,
    aparelho       text,
    criada_em      timestamptz not null default now(),
    ultimo_uso_em  timestamptz not null default now(),
    encerrada_em   timestamptz
);
create index sessao_unidade on sessao (unidade_id);

-- Registro de ações, só de inclusão (RNF-14, H-11). Sem dado pessoal em detalhes.
create table historico (
    id           bigint generated always as identity primary key,
    ocorrido_em  timestamptz not null default now(),
    unidade_id   bigint references unidade (id),
    acao         text not null,
    entidade     text,
    entidade_id  bigint,
    detalhes     jsonb not null default '{}'
);
create index historico_ocorrido_em on historico (ocorrido_em);

-- A data do histórico é sempre a do banco: o app não consegue registrar uma ação no passado.
create function public.historico_carimbar_data() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
begin
    new.ocorrido_em := now();
    return new;
end;
$$;

create trigger historico_data
    before insert on historico
    for each row execute function public.historico_carimbar_data();

-- Erros da API: os logs grátis da Vercel duram 1 hora. Sem dado pessoal.
create table erro (
    id           bigint generated always as identity primary key,
    ocorrido_em  timestamptz not null default now(),
    rota         text not null,
    tipo         text not null,
    mensagem     text not null,
    unidade_id   bigint references unidade (id)
);
create index erro_ocorrido_em on erro (ocorrido_em);
"""

# Modelo de dados, seção 4: o app não apaga o que é oficial e não altera o histórico.
PERMISSOES = """
grant usage on schema public to {app};
grant select, insert, update         on bloco, unidade, unidade_papel to {app};
grant select, insert, update, delete on sessao to {app};
grant select, insert                 on historico to {app};
grant select, insert, delete         on erro to {app};
"""

# Sem tabela temporária para ninguém além do dono: tabela temporária é o caminho clássico para
# sequestrar nomes de tabela em funções. O nome do banco vem de current_database(), então a
# migração serve igual no Neon, no CI e nos testes.
SEM_TEMPORARIA = """
do $$
begin
    execute format('revoke temporary on database %I from public', current_database());
end;
$$;
"""
COM_TEMPORARIA = SEM_TEMPORARIA.replace("revoke temporary", "grant temporary").replace(
    "from public", "to public"
)


def upgrade() -> None:
    app = _papel_app()
    op.execute(TABELAS)
    op.execute(PERMISSOES.format(app=app))
    op.execute(SEM_TEMPORARIA)


def downgrade() -> None:
    app = _papel_app()
    op.execute(
        """
        drop table erro, historico, sessao, unidade_papel, unidade, bloco;
        drop function public.historico_carimbar_data();
        drop function public.bloco_atualizar_logins();
        drop function public.unidade_definir_login();
        drop type papel;
        """
    )
    op.execute(f"revoke usage on schema public from {app};")
    op.execute(COM_TEMPORARIA)
