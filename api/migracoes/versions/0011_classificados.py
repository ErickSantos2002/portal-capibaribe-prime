"""Classificados entre vizinhos: categorias, anúncio, foto do anúncio e aviso à gestão.

Revisão: 0011
Anterior: 0010
Criada em: 2026-10-20

Escrita à mão, no mesmo padrão da 0002 a 0010. Spec:
`docs/superpowers/specs/2026-10-20-classificados-design.md`, seções 4 a 6; as fotos: ADR-0012.

As regras ficam aqui, não na API:
- **situação**: `ativo` ↔ `reservado` → `encerrado` (com motivo); encerrado não volta; o tipo
  `procura` (quem procura algo) nunca fica reservado e encerra com "encontrei" ou "desisti";
- **vence em 30 dias** depois de publicar ou renovar (o banco calcula `vence_em`); vencido só
  renova ou encerra; renovar só vencido ou a menos de 7 dias de vencer;
- **escondido pela gestão** fica travado: só o dono encerra;
- **5 anúncios novos por unidade a cada 24 horas** e **10 abertos** (ativo ou reservado, não
  vencidos);
- **até 4 fotos por anúncio**, da mesma unidade, e **40 fotos enviadas por unidade a cada 24
  horas** (as descartadas contam enquanto a linha existe: a faxina só as apaga depois de 1 dia);
- **um aviso aberto por unidade e anúncio** (índice único parcial) e 10 avisos por unidade a
  cada 24 horas;
- anúncio com foto presa não é apagado (chave estrangeira sem cascata), e só a linha da foto
  descartada é apagada: quem apaga descarta as fotos antes, e o objeto no bucket nunca fica órfão;
- só unidade ativa, com o primeiro acesso feito, anuncia, envia foto e avisa (a que acabou de
  passar por "apagar meus dados" ou pelo reset não consegue, nem de outro aparelho);
- vencido, encerrado e escondido não recebem foto nova;
- o `app` não apaga categoria.
"""

from collections.abc import Sequence

from alembic import context, op
from sqlalchemy import text

revision: str = "0011"
down_revision: str | Sequence[str] | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _papel_app() -> str:
    """Mesmo cuidado da 0001 a 0010: o papel `app` precisa existir e entra como identificador."""
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
-- Com a carga abaixo. A administração acrescenta e renomeia; nunca apaga.
create table categoria_classificado (
    id         bigint generated always as identity primary key,
    nome       text not null constraint categoria_classificado_nome_tamanho check (
                   char_length(nome) between 2 and 40 and nome = btrim(nome)),
    ordem      smallint not null,
    criada_em  timestamptz not null default now()
);
create unique index categoria_classificado_nome_unico on categoria_classificado (lower(nome));

