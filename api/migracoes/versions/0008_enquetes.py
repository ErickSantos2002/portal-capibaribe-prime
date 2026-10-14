"""Enquetes (M4): enquete, opções, destino, voto e as opções de cada voto.

Revisão: 0008
Anterior: 0007
Criada em: 2026-10-13

Escrita à mão, no mesmo padrão da 0002 a 0007. Spec: `docs/superpowers/specs/m4-contrato.md`,
seção 2; modelo: `docs/04-modelo-de-dados.md`, seções 3.5 e 4.

As três regras do roadmap ficam aqui, não na API:
- **um voto por unidade** (RN-01): chave primária `voto (enquete_id, unidade_id)`;
- **nada de voto depois do prazo** (H-21): `voto` e `voto_opcao` recusam gravar com o relógio
  do banco em `encerra_em` ou depois;
- **nada de editar depois do 1º voto** (H-20): `enquete` e `enquete_opcao` recusam mudar se há
  voto. A edição trava a linha da enquete; o voto a pede em modo compartilhado: editar e votar
  ao mesmo tempo não passam juntos.

Além disso: enquete encerrada não muda (RF-25), completa no commit (2 a 10 opções, destino),
destino só na criação (o aviso automático tem o mesmo e não muda), voto só de quem está no
destino, completo no commit (escolha única = uma opção), e nada daqui é apagado pelo `app`
menos as opções (edição antes do 1º voto) e as opções do voto (troca, RN-05: o voto anterior
não é guardado).
"""

from collections.abc import Sequence

from alembic import context, op
from sqlalchemy import text

revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _papel_app() -> str:
    """Mesmo cuidado da 0001 a 0007: o papel `app` precisa existir e entra como identificador."""
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
-- A enquete (H-20). Nunca é apagada (RN-05); encerrada, fica com o resultado (RF-25).
create table enquete (
    id                 bigint generated always as identity primary key,
    pergunta           text not null constraint enquete_pergunta_tamanho check (
                           char_length(btrim(pergunta)) between 1 and 200
                           and char_length(pergunta) <= 200),
    multipla_escolha   boolean not null default false,
    -- RF-23: resultado aparece durante a votação ou só no fim.
    mostrar_resultado  text not null default 'durante' constraint enquete_mostrar_resultado
                           check (mostrar_resultado in ('durante', 'so_no_fim')),
    encerra_em         timestamptz not null,
    -- `false` = só os blocos em `enquete_bloco`. Não muda (o aviso automático também não).
    para_todos         boolean not null,
    criada_por         bigint not null references unidade (id),
    criada_em          timestamptz not null default now(),
    editada_em         timestamptz,
    -- Gravada pelo primeiro voto (trigger `voto_marca_a_enquete`): daí em diante, nada
    -- muda. É uma escrita na linha, para a edição concorrente esbarrar nela.
    primeiro_voto_em   timestamptz,
    -- O aviso automático (H-13), criado na mesma transação.
    aviso_id           bigint not null unique references aviso (id),
    constraint enquete_prazo check (encerra_em > criada_em)
);
create index enquete_encerra_em on enquete (encerra_em);

-- De 2 a 10 por enquete (conferido no commit). Editar = apagar e inserir de novo.
create table enquete_opcao (
    id          bigint generated always as identity primary key,
    enquete_id  bigint not null references enquete (id),
    texto       text not null constraint enquete_opcao_texto_tamanho check (
                    char_length(btrim(texto)) between 1 and 100 and char_length(texto) <= 100),
    ordem       smallint not null constraint enquete_opcao_ordem check (ordem between 1 and 10),
    constraint enquete_opcao_ordem_unica unique (enquete_id, ordem),
    constraint enquete_opcao_texto_unico unique (enquete_id, texto),
    -- Alvo da chave estrangeira composta de `voto_opcao`: opção de outra enquete não entra.
    constraint enquete_opcao_da_enquete unique (enquete_id, id)
);

