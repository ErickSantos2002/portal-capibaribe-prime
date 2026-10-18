"""Regras de banco das indicações (migração 0010), com SQL direto: as tentativas de burlar.

Spec: `docs/superpowers/specs/2026-10-18-indicacoes-design.md`, seções 4 e 5. Cada tentativa
roda como `app` (o que a API usa), e as que dependem das triggers também como `dono`.
"""

import pytest
from psycopg.errors import InsufficientPrivilege
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError, ProgrammingError

from app.modelos.indicacoes import CATEGORIAS_INICIAIS
from testes.apoio import restricao
from testes.apoio_indicacoes import categoria_id, criar_prestador, opinar

pytestmark = pytest.mark.usefixtures("banco_limpo")


def _recusado(engine: Engine, nome: str, comando: str, **parametros) -> None:
    with pytest.raises(DBAPIError) as erro, engine.begin() as con:
        con.execute(text(comando), parametros)
    assert restricao(erro.value) == nome, erro.value


# --- tabelas, categorias e permissões (Tarefa 1) ------------------------------------------------


def test_categorias_iniciais_na_ordem(engine_app):
    with engine_app.connect() as con:
        nomes = con.execute(text("select nome from categoria_servico order by ordem")).scalars()
        nomes = list(nomes)
    assert nomes == [n for n, _ in CATEGORIAS_INICIAIS]
    assert nomes[0] == "Móveis planejados" and nomes[-1] == "Outros"


def test_segunda_opiniao_da_mesma_unidade_e_recusada(engine_app, ids):
    with engine_app.begin() as con:
        p = criar_prestador(con, ids["u"])
    with pytest.raises(IntegrityError, match="opiniao_servico_unica"), engine_app.begin() as con:
        opinar(con, p, ids["u"])


def test_telefone_repetido_e_recusado_mesmo_escondido(engine_app, engine_dono, ids):
    with engine_app.begin() as con:
        p = criar_prestador(con, ids["u"])
    with engine_dono.begin() as con:
        con.execute(
            text("update prestador set escondido_em = now(), escondido_por = :v where id = :p"),
            {"p": p, "v": ids["v"]},
        )
    with pytest.raises(IntegrityError, match="prestador_telefone_unico"), engine_app.begin() as con:
        criar_prestador(con, ids["v"], nome="Outra marcenaria")


@pytest.mark.parametrize("telefone", ["0812345678", "8112345678x", "81812345678", "123"])
def test_telefone_fora_do_formato(engine_app, ids, telefone):
    erro = pytest.raises(IntegrityError, match="prestador_telefone_formato")
    with erro, engine_app.begin() as con:
        criar_prestador(con, ids["u"], telefone=telefone)


@pytest.mark.parametrize("instagram", ["", "com espaço", "@arroba", "a" * 31])
def test_instagram_fora_do_formato(engine_app, ids, instagram):
    erro = pytest.raises(IntegrityError, match="prestador_instagram_formato")
    with erro, engine_app.begin() as con:
        p = criar_prestador(con, ids["u"])
        con.execute(
            text("update prestador set instagram = :i where id = :p"),
            {"i": instagram, "p": p},
        )


@pytest.mark.parametrize("nome", ["X", " Marcenaria", "a" * 81])
def test_nome_fora_do_tamanho(engine_app, ids, nome):
    erro = pytest.raises(IntegrityError, match="prestador_nome_tamanho")
    with erro, engine_app.begin() as con:
        criar_prestador(con, ids["u"], nome=nome)


def test_comentario_com_501_letras_e_recusado(engine_app, ids):
    erro = pytest.raises(IntegrityError, match="opiniao_servico_comentario_tamanho")
    with erro, engine_app.begin() as con:
        criar_prestador(con, ids["u"], comentario="a" * 501)


def test_app_nao_apaga_prestador_nem_categoria(engine_app, ids):
    with engine_app.begin() as con:
        criar_prestador(con, ids["u"])
    for tabela in ("prestador", "categoria_servico"):
        with pytest.raises(ProgrammingError) as erro, engine_app.begin() as con:
            con.execute(text(f"delete from {tabela}"))
        assert isinstance(erro.value.orig, InsufficientPrivilege)


def test_segundo_aviso_aberto_da_mesma_unidade_e_recusado(engine_app, ids):
    with engine_app.begin() as con:
        p = criar_prestador(con, ids["u"])
        con.execute(
            text("insert into aviso_servico (prestador_id, unidade_id) values (:p, :u)"),
            {"p": p, "u": ids["v"]},
        )
    with pytest.raises(IntegrityError, match="aviso_servico_aberto"), engine_app.begin() as con:
        con.execute(
            text("insert into aviso_servico (prestador_id, unidade_id) values (:p, :u)"),
            {"p": p, "u": ids["v"]},
        )


