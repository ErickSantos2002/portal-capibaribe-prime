"""As regras dos classificados no banco (migração 0011), tentando burlar direto como `app` (padrão
do M4). Spec: `docs/superpowers/specs/2026-10-20-classificados-design.md`, seção 4."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError, ProgrammingError

from app.modelos.classificados import CATEGORIAS_INICIAIS
from testes.apoio import restricao
from testes.apoio_classificados import (
    criar_anuncio,
    criar_foto,
    envelhecer,
    prender_foto,
)


@pytest.fixture
def ids(banco_limpo, ids):
    return ids


def _recusa(engine, sql: str, params: dict | None = None) -> str | None:
    with pytest.raises(DBAPIError) as erro, engine.begin() as con:
        con.execute(text(sql), params or {})
    return restricao(erro.value)


def _um(engine, sql: str, params: dict | None = None):
    with engine.begin() as con:
        return con.execute(text(sql), params or {}).one()


def test_categorias_iniciais_na_ordem(engine_app, banco_limpo):
    with engine_app.connect() as con:
        nomes = (
            con.execute(text("select nome from categoria_classificado order by ordem"))
            .scalars()
            .all()
        )
    assert nomes == [n for n, _ in CATEGORIAS_INICIAIS]
    assert nomes[0] == "Móveis" and nomes[-1] == "Outros"


def test_app_nao_apaga_categoria(engine_app, ids):
    with pytest.raises(ProgrammingError, match="permission denied"), engine_app.begin() as con:
        con.execute(text("delete from categoria_classificado"))


def test_datas_e_situacao_sao_do_banco(engine_app, ids):
    with engine_app.begin() as con:
        a = con.execute(
            text(
                "insert into anuncio (unidade_id, categoria_id, tipo, titulo, contato, situacao,"
                " publicado_em, vence_em) values (:u, 1, 'doacao', 'Berço', '81999990001',"
                " 'reservado', '2000-01-01', '2000-02-01') returning id"
            ),
            {"u": ids["u"]},
        ).scalar_one()
    linha = _um(
        engine_app,
        "select situacao, publicado_em > now() - interval '1 minute' as agora,"
        " vence_em - publicado_em as prazo from anuncio where id = :a",
        {"a": a},
    )
    assert linha.situacao == "ativo" and linha.agora
    assert linha.prazo.days == 30


@pytest.mark.parametrize("tipo", ["doacao", "troca"])
def test_preco_so_na_venda(engine_app, ids, tipo):
    with pytest.raises(IntegrityError) as erro, engine_app.begin() as con:
        criar_anuncio(con, ids["u"], tipo=tipo, preco=100)
    assert restricao(erro.value) == "anuncio_preco"


@pytest.mark.parametrize("preco", [-1, 10_000_001])
def test_preco_fora_da_faixa(engine_app, ids, preco):
    with pytest.raises(IntegrityError) as erro, engine_app.begin() as con:
        criar_anuncio(con, ids["u"], preco=preco)
    assert restricao(erro.value) == "anuncio_preco"


def test_tipo_fora_da_lista(engine_app, ids):
    with pytest.raises(IntegrityError) as erro, engine_app.begin() as con:
        criar_anuncio(con, ids["u"], tipo="aluguel", preco=None)
    assert restricao(erro.value) == "anuncio_tipo"


def test_unidade_inativa_nao_anuncia_nem_envia_foto_nem_avisa(engine_app, engine_dono, ids):
    with engine_app.begin() as con:
        a = criar_anuncio(con, ids["v"])
    with engine_dono.begin() as con:
        con.execute(text("update unidade set ativa = false where id = :u"), {"u": ids["u"]})
    with pytest.raises(IntegrityError) as erro, engine_app.begin() as con:
        criar_anuncio(con, ids["u"])
    assert restricao(erro.value) == "classificado_de_unidade_inativa"
    with pytest.raises(IntegrityError) as erro, engine_app.begin() as con:
        criar_foto(con, ids["u"])
    assert restricao(erro.value) == "classificado_de_unidade_inativa"
    assert (
        _recusa(
            engine_app,
            "insert into aviso_anuncio (anuncio_id, unidade_id) values (:a, :u)",
            {"a": a, "u": ids["u"]},
        )
        == "classificado_de_unidade_inativa"
    )


def test_unidade_inativa_nao_mexe_no_anuncio(engine_app, engine_dono, ids):
    with engine_app.begin() as con:
        a = criar_anuncio(con, ids["u"])
    with engine_dono.begin() as con:
        con.execute(text("update unidade set ativa = false where id = :u"), {"u": ids["u"]})
    assert (
        _recusa(engine_app, "update anuncio set situacao = 'reservado' where id = :a", {"a": a})
        == "classificado_de_unidade_inativa"
    )


def test_limite_de_5_anuncios_por_dia(engine_app, ids):
    with engine_app.begin() as con:
        for n in range(5):
            criar_anuncio(con, ids["u"], titulo=f"Coisa {n}")
    with pytest.raises(IntegrityError) as erro, engine_app.begin() as con:
        criar_anuncio(con, ids["u"], titulo="A sexta")
    assert restricao(erro.value) == "anuncio_limite_dia"


def test_limite_de_10_abertos_nao_conta_vencido_nem_encerrado(engine_app, engine_superusuario, ids):
    criados = []
    with engine_app.begin() as con:
        for n in range(5):
            criados.append(criar_anuncio(con, ids["u"], titulo=f"Coisa {n}"))
    # Os 5 de "ontem": o limite do dia libera, os abertos continuam contando.
    for a in criados:
        envelhecer(engine_superusuario, "anuncio", "publicado_em", a, 2)
    with engine_app.begin() as con:
        for n in range(5, 10):
            criados.append(criar_anuncio(con, ids["u"], titulo=f"Coisa {n}"))
    for a in criados[5:]:
        envelhecer(engine_superusuario, "anuncio", "publicado_em", a, 2)
    with pytest.raises(IntegrityError) as erro, engine_app.begin() as con:
        criar_anuncio(con, ids["u"], titulo="A décima primeira")
    assert restricao(erro.value) == "anuncio_limite_abertos"
    # Um vencido e um encerrado liberam duas vagas.
    envelhecer(engine_superusuario, "anuncio", "vence_em", criados[0], 1)
    with engine_app.begin() as con:
        con.execute(
            text(
                "update anuncio set situacao = 'encerrado', motivo_encerramento = 'vendi'"
                " where id = :a"
            ),
            {"a": criados[1]},
        )
        criar_anuncio(con, ids["u"], titulo="Cabe agora")
        criar_anuncio(con, ids["u"], titulo="Cabe também")


def test_encerrar_pede_motivo_e_nao_volta(engine_app, ids):
    with engine_app.begin() as con:
        a = criar_anuncio(con, ids["u"])
    assert (
        _recusa(engine_app, "update anuncio set situacao = 'encerrado' where id = :a", {"a": a})
        == "anuncio_encerramento"
    )
    with engine_app.begin() as con:
        con.execute(
            text(
                "update anuncio set situacao = 'encerrado', motivo_encerramento = 'doei'"
                " where id = :a"
            ),
            {"a": a},
        )
    assert _um(
        engine_app, "select encerrado_em is not null as ok from anuncio where id = :a", {"a": a}
    ).ok
    for sql in (
        "update anuncio set situacao = 'ativo', motivo_encerramento = null where id = :a",
        "update anuncio set titulo = 'Outro título' where id = :a",
        "update anuncio set renovado_em = now() where id = :a",
    ):
        assert _recusa(engine_app, sql, {"a": a}) == "anuncio_encerrado"


def test_reservar_e_liberar(engine_app, ids):
    with engine_app.begin() as con:
        a = criar_anuncio(con, ids["u"])
        con.execute(text("update anuncio set situacao = 'reservado' where id = :a"), {"a": a})
        con.execute(text("update anuncio set situacao = 'ativo' where id = :a"), {"a": a})
    assert (
        _um(engine_app, "select situacao from anuncio where id = :a", {"a": a}).situacao == "ativo"
    )


def test_vencido_nao_edita_nem_reserva_mas_renova_e_encerra(engine_app, engine_superusuario, ids):
    with engine_app.begin() as con:
        a = criar_anuncio(con, ids["u"])
        b = criar_anuncio(con, ids["u"], titulo="Outro")
    for x in (a, b):
        envelhecer(engine_superusuario, "anuncio", "vence_em", x, 1)
    for sql in (
        "update anuncio set titulo = 'Novo título' where id = :a",
        "update anuncio set situacao = 'reservado' where id = :a",
    ):
        assert _recusa(engine_app, sql, {"a": a}) == "anuncio_vencido"
    with engine_app.begin() as con:
        con.execute(text("update anuncio set renovado_em = now() where id = :a"), {"a": a})
        con.execute(
            text(
                "update anuncio set situacao = 'encerrado', motivo_encerramento = 'desisti'"
                " where id = :a"
            ),
            {"a": b},
        )
    linha = _um(
        engine_app,
        "select vence_em > now() + interval '29 days' as renovado from anuncio where id = :a",
        {"a": a},
    )
    assert linha.renovado


def test_renovar_so_a_menos_de_7_dias(engine_app, engine_superusuario, ids):
    with engine_app.begin() as con:
        a = criar_anuncio(con, ids["u"])
    assert (
        _recusa(engine_app, "update anuncio set renovado_em = now() where id = :a", {"a": a})
        == "anuncio_renovar_cedo"
    )
    # A 6 dias de vencer: pode.
    with engine_superusuario.begin() as con:
        con.execute(text("alter table anuncio disable trigger user"))
        con.execute(
            text("update anuncio set vence_em = now() + interval '6 days' where id = :a"), {"a": a}
        )
        con.execute(text("alter table anuncio enable trigger user"))
    with engine_app.begin() as con:
        con.execute(text("update anuncio set renovado_em = now() where id = :a"), {"a": a})


def test_vencimento_nao_muda_a_mao(engine_dono, ids, engine_app):
    with engine_app.begin() as con:
        a = criar_anuncio(con, ids["u"])
    # Nem o `app` tem a coluna (grant), nem o dono passa pela trigger.
    with pytest.raises(ProgrammingError, match="permission denied"), engine_app.begin() as con:
        con.execute(
            text("update anuncio set vence_em = now() + interval '1 year' where id = :a"), {"a": a}
        )
    assert (
        _recusa(
            engine_dono,
            "update anuncio set vence_em = now() + interval '1 year' where id = :a",
            {"a": a},
        )
        == "anuncio_fixo"
    )


def test_escondido_so_encerra_e_nao_volta(engine_app, ids):
    with engine_app.begin() as con:
        a = criar_anuncio(con, ids["u"])
        con.execute(
            text("update anuncio set escondido_em = now(), escondido_por = :g where id = :a"),
            {"a": a, "g": ids["v"]},
        )
    for sql in (
        "update anuncio set titulo = 'Outro título' where id = :a",
        "update anuncio set situacao = 'reservado' where id = :a",
        "update anuncio set escondido_em = null, escondido_por = null where id = :a",
    ):
        assert _recusa(engine_app, sql, {"a": a}) == "anuncio_escondido"
    with engine_app.begin() as con:
        con.execute(
            text(
                "update anuncio set situacao = 'encerrado', motivo_encerramento = 'desisti'"
                " where id = :a"
            ),
            {"a": a},
        )


def test_esconder_nao_muda_o_conteudo(engine_app, ids):
    with engine_app.begin() as con:
        a = criar_anuncio(con, ids["u"])
    assert (
        _recusa(
            engine_app,
            "update anuncio set escondido_em = now(), titulo = 'Trocado' where id = :a",
            {"a": a},
        )
        == "anuncio_escondido"
    )


def test_unidade_e_data_do_anuncio_nao_mudam(engine_dono, engine_app, ids):
    with engine_app.begin() as con:
        a = criar_anuncio(con, ids["u"])
    assert (
        _recusa(
            engine_dono, "update anuncio set unidade_id = :v where id = :a", {"a": a, "v": ids["v"]}
        )
        == "anuncio_fixo"
    )


# --- fotos -----------------------------------------------------------------------------------


def test_ate_4_fotos_por_anuncio(engine_app, ids):
    with engine_app.begin() as con:
        a = criar_anuncio(con, ids["u"])
        for ordem in range(4):
            prender_foto(con, criar_foto(con, ids["u"]), a, ordem)
        quinta = criar_foto(con, ids["u"])
    assert (
        _recusa(
            engine_app,
            "update anuncio_foto set anuncio_id = :a, ordem = 3 where id = :f",
            {"a": a, "f": quinta},
        )
        == "anuncio_limite_fotos"
    )


def test_foto_de_outra_unidade_nao_entra(engine_app, ids):
    with engine_app.begin() as con:
        a = criar_anuncio(con, ids["u"])
        alheia = criar_foto(con, ids["v"])
    assert (
        _recusa(
            engine_app,
            "update anuncio_foto set anuncio_id = :a, ordem = 0 where id = :f",
            {"a": a, "f": alheia},
        )
        == "anuncio_foto_de_outra_unidade"
    )


def test_foto_pendente_nao_entra_no_anuncio(engine_app, ids):
    with engine_app.begin() as con:
        a = criar_anuncio(con, ids["u"])
        pendente = criar_foto(con, ids["u"], confirmada=False)
    assert (
        _recusa(
            engine_app,
            "update anuncio_foto set anuncio_id = :a, ordem = 0 where id = :f",
            {"a": a, "f": pendente},
        )
        == "anuncio_foto_estado"
    )


def test_foto_sai_do_anuncio_so_descartada_e_nao_volta(engine_app, ids):
    with engine_app.begin() as con:
        a = criar_anuncio(con, ids["u"])
        b = criar_anuncio(con, ids["u"], titulo="Outro")
        f = criar_foto(con, ids["u"])
        prender_foto(con, f, a, 0)
    assert (
        _recusa(
            engine_app, "update anuncio_foto set anuncio_id = :b where id = :f", {"b": b, "f": f}
        )
        == "anuncio_foto_fixa"
    )
    with engine_app.begin() as con:
        con.execute(
            text(
                "update anuncio_foto set anuncio_id = null, ordem = null, descartada_em = now()"
                " where id = :f"
            ),
            {"f": f},
        )
    assert (
        _recusa(
            engine_app,
            "update anuncio_foto set anuncio_id = :a, ordem = 0, descartada_em = null"
            " where id = :f",
            {"a": a, "f": f},
        )
        == "anuncio_foto_descartada"
    )


def test_confirmada_nao_muda_o_que_e(engine_app, ids):
    with engine_app.begin() as con:
        f = criar_foto(con, ids["u"])
    assert (
        _recusa(engine_app, "update anuncio_foto set bytes = 5 where id = :f", {"f": f})
        == "anuncio_foto_fixa"
    )


def test_encerrado_nao_recebe_foto(engine_app, ids):
    with engine_app.begin() as con:
        a = criar_anuncio(con, ids["u"])
        con.execute(
            text(
                "update anuncio set situacao = 'encerrado', motivo_encerramento = 'vendi'"
                " where id = :a"
            ),
            {"a": a},
        )
        f = criar_foto(con, ids["u"])
    assert (
        _recusa(
            engine_app,
            "update anuncio_foto set anuncio_id = :a, ordem = 0 where id = :f",
            {"a": a, "f": f},
        )
        == "anuncio_foto_anuncio_fechado"
    )


def test_limite_de_40_fotos_por_dia_conta_as_descartadas(engine_app, ids):
    with engine_app.begin() as con:
        for _ in range(39):
            criar_foto(con, ids["u"])
        f = criar_foto(con, ids["u"])
        con.execute(text("update anuncio_foto set descartada_em = now() where id = :f"), {"f": f})
    with pytest.raises(IntegrityError) as erro, engine_app.begin() as con:
        criar_foto(con, ids["u"])
    assert restricao(erro.value) == "anuncio_foto_limite_dia"


def test_anuncio_com_foto_presa_nao_e_apagado(engine_app, ids):
    with engine_app.begin() as con:
        a = criar_anuncio(con, ids["u"])
        prender_foto(con, criar_foto(con, ids["u"]), a, 0)
    assert (
        _recusa(engine_app, "delete from anuncio where id = :a", {"a": a})
        == "anuncio_foto_anuncio_id_fkey"
    )


def test_apagar_anuncio_leva_os_avisos(engine_app, ids):
    with engine_app.begin() as con:
        a = criar_anuncio(con, ids["u"])
        con.execute(
            text("insert into aviso_anuncio (anuncio_id, unidade_id) values (:a, :v)"),
            {"a": a, "v": ids["v"]},
        )
        con.execute(text("delete from anuncio where id = :a"), {"a": a})
        assert con.execute(text("select count(*) from aviso_anuncio")).scalar_one() == 0


# --- avisos ----------------------------------------------------------------------------------


def test_um_aviso_aberto_por_unidade(engine_app, ids):
    with engine_app.begin() as con:
        a = criar_anuncio(con, ids["u"])
        con.execute(
            text("insert into aviso_anuncio (anuncio_id, unidade_id) values (:a, :v)"),
            {"a": a, "v": ids["v"]},
        )
    assert (
        _recusa(
            engine_app,
            "insert into aviso_anuncio (anuncio_id, unidade_id) values (:a, :v)",
            {"a": a, "v": ids["v"]},
        )
        == "aviso_anuncio_aberto"
    )


def test_limite_de_10_avisos_por_dia(engine_app, ids):
    with engine_app.begin() as con:
        anuncios = []
        for n in range(5):
            anuncios.append(criar_anuncio(con, ids["u"], titulo=f"Coisa {n}"))
        for n in range(5):
            anuncios.append(criar_anuncio(con, ids["u2"], titulo=f"Coisa {n}"))
        for a in anuncios:
            con.execute(
                text("insert into aviso_anuncio (anuncio_id, unidade_id) values (:a, :v)"),
                {"a": a, "v": ids["v"]},
            )
        b = criar_anuncio(con, ids["v"], titulo="Do próprio")
    assert (
        _recusa(
            engine_app,
            "insert into aviso_anuncio (anuncio_id, unidade_id) values (:a, :v)",
            {"a": b, "v": ids["v"]},
        )
        == "aviso_anuncio_limite_dia"
    )


def test_escondido_nao_recebe_aviso_e_aviso_resolvido_nao_reabre(engine_app, ids):
    with engine_app.begin() as con:
        a = criar_anuncio(con, ids["u"])
        aviso = con.execute(
            text("insert into aviso_anuncio (anuncio_id, unidade_id) values (:a, :v) returning id"),
            {"a": a, "v": ids["v"]},
        ).scalar_one()
        con.execute(
            text("update aviso_anuncio set resolvido_em = now(), resolvido_por = :g where id = :i"),
            {"i": aviso, "g": ids["u2"]},
        )
        con.execute(text("update anuncio set escondido_em = now() where id = :a"), {"a": a})
    assert (
        _recusa(
            engine_app,
            "update aviso_anuncio set resolvido_em = null where id = :i",
            {"i": aviso},
        )
        == "aviso_anuncio_fixo"
    )
    assert (
        _recusa(
            engine_app,
            "insert into aviso_anuncio (anuncio_id, unidade_id) values (:a, :v)",
            {"a": a, "v": ids["u2"]},
        )
        == "anuncio_escondido"
    )