-- Destino quando a enquete não é para todos.
create table enquete_bloco (
    enquete_id  bigint not null references enquete (id),
    bloco_id    bigint not null references bloco (id),
    primary key (enquete_id, bloco_id)
);
create index enquete_bloco_bloco on enquete_bloco (bloco_id);

-- A participação da unidade (H-21). A chave primária é a regra "um voto por unidade" (RN-01).
create table voto (
    enquete_id  bigint not null references enquete (id),
    unidade_id  bigint not null references unidade (id),
    -- Atualizada quando o voto é trocado.
    votado_em   timestamptz not null default now(),
    primary key (enquete_id, unidade_id)
);
create index voto_unidade on voto (unidade_id);

-- Uma linha por opção marcada. O voto anterior não é guardado (modelo, seção 3.5).
create table voto_opcao (
    enquete_id  bigint not null,
    unidade_id  bigint not null,
    opcao_id    bigint not null,
    primary key (enquete_id, unidade_id, opcao_id),
    constraint voto_opcao_do_voto foreign key (enquete_id, unidade_id)
        references voto (enquete_id, unidade_id),
    constraint voto_opcao_da_enquete foreign key (enquete_id, opcao_id)
        references enquete_opcao (enquete_id, id)
);
create index voto_opcao_opcao on voto_opcao (enquete_id, opcao_id);
"""

# Toda função de trigger fixa o search_path com pg_temp por último e usa nomes qualificados
# (dúvida 20 do M0).
REGRAS_DA_ENQUETE = """
-- Datas do banco; prazo no futuro (até 366 dias); depois do encerramento ou do 1º voto, nada
-- muda. Prazo sempre pelo relógio (`clock_timestamp()`), nunca pelo início da transação
-- (`now()`): uma transação aberta antes do prazo não reabre a enquete depois dele.
--
-- "Com voto" é a coluna `primeiro_voto_em`, que o primeiro voto **grava** nesta linha (trigger
-- `voto_marca_a_enquete`), e não só um `exists` em `voto`: uma edição cuja foto (REPEATABLE READ,
-- SERIALIZABLE) é de antes do voto esbarra na linha que o voto mudou e recebe erro de
-- serialização; em READ COMMITTED, espera o voto e vê a coluna preenchida.
create function public.enquete_conferir() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
begin
    if tg_op = 'INSERT' then
        new.criada_em := now();
        new.editada_em := null;
        new.primeiro_voto_em := null;
    else
        -- O primeiro voto marca a enquete (só isso muda, de nulo para a hora, e com voto de
        -- verdade na mesma transação). Prazo e destino o voto já conferiu.
        if old.primeiro_voto_em is null and new.primeiro_voto_em is not null
           and (new.pergunta, new.multipla_escolha, new.mostrar_resultado, new.encerra_em,
                new.para_todos, new.criada_por, new.criada_em, new.editada_em, new.aviso_id)
               is not distinct from
               (old.pergunta, old.multipla_escolha, old.mostrar_resultado, old.encerra_em,
                old.para_todos, old.criada_por, old.criada_em, old.editada_em, old.aviso_id) then
            if not exists (select 1 from public.voto v where v.enquete_id = old.id) then
                raise exception 'Só o voto marca a enquete como votada.'
                    using errcode = 'check_violation', constraint = 'enquete_primeiro_voto';
            end if;
            new.primeiro_voto_em := clock_timestamp();
            return new;
        end if;
        if old.primeiro_voto_em is not null
           or exists (select 1 from public.voto v where v.enquete_id = old.id) then
            raise exception 'A enquete já recebeu votos: nada nela muda mais.'
                using errcode = 'check_violation', constraint = 'enquete_com_voto';
        end if;
        if old.encerra_em <= clock_timestamp() then
            raise exception 'Enquete encerrada não muda.'
                using errcode = 'check_violation', constraint = 'enquete_encerrada';
        end if;
        if new.primeiro_voto_em is not null then
            raise exception 'Só o voto marca a enquete como votada.'
                using errcode = 'check_violation', constraint = 'enquete_primeiro_voto';
        end if;
        new.criada_em := old.criada_em;
        new.editada_em := now();
    end if;
    if new.encerra_em <= clock_timestamp()
       or new.encerra_em > clock_timestamp() + interval '366 days' then
        raise exception 'O término da enquete precisa ser no futuro e em até 1 ano.'
            using errcode = 'check_violation', constraint = 'enquete_encerramento';
    end if;
    return new;