def test_categorias_iguais_sem_diferenciar_maiuscula(engine_app):
    _recusado(
        engine_app,
        "categoria_servico_nome_unico",
        "insert into categoria_servico (nome, ordem) values ('eletricista', 500)",
    )


def test_apoio_acha_a_categoria(engine_app):
    with engine_app.connect() as con:
        assert categoria_id(con, "Outros") > 0


# --- regras nas triggers (Tarefa 2) --------------------------------------------------------------


def _prestadores_sem_regra(engine_superusuario, autor: int, quantos: int) -> list[int]:
    """Prestadores criados por fora das triggers (superusuário): não contam no limite de ninguém
    porque a data fica no passado."""
    with engine_superusuario.begin() as con:
        con.execute(text("set local session_replication_role = replica"))
        return list(
            con.execute(
                text(
                    "insert into prestador (categoria_id, nome, nome_busca, telefone, criado_por,"
                    " criado_em) select (select min(id) from categoria_servico), 'P' || g,"
                    " 'p' || g, '8199999' || lpad(g::text, 4, '0'), :u, now() - interval '2 days'"
                    " from generate_series(1, :n) g returning id"
                ),
                {"u": autor, "n": quantos},
            ).scalars()
        )


def _desativar(engine_dono, unidade: int) -> None:
    with engine_dono.begin() as con:
        con.execute(text("update unidade set ativa = false where id = :u"), {"u": unidade})


def test_unidade_inativa_nao_indica_nem_opina_nem_avisa(engine_app, engine_dono, ids):
    with engine_app.begin() as con:
        p = criar_prestador(con, ids["u"])
    _desativar(engine_dono, ids["v"])
    with pytest.raises(DBAPIError) as erro, engine_app.begin() as con:
        criar_prestador(con, ids["v"], telefone="81999990002")
    assert restricao(erro.value) == "indicacao_de_unidade_inativa"
    _recusado(
        engine_app,
        "indicacao_de_unidade_inativa",
        "insert into opiniao_servico (prestador_id, unidade_id, recomenda) values (:p, :v, true)",
        p=p,
        v=ids["v"],
    )
    _recusado(
        engine_app,
        "indicacao_de_unidade_inativa",
        "insert into aviso_servico (prestador_id, unidade_id) values (:p, :v)",
        p=p,
        v=ids["v"],
    )
    # E a opinião que ela já tinha não muda mais.
    _desativar(engine_dono, ids["u"])
    _recusado(
        engine_app,
        "indicacao_de_unidade_inativa",
        "update opiniao_servico set recomenda = false where unidade_id = :u",
        u=ids["u"],
    )


def test_prestador_sem_autor_e_recusado(engine_app):
    _recusado(
        engine_app,
        "indicacao_de_unidade_inativa",
        "insert into prestador (categoria_id, nome, nome_busca, telefone)"
        " values ((select min(id) from categoria_servico), 'Fulano', 'fulano', '81999990009')",
    )


def test_limite_de_10_indicacoes_por_dia(engine_app, ids):
    with engine_app.begin() as con:
        for i in range(10):
            criar_prestador(con, ids["u"], telefone=f"8199999{i:04d}")
    with pytest.raises(DBAPIError) as erro, engine_app.begin() as con:
        criar_prestador(con, ids["u"], telefone="81999998888")
    assert restricao(erro.value) == "prestador_limite_dia"
    # Outra unidade não tem nada com isso.
    with engine_app.begin() as con:
        criar_prestador(con, ids["v"], telefone="81999998888")


def test_limite_de_30_opinioes_por_dia_conta_as_apagadas(engine_app, engine_superusuario, ids):
    prestadores = _prestadores_sem_regra(engine_superusuario, ids["v"], 31)
    with engine_app.begin() as con:
        for p in prestadores[:29]:
            opinar(con, p, ids["u"])
        con.execute(
            text(
                "insert into historico (unidade_id, acao, entidade, entidade_id)"
                " values (:u, 'indicacao_opiniao_apagada', 'prestador', :p)"
            ),
            {"u": ids["u"], "p": prestadores[29]},
        )
    _recusado(
        engine_app,
        "opiniao_limite_dia",
        "insert into opiniao_servico (prestador_id, unidade_id, recomenda) values (:p, :u, true)",
        p=prestadores[30],
        u=ids["u"],
    )
    # A outra unidade continua opinando.
    with engine_app.begin() as con:
        opinar(con, prestadores[30], ids["u2"])


