"""Avisos sem anexo (aviso, aviso_versao, aviso_bloco, aviso_leitura) e regras do M1.

Revisão: 0002
Anterior: 0001
Criada em: 2026-10-05

Escrita à mão, no mesmo padrão da 0001. Base: `docs/04-modelo-de-dados.md` (seções 3.3 e 4) e
`docs/superpowers/specs/m1-contrato.md` (seção 2). `aviso_anexo` e `arquivo` ficam para o M3.

Além das tabelas de avisos:
- papel em vigor só em unidade ativa e já ativada; os papéis que a carga do M0 deu a unidades
  ainda com `mudar123` são retirados (o admin volta por `promover_admin`);
- o último administrador não pode ser retirado (H-09, prometido para o M1 no M0), nem a unidade
  com papel desativada;
- `unidade.senha_trocada_em`: sessão aberta antes da última troca de senha não vale;
- datas de papel, aviso, versão e leitura carimbadas pelo banco;
- o `app` só altera `retirado_em`/`retirado_por` em `unidade_papel`;
- unidade ativada precisa ter responsável e celular, nos formatos combinados (RF-04).
"""

from collections.abc import Sequence

from alembic import context, op
from sqlalchemy import text

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _papel_app() -> str:
    """Mesmo cuidado da 0001: o papel `app` precisa existir e entra como identificador."""
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


# Toda função de trigger fixa o search_path com pg_temp por último e usa nomes qualificados
# (dúvida 20 do M0: sem isso, uma tabela temporária homônima seria lida no lugar da verdadeira).
AVISOS = """
-- O aviso em si (H-12 a H-16). Nunca é apagado: corrige-se (versão nova) ou arquiva-se (RN-05).
create table aviso (
    id              bigint generated always as identity primary key,
    publicado_por   bigint not null references unidade (id),
    -- Com que papel foi assinado ("Publicado pela Comissão"): o papel da unidade pode mudar.
    publicado_como  papel not null,
    publicado_em    timestamptz not null default now(),
    para_todos      boolean not null,
    fixado          boolean not null default false,
    arquivado_em    timestamptz
);
create index aviso_publicado_em on aviso (publicado_em);

-- Título e texto, com o histórico de correções (RF-14, H-15). A maior versão é a em vigor.
create table aviso_versao (
    aviso_id    bigint not null references aviso (id),
    versao      smallint not null constraint aviso_versao_minima check (versao >= 1),
    titulo      text not null constraint aviso_versao_titulo_tamanho check (
                    char_length(btrim(titulo)) between 1 and 120 and char_length(titulo) <= 120),
    texto       text not null constraint aviso_versao_texto_tamanho check (
                    char_length(btrim(texto)) between 1 and 10000 and char_length(texto) <= 10000),
    criada_em   timestamptz not null default now(),
    criada_por  bigint not null references unidade (id),
    primary key (aviso_id, versao)
);

-- Destino quando o aviso não é para todos.
create table aviso_bloco (
    aviso_id  bigint not null references aviso (id),
    bloco_id  bigint not null references bloco (id),
    primary key (aviso_id, bloco_id)
);
create index aviso_bloco_bloco on aviso_bloco (bloco_id);

-- Primeira abertura pela unidade (H-16). Abrir de novo não muda nada.
create table aviso_leitura (
    aviso_id    bigint not null references aviso (id),
    unidade_id  bigint not null references unidade (id),
    lido_em     timestamptz not null default now(),
    primary key (aviso_id, unidade_id)
);
create index aviso_leitura_unidade on aviso_leitura (unidade_id);

-- Datas do aviso são do banco. Arquivar carimba a data uma vez; arquivado não volta ao mural.
create function public.aviso_carimbar() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
begin
    if tg_op = 'INSERT' then
        new.publicado_em := now();
        new.arquivado_em := null;
        return new;
    end if;
    if old.arquivado_em is not null then
        if new.arquivado_em is null then
            raise exception 'Aviso arquivado não volta ao mural.'
                using errcode = 'check_violation', constraint = 'aviso_arquivado';
        end if;
        new.arquivado_em := old.arquivado_em;
    elsif new.arquivado_em is not null then
        new.arquivado_em := now();
    end if;
    return new;
end;
$$;

create trigger aviso_datas
    before insert or update on aviso
    for each row execute function public.aviso_carimbar();

-- Versões em sequência (1, 2, 3...) e com a data do banco.
create function public.aviso_versao_conferir() returns trigger
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

create trigger aviso_versao_sequencia
    before insert on aviso_versao
    for each row execute function public.aviso_versao_conferir();

-- Aviso para todos não tem lista de blocos.
create function public.aviso_bloco_conferir() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
begin
    if (select a.para_todos from public.aviso a where a.id = new.aviso_id) then
        raise exception 'Aviso para todos os blocos não tem lista de blocos.'
            using errcode = 'check_violation', constraint = 'aviso_bloco_destino';
    end if;
    return new;
end;
$$;

create trigger aviso_bloco_destino
    before insert on aviso_bloco
    for each row execute function public.aviso_bloco_conferir();

create function public.aviso_leitura_carimbar() returns trigger
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

-- No commit: todo aviso tem a versão 1 e, se não é para todos, pelo menos um bloco. Adiado para
-- o fim da transação porque o aviso nasce antes da versão e dos blocos.
create function public.aviso_conferir_completo() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
begin
    if not exists (select 1 from public.aviso_versao v
                    where v.aviso_id = new.id and v.versao = 1) then
        raise exception 'Aviso sem título e texto (versão 1).'
            using errcode = 'check_violation', constraint = 'aviso_completo';
    end if;
    if not new.para_todos
       and not exists (select 1 from public.aviso_bloco b where b.aviso_id = new.id) then
        raise exception 'Aviso sem destino: escolha pelo menos um bloco.'
            using errcode = 'check_violation', constraint = 'aviso_completo';
    end if;
    return null;
end;
$$;

create constraint trigger aviso_completo
    after insert on aviso
    deferrable initially deferred
    for each row execute function public.aviso_conferir_completo();
"""