end;
$$;

create trigger enquete_regras
    before insert or update on enquete
    for each row execute function public.enquete_conferir();

-- No commit: de 2 a 10 opções; se não é para todos, pelo menos um bloco; e o aviso automático
-- com exatamente o mesmo destino (senão a pergunta aparece, pelo botão do aviso, para quem não
-- está no destino da enquete).
create function public.enquete_conferir_completa() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
declare
    opcoes integer;
    todos boolean;
    aviso bigint;
begin
    select e.para_todos, e.aviso_id into todos, aviso from public.enquete e where e.id = new.id;
    select count(*) into opcoes from public.enquete_opcao o where o.enquete_id = new.id;
    if opcoes not between 2 and 10 then
        raise exception 'A enquete precisa de 2 a 10 opções.'
            using errcode = 'check_violation', constraint = 'enquete_completa';
    end if;
    if not todos
       and not exists (select 1 from public.enquete_bloco b where b.enquete_id = new.id) then
        raise exception 'Enquete sem destino: escolha pelo menos um bloco.'
            using errcode = 'check_violation', constraint = 'enquete_completa';
    end if;
    if (select a.para_todos from public.aviso a where a.id = aviso) is distinct from todos
       or exists (select b.bloco_id from public.enquete_bloco b where b.enquete_id = new.id
                  except
                  select b.bloco_id from public.aviso_bloco b where b.aviso_id = aviso)
       or exists (select b.bloco_id from public.aviso_bloco b where b.aviso_id = aviso
                  except
                  select b.bloco_id from public.enquete_bloco b where b.enquete_id = new.id) then
        raise exception 'O aviso automático precisa ter o mesmo destino da enquete.'
            using errcode = 'check_violation', constraint = 'enquete_destino_do_aviso';
    end if;
    return null;
end;
$$;

create constraint trigger enquete_completa
    after insert on enquete
    deferrable initially deferred
    for each row execute function public.enquete_conferir_completa();

-- O aviso de uma enquete não ganha bloco depois da transação que criou a enquete.
create function public.aviso_bloco_da_enquete() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
begin
    if exists (select 1 from public.enquete e
                where e.aviso_id = new.aviso_id and e.criada_em is distinct from now()) then
        raise exception 'O destino do aviso de uma enquete não muda.'
            using errcode = 'check_violation', constraint = 'enquete_destino_do_aviso';
    end if;
    return new;
end;
$$;

create trigger aviso_bloco_da_enquete
    before insert on aviso_bloco
    for each row execute function public.aviso_bloco_da_enquete();

-- Opção nova ou apagada: a enquete está aberta e sem voto. Trava a linha dela (como a edição):
-- um voto em andamento termina antes, e o primeiro voto já marcou a linha.
create function public.enquete_opcao_conferir() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
declare
    alvo bigint := case when tg_op = 'DELETE' then old.enquete_id else new.enquete_id end;
    encerra timestamptz;
    votada timestamptz;