-- O anúncio é da unidade: some com "apagar meus dados", o reset e a faxina (vencido há 30 dias,
-- encerrado há 7).
create table anuncio (
    id                   bigint generated always as identity primary key,
    unidade_id           bigint not null references unidade (id),
    categoria_id         bigint not null references categoria_classificado (id),
    tipo                 text not null constraint anuncio_tipo check (
                             tipo in ('venda', 'troca', 'doacao', 'procura')),
    titulo               text not null constraint anuncio_titulo_tamanho check (
                             char_length(titulo) between 3 and 80 and titulo = btrim(titulo)),
    descricao            text constraint anuncio_descricao_tamanho check (
                             descricao is null or (char_length(btrim(descricao)) between 1 and 1000
                             and char_length(descricao) <= 1000)),
    -- Só na venda; nulo = "a combinar". Até R$ 100.000.
    preco_centavos       integer constraint anuncio_preco check (
                             preco_centavos is null
                             or (tipo = 'venda' and preco_centavos between 0 and 10000000)),
    -- Só dígitos, a mesma regra do telefone do prestador (0010): DDD sem zero, celular com o 9.
    contato              text not null constraint anuncio_contato_formato check (
                             contato ~ '^[1-9]{2}(9[0-9]{8}|[2-5][0-9]{7})$'),
    situacao             text not null default 'ativo' constraint anuncio_situacao check (
                             situacao in ('ativo', 'reservado', 'encerrado')),
    motivo_encerramento  text constraint anuncio_motivo_encerramento check (
                             motivo_encerramento in ('vendi', 'troquei', 'doei', 'desisti',
                                                     'encontrei')),
    publicado_em         timestamptz not null default now(),
    renovado_em          timestamptz,
    vence_em             timestamptz not null default now() + interval '30 days',
    editado_em           timestamptz,
    encerrado_em         timestamptz,
    escondido_em         timestamptz,
    escondido_por        bigint references unidade (id),
    -- Encerrado tem motivo e data; aberto não tem nenhum dos dois.
    constraint anuncio_encerramento check (
        (situacao = 'encerrado') = (motivo_encerramento is not null)
        and (situacao = 'encerrado') = (encerrado_em is not null)),
    -- Escondido tem a data e quem escondeu, ou nenhum dos dois (revisão B1).
    constraint anuncio_escondimento check ((escondido_em is null) = (escondido_por is null)),
    -- "Procura" encerra com "Encontrei" ou "Desisti"; os outros tipos não encontram.
    constraint anuncio_motivo_do_tipo check (
        motivo_encerramento is null or motivo_encerramento = 'desisti'
        or (tipo = 'procura') = (motivo_encerramento = 'encontrei'))
);
-- Os limites do dia e de abertos contam por unidade; a lista e a faxina, por data.
create index anuncio_unidade on anuncio (unidade_id, publicado_em);
create index anuncio_vence on anuncio (vence_em);

-- A foto do anúncio (ADR-0012). Mora em `classificados/<chave>`, pasta sem trava, e é apagada de
-- verdade. Pendente (sem `confirmada_em`) → pronta (confirmada, sem anúncio) → no anúncio (com
-- ordem) → descartada (`descartada_em`: o objeto é apagado, e a linha, na faxina).
create table anuncio_foto (
    id             bigint generated always as identity primary key,
    -- Sem cascata: apagar o anúncio com foto presa falha, para nenhum objeto ficar órfão.
    anuncio_id     bigint references anuncio (id),
    unidade_id     bigint not null references unidade (id),
    -- 128 bits aleatórios, gerados pela API.
    chave          text not null constraint anuncio_foto_chave check (chave ~ '^[0-9a-f]{32}$'),
    tipo           text not null constraint anuncio_foto_tipo check (
                       tipo in ('image/jpeg', 'image/png', 'image/webp')),
    bytes          integer not null constraint anuncio_foto_bytes check (
                       bytes between 1 and 10485760),
    -- A primeira (0) é a capa.
    ordem          smallint constraint anuncio_foto_ordem check (ordem between 0 and 3),
    enviada_em     timestamptz not null default now(),
    confirmada_em  timestamptz,
    descartada_em  timestamptz,
    constraint anuncio_foto_chave_unica unique (chave),
    -- No anúncio: confirmada, não descartada e com ordem. Fora dele: sem ordem.
    constraint anuncio_foto_estado check (
        (anuncio_id is null) = (ordem is null)
        and (anuncio_id is null or (confirmada_em is not null and descartada_em is null)))
);
create index anuncio_foto_anuncio on anuncio_foto (anuncio_id);
create index anuncio_foto_unidade on anuncio_foto (unidade_id, enviada_em);

-- "Tem algo errado aqui?": só a gestão vê, sem a placa de quem avisou. Vai junto com o anúncio.
create table aviso_anuncio (
    id             bigint generated always as identity primary key,
    anuncio_id     bigint not null references anuncio (id) on delete cascade,
    unidade_id     bigint not null references unidade (id),
    motivo         text constraint aviso_anuncio_motivo_tamanho check (
                       motivo is null or (char_length(btrim(motivo)) between 1 and 300
                       and char_length(motivo) <= 300)),
    criado_em      timestamptz not null default now(),
    resolvido_em   timestamptz,
    resolvido_por  bigint references unidade (id)
);
create unique index aviso_anuncio_aberto on aviso_anuncio (anuncio_id, unidade_id)
    where resolvido_em is null;