# Papel em vigor numa unidade que não entrou é uma conta de gestão com a senha que todo mundo
# conhece (revisão do M1). A carga do M0 deu `admin` a uma unidade ainda com `mudar123`: esse
# papel é retirado aqui, ANTES das regras novas (que não deixariam retirar o último admin). O
# admin volta pelo comando `promover_admin`, depois do primeiro acesso (spec do M1, seção 2.5).
RETIRAR_PAPEIS_SEM_ATIVACAO = """
with retirados as (
    update unidade_papel p set retirado_em = now()
      from unidade u
     where u.id = p.unidade_id and p.retirado_em is null
       and (u.ativada_em is null or not u.ativa)
    returning p.unidade_id, p.papel
)
insert into historico (acao, entidade, entidade_id, detalhes)
select 'papel_retirado', 'unidade', unidade_id,
       jsonb_build_object('papel', papel, 'origem', 'migracao_0002')
  from retirados;
"""

PAPEIS_E_CONTATOS = """
-- Papel: datas do banco; só em unidade ativa e ativada; retirado não volta; o último admin não
-- sai (H-09).
create function public.unidade_papel_conferir() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
begin
    if tg_op = 'INSERT' then
        -- Trava a linha da unidade: um reset ao mesmo tempo espera (ou é recusado).
        perform 1 from public.unidade u
          where u.id = new.unidade_id and u.ativa and u.ativada_em is not null
          for share;
        if not found then
            raise exception 'Papel só em unidade ativa que já fez o primeiro acesso.'
                using errcode = 'check_violation', constraint = 'papel_em_unidade_ativada';
        end if;
        new.concedido_em := now();
        new.retirado_em := null;
        new.retirado_por := null;
        return new;
    end if;
    if old.retirado_em is not null then
        if new.retirado_em is distinct from old.retirado_em then
            raise exception 'Papel retirado não volta a valer: conceda de novo.'
                using errcode = 'check_violation', constraint = 'papel_retirado';
        end if;
        return new;
    end if;
    if new.retirado_em is not null then
        new.retirado_em := now();
        if old.papel = 'admin' then
            -- Trava as outras linhas de admin em vigor. Duas retiradas ao mesmo tempo: no READ
            -- COMMITTED a segunda espera e relê (e é recusada); no REPEATABLE READ ou acima,
            -- falha por serialização. Também pode dar impasse, que o Postgres desfaz abortando
            -- uma das duas. Em nenhum caso o Portal fica sem administrador.
            perform 1 from public.unidade_papel p
              where p.papel = 'admin' and p.retirado_em is null and p.id <> old.id
              for update;
            if not found then
                raise exception 'O Portal não pode ficar sem administrador.'
                    using errcode = 'check_violation', constraint = 'ultimo_admin';
            end if;
        end if;
    end if;
    return new;
end;
$$;

create trigger unidade_papel_regras
    before insert or update on unidade_papel
    for each row execute function public.unidade_papel_conferir();

-- Contatos (RF-04): obrigatórios depois de ativar; celular só com dígitos (DDD + número);
-- e-mail em minúsculas.
alter table unidade
    add constraint unidade_ativada_tem_contato
        check (ativada_em is null or (responsavel_nome is not null and celular is not null)),
    add constraint unidade_nome_formato
        check (responsavel_nome is null or (char_length(responsavel_nome) between 1 and 100
               and responsavel_nome = btrim(responsavel_nome))),
    add constraint unidade_celular_formato
        check (celular is null or celular ~ '^[0-9]{10,11}$'),
    add constraint unidade_email_formato
        check (email is null or (char_length(email) <= 254 and email = lower(email)
               and email ~ '^[^@[:space:]]+@[^@[:space:]]+\\.[^@[:space:]]+$'));

-- Quando a senha mudou pela última vez (data do banco). Sessão aberta antes disso não vale:
-- quem entrou com mudar123 antes do morador perde o acesso quando ele troca a senha, e o reset
-- e o "apagar meus dados" derrubam todos os aparelhos sem depender da rota (revisão do M1).
alter table unidade add column senha_trocada_em timestamptz not null default now();

create function public.unidade_conferir() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
begin
    if tg_op = 'INSERT' then
        new.senha_trocada_em := now();
        return new;
    end if;
    if new.senha_hash is distinct from old.senha_hash then
        new.senha_trocada_em := now();
    else
        new.senha_trocada_em := old.senha_trocada_em;
    end if;
    -- Unidade com papel em vigor não é desativada nem volta a "não ativada": retire o papel
    -- antes (o reset faz isso). Cobre também o único admin.
    if (not new.ativa or new.ativada_em is null)
       and (old.ativa and old.ativada_em is not null)
       and exists (select 1 from public.unidade_papel p
                    where p.unidade_id = new.id and p.retirado_em is null) then
        raise exception 'Retire o papel de gestão antes de desativar ou resetar a unidade.'
            using errcode = 'check_violation', constraint = 'unidade_com_papel';
    end if;
    return new;
end;
$$;

create trigger unidade_regras
    before insert or update on unidade
    for each row execute function public.unidade_conferir();

-- A data da sessão é a do banco: uma sessão "do futuro" sobreviveria à troca de senha.
create function public.sessao_carimbar() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
begin
    if tg_op = 'INSERT' then
        new.criada_em := now();
    else
        new.criada_em := old.criada_em;
    end if;
    return new;
end;
$$;

create trigger sessao_data
    before insert or update on sessao
    for each row execute function public.sessao_carimbar();
"""

