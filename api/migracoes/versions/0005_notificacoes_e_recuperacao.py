"""Notificações e recuperação de senha (M2): inscrição de push por aparelho, token de
recuperação e registro de envios.

Revisão: 0005
Anterior: 0004
Criada em: 2026-10-06

Escrita à mão, no mesmo padrão da 0002 a 0004. Spec: `docs/superpowers/specs/m2-contrato.md`,
seção 2.

- `inscricao_push` (H-05): para onde mandar o push de cada aparelho. A chave é a sessão (modelo
  de dados, seção 3.1): uma por aparelho, e some quando a sessão é encerrada (trigger em
  `sessao`). Só aceita o formato do padrão Web Push (endpoint `https`, chave P-256 de 65 bytes e
  segredo de 16 bytes em base64url). No máximo 10 aparelhos inscritos por unidade, contando só
  as sessões que ainda valem.
- `token_recuperacao` (H-04): o link de "esqueci a senha". O banco guarda só o SHA-256 do token,
  carimba a criação e a validade (1 hora, ignorando o que a aplicação mandar), aceita o uso uma
  vez só e nunca depois de vencido, nem depois de a senha ter mudado. Só nasce para unidade
  ativa, ativada e com e-mail, e no máximo 3 por unidade por hora e 6 por dia (contra encher a
  caixa de alguém e gastar a cota do Gmail).
- `notificacao_envio` (H-13): um registro por aviso e canal (`push`, `email`). A chave única é o
  que impede mandar duas vezes; a situação só anda para a frente. Guarda só contagens, nunca
  endereço, e-mail ou unidade: é a medida de entrega, não dado pessoal.
"""

from collections.abc import Sequence

from alembic import context, op
from sqlalchemy import text

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _papel_app() -> str:
    """Mesmo cuidado da 0001 a 0004: o papel `app` precisa existir e entra como identificador."""
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


INSCRICAO_PUSH = """
-- Para onde mandar a notificação de cada aparelho (H-05). Endereço de push é dado de uso
-- técnico (modelo, seção 5): some junto com a sessão.
create table inscricao_push (
    sessao_id     bigint primary key references sessao (id) on delete cascade,
    endpoint      text not null unique constraint inscricao_push_endpoint check (
                      endpoint ~ '^https://' and char_length(endpoint) <= 2048),
    -- Chave pública P-256 do navegador (65 bytes) e segredo (16 bytes), em base64url.
    chave_p256dh  text not null constraint inscricao_push_p256dh check (
                      chave_p256dh ~ '^[A-Za-z0-9_-]{87}=?$'),
    chave_auth    text not null constraint inscricao_push_auth check (
                      chave_auth ~ '^[A-Za-z0-9_-]{22}(==)?$'),
    criada_em     timestamptz not null default now()
);

create function public.inscricao_push_conferir() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
declare
    da_unidade bigint;
    encerrada timestamptz;
    outras integer;
begin
    if tg_op = 'INSERT' then
        new.criada_em := now();
    else
        new.criada_em := old.criada_em;
    end if;
    -- Trava a sessão (`for share`) antes de ler `encerrada_em`: encerrar ao mesmo tempo espera
    -- esta inscrição (e o trigger de `sessao` a apaga depois) ou termina antes (e aqui se lê o
    -- valor novo). Sem a trava, a inscrição sobrevivia à sessão encerrada (revisão, achado 4).
    select s.unidade_id, s.encerrada_em into da_unidade, encerrada
      from public.sessao s where s.id = new.sessao_id for share;
    if encerrada is not null then
        raise exception 'Aparelho desconectado não recebe notificação.'
            using errcode = 'check_violation', constraint = 'inscricao_push_sessao_encerrada';
    end if;
    -- Duas inscrições da mesma unidade ao mesmo tempo: uma espera a outra e conta com ela.
    -- (`no key update` não segura quem só cria sessão para a unidade.)
    perform 1 from public.unidade u where u.id = da_unidade for no key update;
    -- Só contam as sessões que ainda valem, pela regra de `buscar_sessao` (aberta, usada nos
    -- últimos 180 dias, aberta depois da última troca de senha): as outras o morador não vê
    -- em Minha unidade e não teria como liberar a vaga (revisão, achado 5).
    select count(*) into outras
      from public.inscricao_push i
      join public.sessao s on s.id = i.sessao_id
      join public.unidade u on u.id = s.unidade_id
     where s.unidade_id = da_unidade and s.encerrada_em is null
       and s.ultimo_uso_em > now() - interval '180 days'
       and s.criada_em >= u.senha_trocada_em
       and i.sessao_id <> new.sessao_id
       and (tg_op = 'INSERT' or i.sessao_id <> old.sessao_id);
    if outras >= 10 then
        raise exception 'No máximo 10 aparelhos com notificação por apartamento.'
            using errcode = 'check_violation', constraint = 'inscricao_push_limite';
    end if;
    return new;
end;
$$;

create trigger inscricao_push_regras
    before insert or update on inscricao_push
    for each row execute function public.inscricao_push_conferir();

-- Sair, desconectar, trocar a senha e resetar encerram a sessão: a notificação para junto.
create function public.sessao_encerrada_sem_push() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
begin
    delete from public.inscricao_push i where i.sessao_id = new.id;
    return null;
end;
$$;

create trigger sessao_sem_push
    after update of encerrada_em on sessao
    for each row when (new.encerrada_em is not null and old.encerrada_em is null)
    execute function public.sessao_encerrada_sem_push();
"""