def test_mudar_a_opiniao_nao_conta_no_limite(engine_app, engine_superusuario, ids):
    prestadores = _prestadores_sem_regra(engine_superusuario, ids["v"], 31)
    with engine_app.begin() as con:
        for p in prestadores[:30]:
            opinar(con, p, ids["u"])
    _recusado(
        engine_app,
        "opiniao_limite_dia",
        "insert into opiniao_servico (prestador_id, unidade_id, recomenda) values (:p, :u, true)",
        p=prestadores[30],
        u=ids["u"],
    )
    with engine_app.begin() as con:
        mudou = con.execute(
            text(
                "update opiniao_servico set recomenda = false, comentario = 'Mudei'"
                " where prestador_id = :p and unidade_id = :u"
            ),
            {"p": prestadores[0], "u": ids["u"]},
        ).rowcount
    assert mudou == 1


def _esconder_opiniao(engine, prestador: int, unidade: int, gestao: int) -> None:
    with engine.begin() as con:
        con.execute(
            text(
                "update opiniao_servico set escondida_em = now(), escondida_por = :g"
                " where prestador_id = :p and unidade_id = :u"
            ),
            {"p": prestador, "u": unidade, "g": gestao},
        )


def test_opiniao_escondida_travada(engine_app, ids):
    with engine_app.begin() as con:
        p = criar_prestador(con, ids["u"], comentario="Ótimo")
    _esconder_opiniao(engine_app, p, ids["u"], ids["v"])
    filtro = {"p": p, "u": ids["u"]}
    _recusado(
        engine_app,
        "opiniao_escondida",
        "update opiniao_servico set comentario = 'Outro' where prestador_id = :p"
        " and unidade_id = :u",
        **filtro,
    )
    _recusado(
        engine_app,
        "opiniao_escondida",
        "update opiniao_servico set escondida_em = null where prestador_id = :p"
        " and unidade_id = :u",
        **filtro,
    )
    # Apagar de verdade passa ("apagar meus dados" e o reset).
    with engine_app.begin() as con:
        apagadas = con.execute(
            text("delete from opiniao_servico where prestador_id = :p and unidade_id = :u"),
            filtro,
        ).rowcount
    assert apagadas == 1


def test_esconder_a_opiniao_nao_muda_o_que_ela_diz(engine_app, ids):
    with engine_app.begin() as con:
        p = criar_prestador(con, ids["u"], comentario="Ótimo")
    _recusado(
        engine_app,
        "opiniao_escondida",
        "update opiniao_servico set escondida_em = now(), comentario = 'Ruim'"
        " where prestador_id = :p",
        p=p,
    )


def test_opiniao_nao_troca_de_prestador_nem_de_unidade(engine_app, engine_dono, ids):
    # O `app` nem tem UPDATE nessas colunas; o `dono` esbarra na trigger.
    with engine_app.begin() as con:
        p = criar_prestador(con, ids["u"])
        outro = criar_prestador(con, ids["v"], telefone="81999990002")
    _recusado(
        engine_dono,
        "opiniao_fixa",
        "update opiniao_servico set unidade_id = :v where prestador_id = :p",
        p=p,
        v=ids["u2"],
    )
    _recusado(
        engine_dono,
        "opiniao_fixa",
        "update opiniao_servico set prestador_id = :o where prestador_id = :p",
        p=p,
        o=outro,
    )


def _esconder_prestador(engine, prestador: int, gestao: int) -> None:
    with engine.begin() as con:
        con.execute(
            text("update prestador set escondido_em = now(), escondido_por = :g where id = :p"),
            {"p": prestador, "g": gestao},
        )


def test_prestador_escondido_nao_recebe_opiniao_nem_aviso_nem_correcao(engine_app, ids):
    with engine_app.begin() as con:
        p = criar_prestador(con, ids["u"])
    _esconder_prestador(engine_app, p, ids["v"])
    _recusado(
        engine_app,
        "prestador_escondido",
        "insert into opiniao_servico (prestador_id, unidade_id, recomenda) values (:p, :v, true)",
        p=p,
        v=ids["v"],
    )
    _recusado(
        engine_app,
        "prestador_escondido",
        "insert into aviso_servico (prestador_id, unidade_id) values (:p, :v)",
        p=p,
        v=ids["v"],
    )
    _recusado(engine_app, "prestador_escondido", "update prestador set nome = 'Outro'")
    _recusado(engine_app, "prestador_escondido", "update prestador set escondido_em = null")
    _recusado(
        engine_app,
        "prestador_escondido",
        "update opiniao_servico set recomenda = false where prestador_id = :p",
        p=p,
    )