begin
    -- Trava a linha da enquete (`for no key update`): com a foto de antes do 1º voto
    -- (REPEATABLE READ), travar a linha que o voto mudou é erro de serialização, e não uma
    -- opção nova numa enquete votada. Trava de escrita, e não `for share`: duas edições ao
    -- mesmo tempo fazem fila, em vez de uma esperar a outra para subir a trava (impasse).
    select e.encerra_em, e.primeiro_voto_em into encerra, votada
      from public.enquete e where e.id = alvo for no key update;
    if not found then
        return new;  -- a chave estrangeira recusa
    end if;
    if votada is not null or exists (select 1 from public.voto v where v.enquete_id = alvo) then
        raise exception 'A enquete já recebeu votos: as opções não mudam mais.'
            using errcode = 'check_violation', constraint = 'enquete_com_voto';
    end if;
    if encerra <= clock_timestamp() then
        raise exception 'Enquete encerrada não muda.'
            using errcode = 'check_violation', constraint = 'enquete_encerrada';
    end if;
    if tg_op = 'DELETE' then
        return old;
    end if;
    if (select count(*) from public.enquete_opcao o where o.enquete_id = alvo) >= 10 then
        raise exception 'No máximo 10 opções por enquete.'
            using errcode = 'check_violation', constraint = 'enquete_opcoes';
    end if;
    return new;
end;
$$;

create trigger enquete_opcao_regras
    before insert or delete on enquete_opcao
    for each row execute function public.enquete_opcao_conferir();

-- Editar as opções (apagar e inserir) também tem de terminar com 2 a 10, no commit.
create function public.enquete_opcao_conferir_completa() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
declare
    alvo bigint := case when tg_op = 'DELETE' then old.enquete_id else new.enquete_id end;
begin
    if (select count(*) from public.enquete_opcao o where o.enquete_id = alvo)
       not between 2 and 10 then
        raise exception 'A enquete precisa de 2 a 10 opções.'
            using errcode = 'check_violation', constraint = 'enquete_completa';
    end if;
    return null;
end;
$$;

create constraint trigger enquete_opcao_completa
    after insert or delete on enquete_opcao
    deferrable initially deferred
    for each row execute function public.enquete_opcao_conferir_completa();

-- Destino: nunca numa enquete para todos, e só na transação que criou a enquete.
create function public.enquete_bloco_conferir() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
declare
    todos boolean;
    criada timestamptz;
begin
    select e.para_todos, e.criada_em into todos, criada
      from public.enquete e where e.id = new.enquete_id;
    if not found then
        return new;  -- a chave estrangeira recusa
    end if;
    if todos then
        raise exception 'Enquete para todos os blocos não tem lista de blocos.'
            using errcode = 'check_violation', constraint = 'enquete_bloco_destino';
    end if;
    if criada is distinct from now() then
        raise exception 'O destino entra junto com a enquete, nunca depois.'
            using errcode = 'check_violation', constraint = 'enquete_destino_fechado';
    end if;
    return new;
end;
$$;

create trigger enquete_bloco_regras
    before insert on enquete_bloco
    for each row execute function public.enquete_bloco_conferir();
"""

REGRAS_DO_VOTO = """
-- Votar ou trocar o voto: enquete aberta pelo relógio da gravação e unidade no destino. Pede a
-- linha da enquete `for share`: uma edição em andamento termina antes (e o voto vê o que ela
-- gravou). O destino é conferido pelo `bloco_id` da unidade, que o `app` não pode mudar (as
-- permissões em `unidade` são por coluna desde esta migração).
create function public.voto_conferir() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
declare
    encerra timestamptz;
    todos boolean;
    votada timestamptz;
