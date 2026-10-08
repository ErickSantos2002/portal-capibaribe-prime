"""Documentos e anexos (M3): arquivo enviado, documento com versões e anexo de aviso.

Revisão: 0007
Anterior: 0006
Criada em: 2026-10-07

Escrita à mão, no mesmo padrão da 0002 a 0006. Spec: `docs/superpowers/specs/m3-contrato.md`,
seção 2; decisão sobre a guarda dos arquivos: ADR-0011.

- `arquivo` (RNF-22): o que foi enviado ao bucket. O conteúdo fica no R2 (`envios/<chave>`
  até a API conferir, `arquivos/<chave>` depois); aqui, só a chave, o nome (um rótulo), o tipo,
  a finalidade e o tamanho. Pendente pode ser corrigido e apagado; confirmado nunca muda nem é
  apagado (o objeto dele está travado no bucket). Até 50 por unidade a cada 24 horas.
- `documento` e `documento_versao` (H-17 a H-19): versões em sequência, cada uma com um arquivo
  confirmado de finalidade `documento`; arquivado não volta nem ganha versão; completo no
  commit (versão 1). Aviso automático (RF-33) só de documento que as unidades podem ver.
- `aviso_anexo` (H-12): até 5 arquivos de finalidade `aviso` por versão, gravados na mesma
  transação que cria a versão (o que foi publicado não ganha nem perde anexo depois). Um
  arquivo serve a um aviso só (a correção repete os anexos do mesmo aviso) e nunca a um
  documento.
- Nada daqui é apagado pelo `app`, menos o arquivo pendente (RN-05).
"""

from collections.abc import Sequence

from alembic import context, op
from sqlalchemy import text

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _papel_app() -> str:
    """Mesmo cuidado da 0001 a 0006: o papel `app` precisa existir e entra como identificador."""
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


# `\\\\` no Python vira `\\` no SQL, que a expressão regular lê como uma barra invertida.
ARQUIVO = """
-- O que foi enviado ao bucket (RNF-22). O conteúdo nunca passa pelo banco.
create table arquivo (
    id              bigint generated always as identity primary key,
    -- 128 bits aleatórios, gerados pela API e nunca reaproveitados (ADR-0011).
    chave           text not null unique constraint arquivo_chave check (
                        chave ~ '^[0-9a-f]{32}$'),
    -- Só um rótulo para a tela e o download: o objeto no bucket nunca usa este nome.
    nome_original   text not null constraint arquivo_nome check (
                        char_length(nome_original) between 1 and 200
                        and nome_original = btrim(nome_original)
                        and nome_original !~ '[[:cntrl:]/\\\\]'),
    tipo            text not null constraint arquivo_tipo check (
                        tipo in ('application/pdf', 'image/jpeg', 'image/png', 'image/webp')),
    finalidade      text not null constraint arquivo_finalidade check (
                        finalidade in ('aviso', 'documento')),
    -- 20 MB no documento (H-17), 10 MB no anexo de aviso (H-12).
    tamanho_bytes   integer not null constraint arquivo_tamanho check (
                        tamanho_bytes between 1 and 20971520
                        and (finalidade = 'documento' or tamanho_bytes <= 10485760)),
    enviado_por     bigint not null references unidade (id),
    enviado_em      timestamptz not null default now(),
    -- Nulo = pendente: a URL de envio foi dada, o conteúdo ainda não foi conferido.
    confirmado_em   timestamptz
);
create index arquivo_enviado on arquivo (enviado_por, enviado_em);
create index arquivo_pendente on arquivo (enviado_em) where confirmado_em is null;

create function public.arquivo_conferir() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
begin
    if tg_op = 'DELETE' then
        if old.confirmado_em is not null then
            raise exception 'Arquivo publicado não é apagado.'
                using errcode = 'check_violation', constraint = 'arquivo_confirmado';
        end if;
        return old;
    end if;
    if tg_op = 'INSERT' then
        new.enviado_em := now();
        new.confirmado_em := null;
        -- Trava a unidade: envios ao mesmo tempo contam uns com os outros.
        perform 1 from public.unidade u where u.id = new.enviado_por for no key update;
        if (select count(*) from public.arquivo a
             where a.enviado_por = new.enviado_por
               and a.enviado_em > now() - interval '24 hours') >= 50 then
            raise exception 'No máximo 50 arquivos por apartamento a cada 24 horas.'
                using errcode = 'check_violation', constraint = 'arquivo_limite_dia';
        end if;
        return new;
    end if;
    if old.confirmado_em is not null then
        raise exception 'Arquivo publicado não muda.'
            using errcode = 'check_violation', constraint = 'arquivo_confirmado';
    end if;
    new.enviado_em := old.enviado_em;
    if new.confirmado_em is not null then
        new.confirmado_em := now();
    end if;
    return new;
end;
$$;

create trigger arquivo_regras
    before insert or update or delete on arquivo
    for each row execute function public.arquivo_conferir();
"""