create index aviso_anuncio_unidade on aviso_anuncio (unidade_id, criado_em);
"""

# A mesma lista de `app.modelos.classificados.CATEGORIAS_INICIAIS` (congelada aqui; o teste
# `test_carga_da_0011_igual_a_constante` confere). "Outros" fica sempre por último.
CARGA = """
insert into categoria_classificado (nome, ordem) values
    ('Móveis', 10),
    ('Eletrodomésticos', 20),
    ('Eletrônicos', 30),
    ('Material de obra e acabamento', 40),
    ('Decoração', 50),
    ('Utilidades domésticas', 60),
    ('Infantil', 70),
    ('Outros', 999);
"""

# Toda função de trigger fixa o search_path com pg_temp por último e usa nomes qualificados
# (dúvida 20 do M0). O apagar não tem trigger: a faxina, "apagar meus dados" e o reset apagam.
REGRAS = """
-- Anunciar: datas do banco, unidade ativa, 5 por dia e 10 abertos. Depois: a situação só anda
-- para a frente (o reservado volta a ativo), o vencido só renova ou encerra, o escondido só
-- encerra, e o encerrado não muda mais (a gestão ainda o esconde).
create function public.anuncio_conferir() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
declare
    renovando boolean;
    encerrando boolean;
    escondendo boolean;
    conteudo_mudou boolean;