TOKEN_RECUPERACAO = """
-- "Esqueci a senha" por e-mail (H-04). O link leva o token; o banco, só o SHA-256 dele.
create table token_recuperacao (
    id          bigint generated always as identity primary key,
    unidade_id  bigint not null references unidade (id),
    token_hash  text not null unique constraint token_recuperacao_hash check (
                    token_hash ~ '^[0-9a-f]{64}$'),
    criado_em   timestamptz not null default now(),
    expira_em   timestamptz not null,
    usado_em    timestamptz
);
create index token_recuperacao_unidade on token_recuperacao (unidade_id, criado_em);

create function public.token_recuperacao_conferir() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
declare
    trocada timestamptz;
begin
    if tg_op = 'INSERT' then
        -- Validade contada pelo banco: a aplicação não consegue dar mais de 1 hora.
        new.criado_em := now();
        new.expira_em := now() + interval '1 hour';
        new.usado_em := null;
        -- Trava a unidade: dois pedidos ao mesmo tempo contam um com o outro.
        perform 1 from public.unidade u
         where u.id = new.unidade_id and u.ativa and u.ativada_em is not null
           and u.email is not null
           for no key update;
        if not found then
            raise exception 'Só unidade ativada e com e-mail recebe link de recuperação.'
                using errcode = 'check_violation', constraint = 'token_recuperacao_sem_email';
        end if;
        if (select count(*) from public.token_recuperacao t
             where t.unidade_id = new.unidade_id
               and t.criado_em > now() - interval '1 hour') >= 3 then
            raise exception 'No máximo 3 links de recuperação por hora.'
                using errcode = 'check_violation', constraint = 'token_recuperacao_limite_hora';
        end if;
        if (select count(*) from public.token_recuperacao t
             where t.unidade_id = new.unidade_id
               and t.criado_em > now() - interval '24 hours') >= 6 then
            raise exception 'No máximo 6 links de recuperação por dia.'
                using errcode = 'check_violation', constraint = 'token_recuperacao_limite_dia';
        end if;
        return new;
    end if;

    new.criado_em := old.criado_em;
    new.expira_em := old.expira_em;
    if old.usado_em is not null then
        raise exception 'Este link já foi usado.'
            using errcode = 'check_violation', constraint = 'token_recuperacao_usado';
    end if;
    if new.usado_em is null then
        return new;
    end if;
    -- Vencido: passou 1 hora, ou a senha mudou depois do pedido (quem usa marca o token antes
    -- de gravar a senha nova, na mesma transação).
    select u.senha_trocada_em into trocada from public.unidade u where u.id = old.unidade_id;
    if old.expira_em <= now() or old.criado_em < trocada then
        raise exception 'Este link venceu.'
            using errcode = 'check_violation', constraint = 'token_recuperacao_vencido';
    end if;
    new.usado_em := now();
    return new;
end;
$$;

create trigger token_recuperacao_regras
    before insert or update on token_recuperacao
    for each row execute function public.token_recuperacao_conferir();
"""

