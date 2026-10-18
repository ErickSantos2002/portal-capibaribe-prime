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
    -- Só dígitos: DDD sem zero e, depois dele, celular (9 e mais 8 dígitos) ou fixo (começa de
    -- 2 a 5, com 8 dígitos). Celular sem o nono dígito não entra: a API põe o 9 antes de
    -- gravar, senão o mesmo número entraria duas vezes, com e sem ele.
    telefone       text not null constraint prestador_telefone_formato check (
                       telefone ~ '^[1-9]{2}(9[0-9]{8}|[2-5][0-9]{7})$'),
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
    resolvido_por      bigint references unidade (id)
);
create unique index aviso_servico_aberto on aviso_servico (prestador_id, unidade_id)
    where resolvido_em is null;
-- O limite do dia conta por unidade e data.
create index aviso_servico_unidade on aviso_servico (unidade_id, criado_em);
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

# Toda função de trigger fixa o search_path com pg_temp por último e usa nomes qualificados
# (dúvida 20 do M0). O apagar não tem trigger: "apagar meus dados" e o reset apagam até a
# opinião escondida; a recusa de a unidade apagar a própria opinião escondida é da rota.
REGRAS = """
-- Indicar: datas do banco, unidade ativa e no máximo 10 por unidade a cada 24 horas. Corrigir:
-- nada muda no escondido (menos perder o autor), o autor só vira nulo, esconder é de nulo para
-- a hora e não volta.
create function public.prestador_conferir() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
begin
    if tg_op = 'INSERT' then
        new.criado_em := now();
        new.editado_em := null;
        new.escondido_em := null;
        new.escondido_por := null;
        -- Trava a unidade: indicações ao mesmo tempo contam umas com as outras.
        perform 1 from public.unidade u
         where u.id = new.criado_por and u.ativa for no key update;
        if not found then
            raise exception 'Só unidade ativa indica um prestador.'
                using errcode = 'check_violation', constraint = 'indicacao_de_unidade_inativa';
        end if;
        if (select count(*) from public.prestador p
             where p.criado_por = new.criado_por
               and p.criado_em > now() - interval '24 hours') >= 10 then
            raise exception 'No máximo 10 indicações por apartamento a cada 24 horas.'
                using errcode = 'check_violation', constraint = 'prestador_limite_dia';
        end if;
        return new;
    end if;
    if new.criado_por is distinct from old.criado_por and new.criado_por is not null then
        raise exception 'Quem indicou não muda (só deixa de existir).'
            using errcode = 'check_violation', constraint = 'prestador_autor_fixo';
    end if;
    if old.escondido_em is not null then
        -- Escondido não muda, menos perder o autor ("apagar meus dados", reset).
        if (new.categoria_id, new.nome, new.nome_busca, new.telefone, new.instagram,
            new.escondido_em, new.escondido_por)
           is distinct from
           (old.categoria_id, old.nome, old.nome_busca, old.telefone, old.instagram,
            old.escondido_em, old.escondido_por) then
            raise exception 'Prestador escondido não muda.'
                using errcode = 'check_violation', constraint = 'prestador_escondido';
        end if;
    elsif new.escondido_em is not null then
        new.escondido_em := now();
    end if;
    new.criado_em := old.criado_em;
    if (new.categoria_id, new.nome, new.telefone, new.instagram)
       is distinct from (old.categoria_id, old.nome, old.telefone, old.instagram) then
        new.editado_em := now();
    else
        new.editado_em := old.editado_em;
    end if;
    return new;
end;
$$;

create trigger prestador_regras
    before insert or update on prestador
    for each row execute function public.prestador_conferir();

-- Opinar: unidade ativa, prestador visível, no máximo 30 novas por unidade a cada 24 horas
-- (contando as que ela mesma apagou, pelo histórico: senão apagar e escrever de novo não teria
-- fim). Mudar a opinião é UPDATE e não conta. Esconder (a gestão) só carimba e trava a linha.
create function public.opiniao_conferir() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
begin
    if tg_op = 'INSERT' then
        new.criada_em := now();
        new.editada_em := null;
        new.escondida_em := null;
        new.escondida_por := null;
        if exists (select 1 from public.prestador p
                    where p.id = new.prestador_id and p.escondido_em is not null) then
            raise exception 'Prestador escondido não recebe opinião.'
                using errcode = 'check_violation', constraint = 'prestador_escondido';
        end if;
        perform 1 from public.unidade u
         where u.id = new.unidade_id and u.ativa for no key update;
        if not found then
            if exists (select 1 from public.unidade u where u.id = new.unidade_id) then
                raise exception 'Só unidade ativa dá opinião.'
                    using errcode = 'check_violation', constraint = 'indicacao_de_unidade_inativa';
            end if;
            return new;  -- a chave estrangeira recusa
        end if;
        if (select count(*) from public.opiniao_servico o
             where o.unidade_id = new.unidade_id
               and o.criada_em > now() - interval '24 hours')
           + (select count(*) from public.historico h
               where h.acao = 'indicacao_opiniao_apagada'
                 and h.unidade_id = new.unidade_id
                 and h.ocorrido_em > now() - interval '24 hours') >= 30 then
            raise exception 'No máximo 30 opiniões novas por apartamento a cada 24 horas.'
                using errcode = 'check_violation', constraint = 'opiniao_limite_dia';
        end if;
        return new;
    end if;
    if (new.prestador_id, new.unidade_id) is distinct from (old.prestador_id, old.unidade_id) then
        raise exception 'A opinião não troca de prestador nem de unidade.'
            using errcode = 'check_violation', constraint = 'opiniao_fixa';
    end if;
    if old.escondida_em is not null then
        raise exception 'A gestão escondeu esta opinião: ela não muda mais.'
            using errcode = 'check_violation', constraint = 'opiniao_escondida';
    end if;
    new.criada_em := old.criada_em;
    if new.escondida_em is not null then
        -- Esconder não muda o que a opinião diz.
        if (new.recomenda, new.comentario) is distinct from (old.recomenda, old.comentario) then
            raise exception 'Esconder a opinião não muda o que ela diz.'
                using errcode = 'check_violation', constraint = 'opiniao_escondida';
        end if;
        new.escondida_em := now();
        new.editada_em := old.editada_em;
        return new;
    end if;
    if exists (select 1 from public.unidade u where u.id = new.unidade_id and not u.ativa) then
        raise exception 'Só unidade ativa muda a opinião.'
            using errcode = 'check_violation', constraint = 'indicacao_de_unidade_inativa';
    end if;
    if exists (select 1 from public.prestador p
                where p.id = new.prestador_id and p.escondido_em is not null) then
        raise exception 'Prestador escondido não recebe opinião.'
            using errcode = 'check_violation', constraint = 'prestador_escondido';
    end if;
    new.editada_em := now();
    return new;
end;
$$;

create trigger opiniao_regras
    before insert or update on opiniao_servico
    for each row execute function public.opiniao_conferir();

-- Avisar: unidade ativa, prestador visível e no máximo 10 por unidade a cada 24 horas (o
-- primeiro aviso de um prestador manda e-mail para a administração; sem teto, uma unidade
-- gastaria a cota do Gmail do dia). Depois, só resolver (de nulo para a hora) muda.
create function public.aviso_servico_conferir() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
begin
    if tg_op = 'INSERT' then
        new.criado_em := now();
        new.resolvido_em := null;
        new.resolvido_por := null;
        if exists (select 1 from public.prestador p
                    where p.id = new.prestador_id and p.escondido_em is not null) then
            raise exception 'Prestador escondido não recebe aviso.'
                using errcode = 'check_violation', constraint = 'prestador_escondido';
        end if;
        -- Trava a unidade: avisos ao mesmo tempo contam uns com os outros.
        perform 1 from public.unidade u
         where u.id = new.unidade_id and u.ativa for no key update;
        if not found then
            if exists (select 1 from public.unidade u where u.id = new.unidade_id) then
                raise exception 'Só unidade ativa avisa a gestão.'
                    using errcode = 'check_violation', constraint = 'indicacao_de_unidade_inativa';
            end if;
            return new;  -- a chave estrangeira recusa
        end if;
        if (select count(*) from public.aviso_servico a
             where a.unidade_id = new.unidade_id
               and a.criado_em > now() - interval '24 hours') >= 10 then
            raise exception 'No máximo 10 avisos por apartamento a cada 24 horas.'
                using errcode = 'check_violation', constraint = 'aviso_servico_limite_dia';
        end if;
        return new;
    end if;
    if (new.prestador_id, new.unidade_id, new.motivo, new.criado_em)
       is distinct from (old.prestador_id, old.unidade_id, old.motivo, old.criado_em)
       or (old.resolvido_em is not null
           and (new.resolvido_em, new.resolvido_por)
               is distinct from (old.resolvido_em, old.resolvido_por)) then
        raise exception 'O aviso não muda; só é resolvido, uma vez.'
            using errcode = 'check_violation', constraint = 'aviso_servico_fixo';
    end if;
    if old.resolvido_em is null and new.resolvido_em is not null then
        new.resolvido_em := now();
    end if;
    return new;
end;
$$;

create trigger aviso_servico_regras
    before insert or update on aviso_servico
    for each row execute function public.aviso_servico_conferir();
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
grant update (resolvido_em, resolvido_por), delete on aviso_servico to {app};
"""


def upgrade() -> None:
    app = _papel_app()
    op.execute(TABELAS)
    op.execute(CARGA)
    op.execute(REGRAS)
    op.execute(PERMISSOES.format(app=app))


def downgrade() -> None:
    # As permissões e as triggers saem com as tabelas; as funções, depois.
    op.execute(
        """
        drop table aviso_servico, opiniao_servico, prestador, categoria_servico;
        drop function public.aviso_servico_conferir();
        drop function public.opiniao_conferir();
        drop function public.prestador_conferir();
        """
    )
