"""Correções da revisão independente do M1: bloqueio por login e IP, aviso arquivado no banco,
versão lida do aviso.

Revisão: 0003
Anterior: 0002
Criada em: 2026-10-05

Escrita à mão, no mesmo padrão da 0002 (`docs/superpowers/plans/m1-revisao.md`):

- **Bloqueio por (login, IP)** (C2): o bloqueio da unidade inteira virava negação de serviço
  contra o dono (5 senhas erradas de qualquer um trancavam a porta dele). Agora conta por login
  e IP, em `entrada_tentativa`. O IP é guardado só como HMAC (`ip_hash`), e a linha expira
  (`expira_em`): nada dela vale depois de 15 minutos. `unidade.tentativas_falhas` e
  `unidade.bloqueada_ate` deixam de existir. A chave é o login (não a unidade) para que login
  que não existe conte e bloqueie igual a um que existe: a resposta não revela qual é qual.
- **Aviso arquivado não recebe versão nova** (C4): a regra era só da aplicação. O trigger de
  `aviso_versao` trava a linha do aviso (`for share`) e recusa (`aviso_versao_arquivado`).
  Arquivar e corrigir ao mesmo tempo: quem chega depois espera o outro e decide com o dado novo.
- **`aviso_leitura.versao_lida`** (U1): a maior versão do aviso que a unidade abriu, para a tela
  mostrar "Corrigido" a quem leu uma versão anterior. `lido_em` continua sendo a primeira
  leitura (o banco não deixa mudar); `versao_lida` só sobe e não passa da versão atual. As
  leituras que já existiam ganham a versão em vigor na hora em que foram feitas (pelas datas).
"""

from collections.abc import Sequence

from alembic import context, op
from sqlalchemy import text

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _papel_app() -> str:
    """Mesmo cuidado da 0001/0002: o papel `app` precisa existir e entra como identificador."""
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


BLOQUEIO = """
-- Senhas erradas por login e IP (H-03, revisão do M1). `falhas_em` guarda só as datas das falhas
-- que ainda contam (últimos 15 minutos); a aplicação descarta as velhas a cada tentativa.
create table entrada_tentativa (
    login          text not null constraint entrada_tentativa_login check (
                       login ~ '^[1-9][0-7][0-9]{2}$'),
    -- HMAC-SHA256 do IP, em hexadecimal: o IP cru nunca é guardado (LGPD).
    ip_hash        text not null constraint entrada_tentativa_ip_hash check (
                       ip_hash ~ '^[0-9a-f]{64}$'),
    falhas_em      timestamptz[] not null default '{}',
    bloqueada_ate  timestamptz,
    -- Depois disso a linha não vale nada e pode ser apagada.
    expira_em      timestamptz not null,
    primary key (login, ip_hash)
);
create index entrada_tentativa_expira on entrada_tentativa (expira_em);

alter table unidade drop column tentativas_falhas, drop column bloqueada_ate;
"""

VERSAO_ARQUIVADO = """
create or replace function public.aviso_versao_conferir() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
declare
    esperada integer;
    arquivado timestamptz;
begin
    -- Trava a linha do aviso (for share): um arquivamento em andamento termina antes, e a
    -- versão é decidida com o dado novo; um arquivamento que chega depois espera esta versão.
    select a.arquivado_em into arquivado from public.aviso a where a.id = new.aviso_id for share;
    if arquivado is not null then
        raise exception 'Aviso arquivado não pode ser corrigido.'
            using errcode = 'check_violation', constraint = 'aviso_versao_arquivado';
    end if;
    select coalesce(max(v.versao), 0) + 1 into esperada
      from public.aviso_versao v where v.aviso_id = new.aviso_id;
    if new.versao <> esperada then
        raise exception 'A próxima versão do aviso é a %.', esperada
            using errcode = 'check_violation', constraint = 'aviso_versao_sequencia';
    end if;
    new.criada_em := now();
    return new;
end;
$$;
"""

# A versão 0002 desta função, para o downgrade.
VERSAO_SEM_ARQUIVADO = """
create or replace function public.aviso_versao_conferir() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
declare
    esperada integer;
begin
    select coalesce(max(v.versao), 0) + 1 into esperada
      from public.aviso_versao v where v.aviso_id = new.aviso_id;
    if new.versao <> esperada then
        raise exception 'A próxima versão do aviso é a %.', esperada
            using errcode = 'check_violation', constraint = 'aviso_versao_sequencia';
    end if;
    new.criada_em := now();
    return new;
end;
$$;
"""

VERSAO_LIDA = """
alter table aviso_leitura add column versao_lida smallint;
-- Leituras de antes: a versão em vigor no momento da leitura.
update aviso_leitura l
   set versao_lida = coalesce((select max(v.versao) from aviso_versao v
                                where v.aviso_id = l.aviso_id and v.criada_em <= l.lido_em), 1);
alter table aviso_leitura alter column versao_lida set not null;

-- A primeira leitura não muda; a versão lida só sobe e não passa da atual. Sem versão
-- informada, conta a atual.
create or replace function public.aviso_leitura_carimbar() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
declare
    atual integer;
begin
    select coalesce(max(v.versao), 1) into atual
      from public.aviso_versao v where v.aviso_id = new.aviso_id;
    if tg_op = 'INSERT' then
        new.lido_em := now();
        new.versao_lida := coalesce(new.versao_lida, atual);
    else
        new.lido_em := old.lido_em;
        new.versao_lida := greatest(old.versao_lida, new.versao_lida);
    end if;
    if new.versao_lida < 1 or new.versao_lida > atual then
        raise exception 'Versão lida fora das versões do aviso (1 a %).', atual
            using errcode = 'check_violation', constraint = 'aviso_leitura_versao';
    end if;
    return new;
end;
$$;

drop trigger aviso_leitura_data on aviso_leitura;
create trigger aviso_leitura_data
    before insert or update on aviso_leitura
    for each row execute function public.aviso_leitura_carimbar();
"""

LIDA_SEM_VERSAO = """
drop trigger aviso_leitura_data on aviso_leitura;
create or replace function public.aviso_leitura_carimbar() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
begin
    new.lido_em := now();
    return new;
end;
$$;
create trigger aviso_leitura_data
    before insert on aviso_leitura
    for each row execute function public.aviso_leitura_carimbar();
alter table aviso_leitura drop column versao_lida;
"""

PERMISSOES = """
grant select, insert, update, delete on entrada_tentativa to {app};
grant update (versao_lida) on aviso_leitura to {app};
"""


def upgrade() -> None:
    app = _papel_app()
    op.execute(BLOQUEIO)
    op.execute(VERSAO_ARQUIVADO)
    op.execute(VERSAO_LIDA)
    op.execute(PERMISSOES.format(app=app))


def downgrade() -> None:
    app = _papel_app()
    op.execute(f"revoke update (versao_lida) on aviso_leitura from {app};")
    op.execute(LIDA_SEM_VERSAO)
    op.execute(VERSAO_SEM_ARQUIVADO)
    op.execute(
        """
        drop table entrada_tentativa;
        alter table unidade
            add column tentativas_falhas smallint not null default 0,
            add column bloqueada_ate timestamptz;
        """
    )