NOTIFICACAO_ENVIO = """
-- Um envio por aviso e canal (H-13). A chave única impede mandar duas vezes; as contagens medem
-- a entrega. Nada de endereço, e-mail ou unidade aqui.
create table notificacao_envio (
    id            bigint generated always as identity primary key,
    aviso_id      bigint not null references aviso (id),
    canal         text not null constraint notificacao_envio_canal check (
                      canal in ('push', 'email')),
    situacao      text not null default 'pendente' constraint notificacao_envio_situacao_valor
                      check (situacao in (
                          'pendente', 'enviando', 'concluido', 'desligado', 'interrompido')),
    criado_em     timestamptz not null default now(),
    iniciado_em   timestamptz,
    concluido_em  timestamptz,
    -- destinos: aparelhos (push) ou unidades (e-mail) a alcançar; pulados: e-mails que não
    -- couberam na cota do dia; removidas: inscrições que o serviço de push disse não existir.
    destinos      integer not null default 0,
    entregues     integer not null default 0,
    falhas        integer not null default 0,
    removidas     integer not null default 0,
    pulados       integer not null default 0,
    constraint notificacao_envio_unico unique (aviso_id, canal),
    constraint notificacao_envio_contagens check (
        destinos >= 0 and entregues >= 0 and falhas >= 0 and removidas >= 0 and pulados >= 0
        and entregues + falhas + pulados <= destinos and removidas <= falhas)
);
create index notificacao_envio_em_aberto on notificacao_envio (criado_em)
    where situacao in ('pendente', 'enviando');

create function public.notificacao_envio_conferir() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
begin
    if tg_op = 'INSERT' then
        if new.situacao <> 'pendente' then
            raise exception 'Envio nasce pendente.'
                using errcode = 'check_violation', constraint = 'notificacao_envio_situacao';
        end if;
        new.criado_em := now();
        new.iniciado_em := null;
        new.concluido_em := null;
        return new;
    end if;

    -- pendente → enviando | desligado | interrompido; enviando → concluido | interrompido.
    -- O resto é final.
    if not (
        (old.situacao = 'pendente'
            and new.situacao in ('pendente', 'enviando', 'desligado', 'interrompido'))
        or (old.situacao = 'enviando'
            and new.situacao in ('enviando', 'concluido', 'interrompido'))
    ) then
        raise exception 'Envio na situação % não muda para %.', old.situacao, new.situacao
            using errcode = 'check_violation', constraint = 'notificacao_envio_situacao';
    end if;
    new.criado_em := old.criado_em;
    new.iniciado_em := case when old.situacao = 'pendente' and new.situacao = 'enviando'
                            then now() else old.iniciado_em end;
    new.concluido_em := case when new.situacao in ('concluido', 'desligado', 'interrompido')
                             then now() else old.concluido_em end;
    return new;
end;
$$;

create trigger notificacao_envio_regras
    before insert or update on notificacao_envio
    for each row execute function public.notificacao_envio_conferir();
"""

PERMISSOES = """
grant select, insert, delete on inscricao_push to {app};
grant update (sessao_id, chave_p256dh, chave_auth) on inscricao_push to {app};
grant select, insert, delete on token_recuperacao to {app};
grant update (usado_em) on token_recuperacao to {app};
grant select, insert on notificacao_envio to {app};
grant update (situacao, destinos, entregues, falhas, removidas, pulados)
    on notificacao_envio to {app};
"""


def upgrade() -> None:
    app = _papel_app()
    op.execute(INSCRICAO_PUSH)
    op.execute(TOKEN_RECUPERACAO)
    op.execute(NOTIFICACAO_ENVIO)
    op.execute(PERMISSOES.format(app=app))


def downgrade() -> None:
    # As permissões saem com as tabelas.
    op.execute(
        """
        drop table notificacao_envio, token_recuperacao, inscricao_push;
        drop trigger sessao_sem_push on sessao;
        drop function public.sessao_encerrada_sem_push();
        drop function public.inscricao_push_conferir();
        drop function public.token_recuperacao_conferir();
        drop function public.notificacao_envio_conferir();
        """
    )
