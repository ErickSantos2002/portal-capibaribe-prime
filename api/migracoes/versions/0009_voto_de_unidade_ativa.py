"""Voto só de unidade ativa (M4, revisão do épico B, ponto 3).

Revisão: 0009
Anterior: 0008
Criada em: 2026-10-14

Até aqui, só a sessão impedia o voto de uma unidade desativada (unidade desativada não tem
sessão); o banco, como `app`, aceitava. Agora a trigger `voto_conferir` também recusa votar ou
trocar o voto de unidade com `ativa = false`, com uma regra própria (`voto_de_unidade_inativa`),
que `enquetes_banco.traduzir` dá como 403 `unidade_inativa` (ajustes do M4, ponto 4: a primeira
versão reaproveitava `voto_fora_do_destino`, e a frase falava do bloco errado). Só a função muda:
nada de tabela, coluna ou permissão.

Escrita à mão, no mesmo padrão da 0002 a 0008. O downgrade devolve a função da 0008.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# A função como a 0008 a criou (sem a conferência de unidade ativa).
VOTO_CONFERIR_0008 = """
create or replace function public.voto_conferir() returns trigger
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
"""

_ANTES_DA_DATA = "    new.votado_em := clock_timestamp();\n"

# Unidade que não existe fica para a chave estrangeira (como na 0008); a que existe e está
# desativada é recusada aqui, ao votar e ao trocar.
_UNIDADE_ATIVA = """    if exists (select 1 from public.unidade u
                where u.id = new.unidade_id and not u.ativa) then
        raise exception 'Unidade desativada não vota.'
            using errcode = 'check_violation', constraint = 'voto_de_unidade_inativa';
    end if;
"""

VOTO_CONFERIR_0009 = VOTO_CONFERIR_0008.replace(_ANTES_DA_DATA, _UNIDADE_ATIVA + _ANTES_DA_DATA)
assert VOTO_CONFERIR_0009 != VOTO_CONFERIR_0008


def upgrade() -> None:
    op.execute(VOTO_CONFERIR_0009)


def downgrade() -> None:
    op.execute(VOTO_CONFERIR_0008)