begin
    if tg_op = 'INSERT' then
        new.publicado_em := now();
        new.vence_em := now() + interval '30 days';
        new.situacao := 'ativo';
        new.renovado_em := null;
        new.editado_em := null;
        new.motivo_encerramento := null;
        new.encerrado_em := null;
        new.escondido_em := null;
        new.escondido_por := null;
        -- Trava a unidade: anúncios ao mesmo tempo contam uns com os outros.
        perform 1 from public.unidade u
         where u.id = new.unidade_id and u.ativa and not u.precisa_trocar_senha
           and u.ativada_em is not null
           for no key update;
        if not found then
            if exists (select 1 from public.unidade u where u.id = new.unidade_id) then
                raise exception 'Só unidade ativa anuncia.'
                    using errcode = 'check_violation',
                          constraint = 'classificado_de_unidade_inativa';
            end if;
            return new;  -- a chave estrangeira recusa
        end if;
        if (select count(*) from public.anuncio a
             where a.unidade_id = new.unidade_id
               and a.publicado_em > now() - interval '24 hours') >= 5 then
            raise exception 'No máximo 5 anúncios novos por apartamento a cada 24 horas.'
                using errcode = 'check_violation', constraint = 'anuncio_limite_dia';
        end if;
        if (select count(*) from public.anuncio a
             where a.unidade_id = new.unidade_id
               and a.situacao in ('ativo', 'reservado')
               and a.vence_em > now()) >= 10 then
            raise exception 'No máximo 10 anúncios abertos por apartamento.'
                using errcode = 'check_violation', constraint = 'anuncio_limite_abertos';
        end if;
        return new;
    end if;

    if (new.unidade_id, new.publicado_em) is distinct from (old.unidade_id, old.publicado_em) then
        raise exception 'O anúncio não troca de unidade nem de data de publicação.'
            using errcode = 'check_violation', constraint = 'anuncio_fixo';
    end if;
    escondendo := old.escondido_em is null and new.escondido_em is not null;
    if old.escondido_em is not null
       and (new.escondido_em, new.escondido_por)
           is distinct from (old.escondido_em, old.escondido_por) then
        raise exception 'O anúncio escondido não volta.'
            using errcode = 'check_violation', constraint = 'anuncio_escondido';
    end if;
    renovando := new.renovado_em is distinct from old.renovado_em;
    encerrando := new.situacao = 'encerrado' and old.situacao <> 'encerrado';
    conteudo_mudou := (new.categoria_id, new.tipo, new.titulo, new.descricao, new.preco_centavos,
                       new.contato)
                      is distinct from
                      (old.categoria_id, old.tipo, old.titulo, old.descricao, old.preco_centavos,
                       old.contato);

    -- Quem procura não reserva: "Procura" nunca fica reservado, nem o reservado vira "Procura".
    if new.tipo = 'procura' and new.situacao = 'reservado' then
        raise exception 'Quem procura não reserva.'
            using errcode = 'check_violation', constraint = 'anuncio_procura_reservado';
    end if;
    if escondendo then
        -- Esconder (a gestão) não muda mais nada.
        if renovando or conteudo_mudou or new.situacao <> old.situacao
           or new.vence_em <> old.vence_em then
            raise exception 'Esconder o anúncio não muda o que ele diz.'
                using errcode = 'check_violation', constraint = 'anuncio_escondido';
        end if;
        new.escondido_em := now();
        new.editado_em := old.editado_em;
        new.encerrado_em := old.encerrado_em;
        return new;
    end if;

    if old.situacao = 'encerrado' then
        raise exception 'O anúncio encerrado não muda mais. Anuncie de novo.'
            using errcode = 'check_violation', constraint = 'anuncio_encerrado';
    end if;
    -- Daqui para baixo, é o dono: só unidade ativa.
    if exists (select 1 from public.unidade u where u.id = new.unidade_id and not u.ativa) then
        raise exception 'Só unidade ativa mexe no anúncio.'
            using errcode = 'check_violation',
                  constraint = 'classificado_de_unidade_inativa';
    end if;

    if encerrando then
        if renovando or conteudo_mudou or new.vence_em <> old.vence_em then
            raise exception 'Encerrar não muda o que o anúncio diz.'
                using errcode = 'check_violation', constraint = 'anuncio_fixo';
        end if;
        if new.motivo_encerramento is null then
            raise exception 'Encerrar pede o motivo.'
                using errcode = 'check_violation', constraint = 'anuncio_encerramento';
        end if;
        new.encerrado_em := now();
        new.editado_em := old.editado_em;
        return new;
    end if;

    if old.escondido_em is not null then
        raise exception 'A gestão escondeu este anúncio: ele só pode ser encerrado.'
            using errcode = 'check_violation', constraint = 'anuncio_escondido';
    end if;
    if new.encerrado_em is distinct from old.encerrado_em
       or new.motivo_encerramento is distinct from old.motivo_encerramento then
        raise exception 'Só encerrar põe o motivo e a data do encerramento.'
            using errcode = 'check_violation', constraint = 'anuncio_fixo';
    end if;

    if renovando then
        if conteudo_mudou or new.situacao <> old.situacao then
            raise exception 'Renovar não muda o que o anúncio diz.'
                using errcode = 'check_violation', constraint = 'anuncio_fixo';
        end if;
        if old.vence_em > now() + interval '7 days' then
            raise exception 'Só dá para renovar a menos de 7 dias de vencer.'
                using errcode = 'check_violation', constraint = 'anuncio_renovar_cedo';
        end if;
        new.renovado_em := now();
        new.vence_em := now() + interval '30 days';
        new.editado_em := old.editado_em;
        return new;
    end if;

    if new.vence_em <> old.vence_em then
        raise exception 'O vencimento muda só ao renovar.'
            using errcode = 'check_violation', constraint = 'anuncio_fixo';
    end if;
    if old.vence_em <= now() then
        raise exception 'O anúncio venceu: renove ou encerre.'
            using errcode = 'check_violation', constraint = 'anuncio_vencido';
    end if;
    if conteudo_mudou then
        new.editado_em := now();
    else
        new.editado_em := old.editado_em;
    end if;
    return new;
end;
$$;

create trigger anuncio_regras
    before insert or update on anuncio
    for each row execute function public.anuncio_conferir();

-- A foto: unidade ativa e 40 por unidade a cada 24 horas; depois de confirmada, não muda o que
-- é; entra num anúncio aberto da mesma unidade, até 4; sai dele só descartada, e descartada não
-- volta.
create function public.anuncio_foto_conferir() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
declare
    dono bigint;