DOCUMENTOS = """
-- O documento (H-17, H-18). Nunca é apagado: versão nova (H-19) ou arquivado (RN-05).
create table documento (
    id              bigint generated always as identity primary key,
    titulo          text not null constraint documento_titulo_tamanho check (
                        char_length(btrim(titulo)) between 1 and 120
                        and char_length(titulo) <= 120),
    categoria       text not null constraint documento_categoria check (categoria in (
                        'convencao', 'regimento', 'ata', 'contrato', 'obra', 'orientacao',
                        'outro')),
    -- A data do documento, não a do envio.
    data_documento  date not null constraint documento_data check (
                        data_documento between '1990-01-01' and '2100-12-31'),
    acesso          text not null constraint documento_acesso check (
                        acesso in ('publico', 'compradores', 'gestao')),
    criado_por      bigint not null references unidade (id),
    criado_em       timestamptz not null default now(),
    -- O aviso automático de "Avisar as unidades" (RF-33), gravado na criação.
    aviso_id        bigint unique references aviso (id),
    arquivado_em    timestamptz,
    -- Um aviso para todos apontando para documento só da gestão seria um botão que não abre.
    constraint documento_aviso_gestao check (aviso_id is null or acesso <> 'gestao')
);

-- O arquivo de cada versão. A maior é a atual; as outras são "Versões anteriores".
create table documento_versao (
    documento_id  bigint not null references documento (id),
    versao        smallint not null constraint documento_versao_minima check (versao >= 1),
    arquivo_id    bigint not null unique references arquivo (id),
    enviada_por   bigint not null references unidade (id),
    enviada_em    timestamptz not null default now(),
    primary key (documento_id, versao)
);

-- Anexos de uma versão do aviso (H-12): a versão antiga continua com os anexos que tinha.
create table aviso_anexo (
    aviso_id    bigint not null,
    versao      smallint not null,
    arquivo_id  bigint not null references arquivo (id),
    ordem       smallint not null constraint aviso_anexo_ordem check (ordem between 1 and 5),
    primary key (aviso_id, versao, arquivo_id),
    constraint aviso_anexo_ordem_unica unique (aviso_id, versao, ordem),
    foreign key (aviso_id, versao) references aviso_versao (aviso_id, versao)
);
create index aviso_anexo_arquivo on aviso_anexo (arquivo_id);

-- Datas do documento são do banco; arquivado não volta (como o aviso).
create function public.documento_carimbar() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
begin
    if tg_op = 'INSERT' then
        new.criado_em := now();
        new.arquivado_em := null;
        return new;
    end if;
    new.criado_em := old.criado_em;
    if old.arquivado_em is not null then
        if new.arquivado_em is null then
            raise exception 'Documento arquivado não volta para a lista.'
                using errcode = 'check_violation', constraint = 'documento_arquivado';
        end if;
        new.arquivado_em := old.arquivado_em;
    elsif new.arquivado_em is not null then
        new.arquivado_em := now();
    end if;
    return new;
end;
$$;

create trigger documento_datas
    before insert or update on documento
    for each row execute function public.documento_carimbar();

-- No commit: todo documento tem a versão 1 (nasce antes dela, na mesma transação).
create function public.documento_conferir_completo() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
begin
    if not exists (select 1 from public.documento_versao v
                    where v.documento_id = new.id and v.versao = 1) then
        raise exception 'Documento sem arquivo (versão 1).'
            using errcode = 'check_violation', constraint = 'documento_completo';
    end if;
    return null;
end;
$$;

create constraint trigger documento_completo
    after insert on documento
    deferrable initially deferred
    for each row execute function public.documento_conferir_completo();

-- O arquivo pode ser usado aqui? Confirmado, da finalidade certa e em nenhum outro lugar (um
-- aviso pode repetir os próprios anexos na correção). Trava a linha do arquivo: dois usos ao
-- mesmo tempo não passam juntos.
create function public.arquivo_conferir_uso(p_arquivo bigint, p_finalidade text, p_aviso bigint)
returns void
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
declare
    da_finalidade text;
    confirmado timestamptz;
begin
    select a.finalidade, a.confirmado_em into da_finalidade, confirmado
      from public.arquivo a where a.id = p_arquivo for no key update;
    if not found then
        return;  -- a chave estrangeira recusa
    end if;
    if confirmado is null then
        raise exception 'Arquivo ainda não conferido pelo Portal.'
            using errcode = 'check_violation', constraint = 'arquivo_nao_confirmado';
    end if;
    if da_finalidade <> p_finalidade then
        raise exception 'Arquivo enviado para outra finalidade.'
            using errcode = 'check_violation', constraint = 'arquivo_finalidade_errada';
    end if;
    if exists (select 1 from public.documento_versao v where v.arquivo_id = p_arquivo)
       or exists (select 1 from public.aviso_anexo n
                   where n.arquivo_id = p_arquivo
                     and (p_aviso is null or n.aviso_id <> p_aviso)) then
        raise exception 'Este arquivo já está em uso em outro lugar.'
            using errcode = 'check_violation', constraint = 'arquivo_em_uso';
    end if;
end;
$$;

-- Versões em sequência, com a data do banco, num documento que não está arquivado.
create function public.documento_versao_conferir() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
declare
    esperada integer;
    arquivado timestamptz;
begin
    -- Trava o documento: arquivar ao mesmo tempo espera esta versão (ou é visto aqui).
    select d.arquivado_em into arquivado
      from public.documento d where d.id = new.documento_id for share;
    if arquivado is not null then
        raise exception 'Documento arquivado não recebe versão nova.'
            using errcode = 'check_violation', constraint = 'documento_arquivado';
    end if;
    select coalesce(max(v.versao), 0) + 1 into esperada
      from public.documento_versao v where v.documento_id = new.documento_id;
    if new.versao <> esperada then
        raise exception 'A próxima versão do documento é a %.', esperada
            using errcode = 'check_violation', constraint = 'documento_versao_sequencia';
    end if;
    perform public.arquivo_conferir_uso(new.arquivo_id, 'documento', null);
    new.enviada_em := now();
    return new;
end;
$$;

create trigger documento_versao_regras
    before insert on documento_versao
    for each row execute function public.documento_versao_conferir();

-- Anexo só na transação que cria a versão: `criada_em` da versão é o `now()` da transação que
-- a gravou (trigger da 0002). Depois disso, a versão publicada fica como foi.
create function public.aviso_anexo_conferir() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
begin
    if (select v.criada_em from public.aviso_versao v
         where v.aviso_id = new.aviso_id and v.versao = new.versao) is distinct from now() then
        raise exception 'Anexo entra junto com a versão do aviso, nunca depois.'
            using errcode = 'check_violation', constraint = 'aviso_anexo_versao_fechada';
    end if;
    perform public.arquivo_conferir_uso(new.arquivo_id, 'aviso', new.aviso_id);
    return new;
end;
$$;

create trigger aviso_anexo_regras
    before insert on aviso_anexo
    for each row execute function public.aviso_anexo_conferir();
"""

# Spec, seção 2.5: o arquivo pendente é corrigido ou apagado; o resto só cresce.
PERMISSOES = """
grant select, insert, delete on arquivo to {app};
grant update (tipo, tamanho_bytes, confirmado_em) on arquivo to {app};
grant select, insert on documento, documento_versao, aviso_anexo to {app};
grant update (arquivado_em) on documento to {app};
"""


def upgrade() -> None:
    app = _papel_app()
    op.execute(ARQUIVO)
    op.execute(DOCUMENTOS)
    op.execute(PERMISSOES.format(app=app))


def downgrade() -> None:
    # As permissões saem com as tabelas.
    op.execute(
        """
        drop table aviso_anexo, documento_versao, documento, arquivo;
        drop function public.aviso_anexo_conferir();
        drop function public.documento_versao_conferir();
        drop function public.arquivo_conferir_uso(bigint, text, bigint);
        drop function public.documento_conferir_completo();
        drop function public.documento_carimbar();
        drop function public.arquivo_conferir();
        """
    )
