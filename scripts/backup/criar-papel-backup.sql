-- Papel `backup`: só lê, para o pg_dump diário do GitHub Actions (ADR-0009).
--
-- Rodar UMA vez, no banco `portal` de produção, conectado como `dono` (conexão direta):
--   psql "<URL do dono>" -v ON_ERROR_STOP=1 -f scripts/backup/criar-papel-backup.sql
-- e, na mesma sessão ou numa nova, definir a senha sem que ela passe por arquivo ou histórico:
--   \password backup
-- A URL do segredo BACKUP_DATABASE_URL usa esse papel, a conexão direta (host SEM "-pooler") e
-- ?sslmode=require.
--
-- Rodar de novo não muda nada (nem a senha). Nenhuma senha neste arquivo: o repositório é público.

do $$
begin
    if not exists (select 1 from pg_roles where rolname = 'backup') then
        -- LOGIN sem senha: até o \password, ninguém entra com ele.
        create role backup login;
    end if;
end;
$$;

-- INHERIT é necessário para usar os privilégios de pg_read_all_data sem SET ROLE.
alter role backup inherit nosuperuser nocreatedb nocreaterole noreplication nobypassrls
    connection limit 2;

-- Lê todas as tabelas, visões e sequências de todos os esquemas. Não escreve nada.
grant pg_read_all_data to backup;

-- Segunda trava: toda transação do papel nasce somente leitura.
alter role backup set default_transaction_read_only = on;

-- Conferência: deve mostrar só pg_read_all_data e nenhum papel de escrita.
select r.rolname as papel,
       r.rolsuper as superusuario,
       r.rolcreaterole as cria_papel,
       array(select m.rolname
               from pg_auth_members a
               join pg_roles m on m.oid = a.roleid
              where a.member = r.oid
              order by 1) as membro_de
  from pg_roles r
 where r.rolname = 'backup';
