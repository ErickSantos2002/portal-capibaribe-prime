-- Verificações de um banco restaurado (ADR-0009). Qualquer uma que não bater levanta exceção, e
-- o psql (com ON_ERROR_STOP) sai com erro. Uso:
--   psql "<URL do banco restaurado>" -X -v ON_ERROR_STOP=1 -v head=<revisão> -f verificacoes.sql
-- `head` vazio pula a comparação com a migração mais nova do repositório.
--
-- Só números e nomes de tabela saem no log: nenhum dado de morador.

\set QUIET on
select set_config('verificacao.head', :'head', false) \gset
\set QUIET off

do $$
declare
    -- Tabelas do modelo até a migração 0005. Migração nova que cria tabela: acrescentar aqui
    -- (o teste api/testes/test_m2_backup.py confere contra o banco migrado).
    esperadas constant text[] := array[
        'bloco', 'unidade', 'unidade_papel', 'sessao', 'historico', 'erro',
        'aviso', 'aviso_versao', 'aviso_bloco', 'aviso_leitura', 'entrada_tentativa',
        'inscricao_push', 'token_recuperacao', 'notificacao_envio', 'alembic_version'
    ];
    faltando text[];
    head constant text := current_setting('verificacao.head');
    versao text;
    n bigint;
begin
    select array_agg(t order by t) into faltando
      from unnest(esperadas) t
     where to_regclass('public.' || t) is null;
    if faltando is not null then
        raise exception 'tabelas do modelo faltando no banco restaurado: %', faltando;
    end if;

    select count(*) into n from public.bloco;
    if n <> 5 then
        raise exception 'esperava 5 blocos, o banco restaurado tem %', n;
    end if;

    select count(*) into n from public.unidade;
    if n <> 320 then
        raise exception 'esperava 320 unidades, o banco restaurado tem %', n;
    end if;

    -- Toda unidade aponta para um bloco que existe (a chave estrangeira veio junto).
    select count(*) into n
      from public.unidade u left join public.bloco b on b.id = u.bloco_id
     where b.id is null;
    if n <> 0 then
        raise exception '% unidades sem bloco no banco restaurado', n;
    end if;

    select count(*) into n from public.alembic_version;
    if n <> 1 then
        raise exception 'alembic_version deveria ter 1 linha, tem %', n;
    end if;
    select version_num into versao from public.alembic_version;
    if head <> '' and versao <> head then
        raise exception 'o backup está na migração %, o repositório na %', versao, head;
    end if;

    -- As funções e gatilhos vieram (sem eles o login das unidades deixa de ser calculado).
    if to_regprocedure('public.unidade_definir_login()') is null then
        raise exception 'função unidade_definir_login ausente no banco restaurado';
    end if;
    select count(*) into n
      from pg_trigger
     where tgrelid = 'public.unidade'::regclass and not tgisinternal;
    if n = 0 then
        raise exception 'a tabela unidade voltou sem gatilhos';
    end if;

    -- As permissões do papel app vieram junto (a API depende delas).
    if to_regrole('app') is not null
       and not has_table_privilege('app', 'public.unidade', 'SELECT') then
        raise exception 'o papel app perdeu o SELECT em unidade na restauração';
    end if;
    -- A trava da migração 0001 (sem tabela temporária) é do banco, não do dump: o
    -- restaurar.sh a reaplica. Aqui se confere que reaplicou.
    if to_regrole('app') is not null
       and has_database_privilege('app', current_database(), 'TEMPORARY') then
        raise exception 'o papel app pode criar tabela temporária (falta o REVOKE TEMPORARY)';
    end if;

    raise notice 'verificações ok: 5 blocos, 320 unidades, migração %', versao;
end;
$$;

-- Resumo para o log: linhas por tabela do modelo.
select table_name as tabela,
       (xpath('/row/n/text()',
              query_to_xml(format('select count(*) as n from public.%I', table_name),
                           false, true, '')))[1]::text::bigint as linhas
  from information_schema.tables
 where table_schema = 'public' and table_type = 'BASE TABLE'
 order by table_name;