begin
    if tg_op = 'DELETE' then
        -- Só sai a linha da foto descartada: quem apaga (a faxina, "apagar meus dados", o reset)
        -- descarta antes e apaga o objeto no bucket, senão ele ficaria órfão (revisão B1).
        if old.descartada_em is null then
            raise exception 'Só a foto descartada é apagada.'
                using errcode = 'check_violation', constraint = 'anuncio_foto_nao_descartada';
        end if;
        return old;
    end if;
    if tg_op = 'INSERT' then
        new.enviada_em := now();
        new.confirmada_em := null;
        new.descartada_em := null;
        new.anuncio_id := null;
        new.ordem := null;
        perform 1 from public.unidade u
         where u.id = new.unidade_id and u.ativa and not u.precisa_trocar_senha
           and u.ativada_em is not null
           for no key update;
        if not found then
            if exists (select 1 from public.unidade u where u.id = new.unidade_id) then
                raise exception 'Só unidade ativa envia foto.'
                    using errcode = 'check_violation',
                          constraint = 'classificado_de_unidade_inativa';
            end if;
            return new;  -- a chave estrangeira recusa
        end if;
        if (select count(*) from public.anuncio_foto f
             where f.unidade_id = new.unidade_id
               and f.enviada_em > now() - interval '24 hours') >= 40 then
            raise exception 'No máximo 40 fotos por apartamento a cada 24 horas.'
                using errcode = 'check_violation', constraint = 'anuncio_foto_limite_dia';
        end if;
        return new;
    end if;

    if (new.chave, new.unidade_id, new.enviada_em)
       is distinct from (old.chave, old.unidade_id, old.enviada_em) then
        raise exception 'A foto não troca de chave, de unidade nem de data.'
            using errcode = 'check_violation', constraint = 'anuncio_foto_fixa';
    end if;
    if old.descartada_em is not null then
        raise exception 'A foto descartada não volta.'
            using errcode = 'check_violation', constraint = 'anuncio_foto_descartada';
    end if;
    if old.confirmada_em is not null then
        if (new.tipo, new.bytes, new.confirmada_em) is distinct from
           (old.tipo, old.bytes, old.confirmada_em) then
            raise exception 'A foto confirmada não muda.'
                using errcode = 'check_violation', constraint = 'anuncio_foto_fixa';
        end if;
    elsif new.confirmada_em is not null then
        new.confirmada_em := now();
    end if;
    if new.descartada_em is not null then
        new.descartada_em := now();
        return new;
    end if;
    if old.anuncio_id is not null and new.anuncio_id is distinct from old.anuncio_id then
        raise exception 'A foto sai do anúncio só descartada.'
            using errcode = 'check_violation', constraint = 'anuncio_foto_fixa';
    end if;
    if old.anuncio_id is null and new.anuncio_id is not null then
        -- Trava o anúncio: duas fotos ao mesmo tempo contam uma com a outra. Encerrado, escondido
        -- ou vencido não recebe foto nova (o vencido também não é editado).
        select a.unidade_id into dono from public.anuncio a
         where a.id = new.anuncio_id and a.situacao <> 'encerrado' and a.escondido_em is null
           and a.vence_em > now()
           for no key update;
        if not found then
            if exists (select 1 from public.anuncio a where a.id = new.anuncio_id) then
                raise exception 'Anúncio encerrado, escondido ou vencido não recebe foto.'
                    using errcode = 'check_violation',
                          constraint = 'anuncio_foto_anuncio_fechado';
            end if;
            return new;  -- a chave estrangeira recusa
        end if;
        if dono <> new.unidade_id then
            raise exception 'A foto é da unidade que anuncia.'
                using errcode = 'check_violation', constraint = 'anuncio_foto_de_outra_unidade';
        end if;
        if exists (select 1 from public.unidade u where u.id = new.unidade_id and not u.ativa) then
            raise exception 'Só unidade ativa põe foto no anúncio.'
                using errcode = 'check_violation',
                      constraint = 'classificado_de_unidade_inativa';
        end if;
        if (select count(*) from public.anuncio_foto f
             where f.anuncio_id = new.anuncio_id) >= 4 then
            raise exception 'No máximo 4 fotos por anúncio.'
                using errcode = 'check_violation', constraint = 'anuncio_limite_fotos';
        end if;
    end if;
    return new;