begin
    -- Quem pode ser o primeiro voto vai marcar a enquete (`voto_marca_a_enquete`): pede a linha
    -- já para escrever. Se pedisse `for share` e só depois escrevesse, dois primeiros votos ao
    -- mesmo tempo travariam um ao outro (impasse). Os outros votos só leem (`for share`).
    select e.primeiro_voto_em into votada from public.enquete e where e.id = new.enquete_id;
    if tg_op = 'INSERT' and votada is null then
        select e.encerra_em, e.para_todos into encerra, todos
          from public.enquete e where e.id = new.enquete_id for no key update;
    else
        select e.encerra_em, e.para_todos into encerra, todos
          from public.enquete e where e.id = new.enquete_id for share;
    end if;
    if not found then
        return new;  -- a chave estrangeira recusa
    end if;
    if clock_timestamp() >= encerra then
        raise exception 'A enquete já terminou: o voto não pode mais ser dado nem trocado.'
            using errcode = 'check_violation', constraint = 'enquete_encerrada';
    end if;
    if tg_op = 'UPDATE' then
        new.enquete_id := old.enquete_id;
        new.unidade_id := old.unidade_id;
    end if;
    if not todos and not exists (
        select 1 from public.enquete_bloco b
          join public.unidade u on u.bloco_id = b.bloco_id
         where b.enquete_id = new.enquete_id and u.id = new.unidade_id) then
        raise exception 'Esta enquete não é para o bloco desta unidade.'
            using errcode = 'check_violation', constraint = 'voto_fora_do_destino';
    end if;
    new.votado_em := clock_timestamp();
    return new;
end;
$$;

create trigger voto_regras
    before insert or update on voto
    for each row execute function public.voto_conferir();

-- O primeiro voto grava na linha da enquete (`primeiro_voto_em`): é essa escrita que faz uma
-- edição concorrente, em qualquer nível de isolamento, esperar ou falhar (achado 1 da revisão).
-- Os votos seguintes não mexem nela (não disputam a linha à toa).
create function public.voto_marca_a_enquete() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
begin
    update public.enquete e set primeiro_voto_em = clock_timestamp()
     where e.id = new.enquete_id and e.primeiro_voto_em is null;
    return null;
end;
$$;

create trigger voto_marca_a_enquete
    after insert on voto
    for each row execute function public.voto_marca_a_enquete();

-- Conferência do commit, comum ao voto e às opções dele: pelo menos uma opção; na escolha
-- única, exatamente uma; e a enquete ainda aberta no commit (um voto gravado antes do prazo e
-- confirmado depois é recusado).
create function public.voto_conferir_completo() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
declare
    alvo_enquete bigint := case when tg_op = 'DELETE' then old.enquete_id else new.enquete_id end;
    alvo_unidade bigint := case when tg_op = 'DELETE' then old.unidade_id else new.unidade_id end;
    marcadas integer;
    multipla boolean;
    encerra timestamptz;
begin
    select e.multipla_escolha, e.encerra_em into multipla, encerra
      from public.enquete e where e.id = alvo_enquete;
    if clock_timestamp() >= encerra then
        raise exception 'A enquete já terminou: o voto não pode mais ser dado nem trocado.'
            using errcode = 'check_violation', constraint = 'enquete_encerrada';
    end if;
    select count(*) into marcadas from public.voto_opcao o
     where o.enquete_id = alvo_enquete and o.unidade_id = alvo_unidade;
    if marcadas < 1 or (not multipla and marcadas <> 1) then
        raise exception 'Voto com opções erradas: escolha uma opção (ou mais, se a enquete deixa).'
            using errcode = 'check_violation', constraint = 'voto_completo';
    end if;
    return null;
end;
$$;

create constraint trigger voto_completo
    after insert or update on voto
    deferrable initially deferred
    for each row execute function public.voto_conferir_completo();

-- Opção marcada ou desmarcada: o voto da unidade existe (e fica travado: duas trocas da mesma
-- unidade nunca misturam as opções) e a enquete está aberta. Se o voto não aparece para esta
-- transação (foto de antes dele, em REPEATABLE READ), a opção é recusada: sem isso, a conferência
-- do commit contaria só as opções que esta transação enxerga.
create function public.voto_opcao_conferir() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
declare
    alvo_enquete bigint := case when tg_op = 'DELETE' then old.enquete_id else new.enquete_id end;
    alvo_unidade bigint := case when tg_op = 'DELETE' then old.unidade_id else new.unidade_id end;
    encerra timestamptz;