def test_prestador_escondido_ainda_perde_o_autor(engine_app, ids):
    # "Apagar meus dados" põe `criado_por = null` também nos escondidos.
    with engine_app.begin() as con:
        p = criar_prestador(con, ids["u"])
    _esconder_prestador(engine_app, p, ids["v"])
    with engine_app.begin() as con:
        con.execute(text("update prestador set criado_por = null where id = :p"), {"p": p})
        assert (
            con.execute(
                text("select criado_por from prestador where id = :p"), {"p": p}
            ).scalar_one()
            is None
        )


def test_criado_por_so_vira_nulo(engine_app, ids):
    with engine_app.begin() as con:
        p = criar_prestador(con, ids["u"])
    _recusado(
        engine_app,
        "prestador_autor_fixo",
        "update prestador set criado_por = :v where id = :p",
        p=p,
        v=ids["v"],
    )
    with engine_app.begin() as con:
        con.execute(text("update prestador set criado_por = null where id = :p"), {"p": p})
    _recusado(
        engine_app,
        "prestador_autor_fixo",
        "update prestador set criado_por = :u where id = :p",
        p=p,
        u=ids["u"],
    )


def test_datas_sao_do_banco(engine_app, ids):
    with engine_app.begin() as con:
        p = con.execute(
            text(
                "insert into prestador (categoria_id, nome, nome_busca, telefone, criado_por,"
                " criado_em, editado_em, escondido_em) values ((select min(id) from"
                " categoria_servico), 'Fulano', 'fulano', '81999990001', :u, '2000-01-01',"
                " '2000-01-01', '2000-01-01') returning id"
            ),
            {"u": ids["u"]},
        ).scalar_one()
        con.execute(
            text(
                "insert into opiniao_servico (prestador_id, unidade_id, recomenda, criada_em,"
                " editada_em, escondida_em) values (:p, :u, true, '2000-01-01', '2000-01-01',"
                " '2000-01-01')"
            ),
            {"p": p, "u": ids["u"]},
        )
        con.execute(
            text(
                "insert into aviso_servico (prestador_id, unidade_id, criado_em, resolvido_em)"
                " values (:p, :v, '2000-01-01', '2000-01-01')"
            ),
            {"p": p, "v": ids["v"]},
        )
        prestador = con.execute(
            text(
                "select criado_em > now() - interval '1 minute', editado_em, escondido_em"
                " from prestador"
            )
        ).one()
        opiniao = con.execute(
            text(
                "select criada_em > now() - interval '1 minute', editada_em, escondida_em"
                " from opiniao_servico"
            )
        ).one()
        aviso = con.execute(
            text("select criado_em > now() - interval '1 minute', resolvido_em from aviso_servico")
        ).one()
    assert tuple(prestador) == (True, None, None)
    assert tuple(opiniao) == (True, None, None)
    assert tuple(aviso) == (True, None)


def test_corrigir_carimba_editado_em(engine_app, ids):
    with engine_app.begin() as con:
        p = criar_prestador(con, ids["u"])
        con.execute(text("update prestador set nome = 'Outro nome' where id = :p"), {"p": p})
        editado = con.execute(
            text("select editado_em is not null from prestador where id = :p"), {"p": p}
        ).scalar_one()
    assert editado


def test_aviso_resolvido_nao_reabre(engine_app, engine_dono, ids):
    # O `app` nem tem UPDATE em motivo e unidade; o `dono` esbarra na trigger.
    with engine_app.begin() as con:
        p = criar_prestador(con, ids["u"])
        con.execute(
            text(
                "insert into aviso_servico (prestador_id, unidade_id, motivo) values (:p, :v, 'X')"
            ),
            {"p": p, "v": ids["v"]},
        )
    _recusado(engine_dono, "aviso_servico_fixo", "update aviso_servico set motivo = 'Y'")
    _recusado(
        engine_dono, "aviso_servico_fixo", "update aviso_servico set unidade_id = :u", u=ids["u"]
    )
    with engine_app.begin() as con:
        con.execute(
            text("update aviso_servico set resolvido_em = now(), resolvido_por = :u"),
            {"u": ids["u"]},
        )
    _recusado(engine_app, "aviso_servico_fixo", "update aviso_servico set resolvido_em = null")
    # Resolvido, a mesma unidade pode avisar de novo.
    with engine_app.begin() as con:
        con.execute(
            text("insert into aviso_servico (prestador_id, unidade_id) values (:p, :v)"),
            {"p": p, "v": ids["v"]},
        )