# Modelo, seção 4 e spec do M1, seção 2.3: nada de avisos é apagado; o publicado não é reescrito.
PERMISSOES = """
grant select, insert on aviso, aviso_versao, aviso_bloco, aviso_leitura to {app};
grant update (fixado, arquivado_em) on aviso to {app};
revoke update on unidade_papel from {app};
grant update (retirado_em, retirado_por) on unidade_papel to {app};
"""


def upgrade() -> None:
    app = _papel_app()
    op.execute(AVISOS)
    op.execute(RETIRAR_PAPEIS_SEM_ATIVACAO)
    op.execute(PAPEIS_E_CONTATOS)
    op.execute(PERMISSOES.format(app=app))


def downgrade() -> None:
    app = _papel_app()
    op.execute(
        f"""
        revoke update (retirado_em, retirado_por) on unidade_papel from {app};
        grant update on unidade_papel to {app};
        alter table unidade
            drop constraint unidade_email_formato,
            drop constraint unidade_celular_formato,
            drop constraint unidade_nome_formato,
            drop constraint unidade_ativada_tem_contato;
        drop trigger sessao_data on sessao;
        drop function public.sessao_carimbar();
        drop trigger unidade_regras on unidade;
        drop function public.unidade_conferir();
        alter table unidade drop column senha_trocada_em;
        drop trigger unidade_papel_regras on unidade_papel;
        drop function public.unidade_papel_conferir();
        drop table aviso_leitura, aviso_bloco, aviso_versao, aviso;
        drop function public.aviso_conferir_completo();
        drop function public.aviso_leitura_carimbar();
        drop function public.aviso_bloco_conferir();
        drop function public.aviso_versao_conferir();
        drop function public.aviso_carimbar();
        """
    )