begin
    perform 1 from public.voto v
     where v.enquete_id = alvo_enquete and v.unidade_id = alvo_unidade for no key update;
    if not found then
        raise exception 'Grave o voto antes das opções dele.'
            using errcode = 'check_violation', constraint = 'voto_completo';
    end if;
    select e.encerra_em into encerra from public.enquete e where e.id = alvo_enquete for share;
    if clock_timestamp() >= encerra then
        raise exception 'A enquete já terminou: o voto não pode mais ser dado nem trocado.'
            using errcode = 'check_violation', constraint = 'enquete_encerrada';
    end if;
    if tg_op = 'DELETE' then
        return old;
    end if;
    return new;
end;
$$;

create trigger voto_opcao_regras
    before insert or delete on voto_opcao
    for each row execute function public.voto_opcao_conferir();

-- A mesma conferência do commit (as duas tabelas têm `enquete_id` e `unidade_id`): trocar o voto
-- apagando e inserindo opções também termina com o voto completo.
create constraint trigger voto_opcao_completo
    after insert or delete on voto_opcao
    deferrable initially deferred
    for each row execute function public.voto_conferir_completo();
"""

# Achado 3 da revisão: desde a 0001 o `app` tinha UPDATE na tabela `unidade` inteira e podia
# mudar o bloco de uma unidade para votar fora do destino. Agora só as colunas que a API muda
# (primeiro acesso, Minha unidade, apagar meus dados, reset, troca de senha, e-mail, e `ativa`,
# que o H-10 vai usar). Bloco, número, andar, login e datas: só o `dono` (H-10, M5). O número
# do bloco também (a trigger da 0001 renumera as unidades dele); o `app` fica com nome e `ativo`.
UNIDADE_POR_COLUNA = """
revoke update on unidade from {app};
grant update (senha_hash, precisa_trocar_senha, ativada_em, responsavel_nome, celular, email,
              receber_avisos_email, ativa) on unidade to {app};
revoke update on bloco from {app};
grant update (nome, ativo) on bloco to {app};
"""

# Spec, seção 2.7: nada é apagado, menos opção (edição antes do 1º voto) e opção do voto (troca).
PERMISSOES = """
grant select, insert on enquete, enquete_bloco, voto to {app};
grant update (pergunta, multipla_escolha, mostrar_resultado, encerra_em) on enquete to {app};
-- Só a trigger do primeiro voto escreve aqui (e a trigger da enquete não deixa outra coisa).
grant update (primeiro_voto_em) on enquete to {app};
grant select, insert, delete on enquete_opcao, voto_opcao to {app};
grant update (votado_em) on voto to {app};
"""


def upgrade() -> None:
    app = _papel_app()
    op.execute(TABELAS)
    op.execute(REGRAS_DA_ENQUETE)
    op.execute(REGRAS_DO_VOTO)
    op.execute(PERMISSOES.format(app=app))
    op.execute(UNIDADE_POR_COLUNA.format(app=app))


def downgrade() -> None:
    app = _papel_app()
    # Volta o UPDATE nas tabelas `unidade` e `bloco` inteiras (0001), e o da coluna da 0006.
    op.execute(
        f"""
        revoke update on unidade from {app};
        grant update on unidade to {app};
        grant update (receber_avisos_email) on unidade to {app};
        revoke update on bloco from {app};
        grant update on bloco to {app};
        """
    )
    # As outras permissões e as triggers saem com as tabelas.
    op.execute(
        """
        drop trigger aviso_bloco_da_enquete on aviso_bloco;
        drop function public.aviso_bloco_da_enquete();
        drop table voto_opcao, voto, enquete_bloco, enquete_opcao, enquete;
        drop function public.voto_opcao_conferir();
        drop function public.voto_conferir_completo();
        drop function public.voto_marca_a_enquete();
        drop function public.voto_conferir();
        drop function public.enquete_bloco_conferir();
        drop function public.enquete_opcao_conferir_completa();
        drop function public.enquete_opcao_conferir();
        drop function public.enquete_conferir_completa();
        drop function public.enquete_conferir();
        """
    )