end;
$$;

create trigger anuncio_foto_regras
    before insert or update or delete on anuncio_foto
    for each row execute function public.anuncio_foto_conferir();

-- Avisar: unidade ativa, anúncio não escondido nem encerrado e no máximo 10 por unidade a cada
-- 24 horas (o primeiro aviso de um anúncio manda e-mail à administração). Depois, só resolver.
create function public.aviso_anuncio_conferir() returns trigger
language plpgsql
set search_path = pg_catalog, public, pg_temp
as $$
begin
    if tg_op = 'INSERT' then
        new.criado_em := now();
        new.resolvido_em := null;
        new.resolvido_por := null;
        if exists (select 1 from public.anuncio a
                    where a.id = new.anuncio_id
                      and (a.escondido_em is not null or a.situacao = 'encerrado')) then
            raise exception 'Anúncio escondido ou encerrado não recebe aviso.'
                using errcode = 'check_violation', constraint = 'anuncio_escondido';
        end if;
        perform 1 from public.unidade u
         where u.id = new.unidade_id and u.ativa and not u.precisa_trocar_senha
           and u.ativada_em is not null
           for no key update;
        if not found then
            if exists (select 1 from public.unidade u where u.id = new.unidade_id) then
                raise exception 'Só unidade ativa avisa a gestão.'
                    using errcode = 'check_violation',
                          constraint = 'classificado_de_unidade_inativa';
            end if;
            return new;  -- a chave estrangeira recusa
        end if;
        if (select count(*) from public.aviso_anuncio a
             where a.unidade_id = new.unidade_id
               and a.criado_em > now() - interval '24 hours') >= 10 then
            raise exception 'No máximo 10 avisos por apartamento a cada 24 horas.'
                using errcode = 'check_violation', constraint = 'aviso_anuncio_limite_dia';
        end if;
        return new;
    end if;
    if (new.anuncio_id, new.unidade_id, new.motivo, new.criado_em)
       is distinct from (old.anuncio_id, old.unidade_id, old.motivo, old.criado_em)
       or (old.resolvido_em is not null
           and (new.resolvido_em, new.resolvido_por)
               is distinct from (old.resolvido_em, old.resolvido_por)) then
        raise exception 'O aviso não muda; só é resolvido, uma vez.'
            using errcode = 'check_violation', constraint = 'aviso_anuncio_fixo';
    end if;
    if old.resolvido_em is null and new.resolvido_em is not null then
        new.resolvido_em := now();
    end if;
    return new;
end;
$$;

create trigger aviso_anuncio_regras
    before insert or update on aviso_anuncio
    for each row execute function public.aviso_anuncio_conferir();
"""

# Padrão da 0007 a 0010: só as colunas que a API escreve. DELETE só onde o Portal apaga de
# verdade (anúncio, foto e aviso: faxina, "apagar meus dados", reset). Nada em categoria.
PERMISSOES = """
grant select, insert on categoria_classificado, anuncio, anuncio_foto, aviso_anuncio to {app};
grant update (nome) on categoria_classificado to {app};
grant update (categoria_id, tipo, titulo, descricao, preco_centavos, contato, situacao,
              motivo_encerramento, renovado_em, escondido_em, escondido_por), delete
    on anuncio to {app};
grant update (anuncio_id, tipo, bytes, ordem, confirmada_em, descartada_em), delete
    on anuncio_foto to {app};
grant update (resolvido_em, resolvido_por), delete on aviso_anuncio to {app};
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
        drop table aviso_anuncio, anuncio_foto, anuncio, categoria_classificado;
        drop function public.aviso_anuncio_conferir();
        drop function public.anuncio_foto_conferir();
        drop function public.anuncio_conferir();
        """
    )
