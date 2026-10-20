"""As migrações aplicam do zero, voltam e aplicam de novo (critério do M0)."""

import re

import psycopg
import pytest

from testes.apoio import rodar_alembic
from testes.conftest import BANCO, apagar_banco, garantir_papeis, recriar_banco, url_para

BANCO_VAZIO = f"{BANCO}_migracoes"


@pytest.fixture
def banco_vazio():
    garantir_papeis()
    recriar_banco(BANCO_VAZIO)
    yield url_para("dono", BANCO_VAZIO)
    apagar_banco(BANCO_VAZIO)


def _tabelas(url: str) -> set[str]:
    with psycopg.connect(url) as con:
        linhas = con.execute(
            "select tablename from pg_tables where schemaname = 'public'"
        ).fetchall()
    return {t for (t,) in linhas}


def test_upgrade_downgrade_upgrade(banco_vazio):
    esperadas = {
        "bloco",
        "unidade",
        "unidade_papel",
        "sessao",
        "historico",
        "erro",
        "aviso",
        "aviso_versao",
        "aviso_bloco",
        "aviso_leitura",
        "inscricao_push",
        "token_recuperacao",
        "notificacao_envio",
        "arquivo",
        "documento",
        "documento_versao",
        "aviso_anexo",
        "enquete",
        "enquete_opcao",
        "enquete_bloco",
        "voto",
        "voto_opcao",
        "categoria_servico",
        "prestador",
        "opiniao_servico",
        "aviso_servico",
    }

    rodar_alembic(banco_vazio, "upgrade", "head")
    assert esperadas <= _tabelas(banco_vazio)

    rodar_alembic(banco_vazio, "downgrade", "base")
    assert _tabelas(banco_vazio) == {"alembic_version"}

    rodar_alembic(banco_vazio, "upgrade", "head")
    assert esperadas <= _tabelas(banco_vazio)


def test_migracao_falha_com_mensagem_clara_sem_papel_app(banco_vazio):
    with pytest.raises(RuntimeError, match=r"papel .*papel_que_nao_existe.* não existe"):
        rodar_alembic(banco_vazio, "upgrade", "head", x=["papel_app=papel_que_nao_existe"])
    # Nada ficou pela metade: a migração roda numa transação só.
    assert _tabelas(banco_vazio) <= {"alembic_version"}


def test_downgrade_da_0002_volta_ao_m0(banco_vazio):
    rodar_alembic(banco_vazio, "upgrade", "head")
    rodar_alembic(banco_vazio, "downgrade", "0001")
    assert _tabelas(banco_vazio) == {
        "alembic_version",
        "bloco",
        "unidade",
        "unidade_papel",
        "sessao",
        "historico",
        "erro",
    }
    rodar_alembic(banco_vazio, "upgrade", "head")
    assert "aviso" in _tabelas(banco_vazio)


def test_0002_retira_o_admin_que_a_carga_do_m0_deu_a_unidade_nao_ativada(banco_vazio):
    # Produção depois do M0: o admin estava numa unidade ainda com mudar123. A 0002 retira esse
    # papel (registrando no histórico); o admin volta por `promover_admin`.
    rodar_alembic(banco_vazio, "upgrade", "0001")
    with psycopg.connect(banco_vazio, autocommit=True) as con:
        con.execute("insert into bloco (numero, nome) values (1, 'Bloco 1')")
        con.execute(
            "insert into unidade (bloco_id, numero, andar, senha_hash)"
            " select id, '101', 1, 'h' from bloco"
        )
        con.execute("insert into unidade_papel (unidade_id, papel) select id, 'admin' from unidade")
    rodar_alembic(banco_vazio, "upgrade", "head")
    with psycopg.connect(banco_vazio) as con:
        em_vigor = con.execute(
            "select count(*) from unidade_papel where retirado_em is null"
        ).fetchone()
        registro = con.execute(
            "select acao, detalhes from historico where acao = 'papel_retirado'"
        ).fetchone()
    assert em_vigor == (0,)
    assert registro == ("papel_retirado", {"papel": "admin", "origem": "migracao_0002"})


def test_0003_preenche_a_versao_lida_pelas_datas(banco_vazio):
    # Quem leu antes da correção leu a versão 1; quem leu depois, a 2 (revisão do M1, U1).
    rodar_alembic(banco_vazio, "upgrade", "0002")
    with psycopg.connect(banco_vazio, autocommit=True) as con:
        con.execute("insert into bloco (numero, nome) values (1, 'Bloco 1')")
        con.execute(
            "insert into unidade (bloco_id, numero, andar, senha_hash)"
            " select id, n, 1, 'h' from bloco, (values ('101'), ('102')) as v(n)"
        )
        with con.transaction():
            con.execute(
                "insert into aviso (publicado_por, publicado_como, para_todos)"
                " select min(id), 'comissao', true from unidade"
            )
            con.execute(
                "insert into aviso_versao (aviso_id, versao, titulo, texto, criada_por)"
                " select a.id, 1, 'T', 'X', a.publicado_por from aviso a"
            )
        con.execute(
            "insert into aviso_leitura (aviso_id, unidade_id)"
            " select a.id, u.id from aviso a, unidade u where u.numero = '101'"
        )
        con.execute(
            "insert into aviso_versao (aviso_id, versao, titulo, texto, criada_por)"
            " select a.id, 2, 'T2', 'X2', a.publicado_por from aviso a"
        )
        con.execute(
            "insert into aviso_leitura (aviso_id, unidade_id)"
            " select a.id, u.id from aviso a, unidade u where u.numero = '102'"
        )
    rodar_alembic(banco_vazio, "upgrade", "head")
    with psycopg.connect(banco_vazio) as con:
        lidas = con.execute(
            "select u.numero, l.versao_lida from aviso_leitura l"
            " join unidade u on u.id = l.unidade_id order by u.numero"
        ).fetchall()
    assert lidas == [("101", 1), ("102", 2)]


def _colunas(url: str, tabela: str) -> set[str]:
    with psycopg.connect(url) as con:
        linhas = con.execute(
            "select column_name from information_schema.columns where table_name = %s", [tabela]
        ).fetchall()
    return {c for (c,) in linhas}


NOVAS_DA_0004 = {"categoria", "evento_quando", "evento_onde"}


def test_0004_avisos_existentes_viram_geral_sem_evento(banco_vazio):
    # Avisos publicados antes da 0004 (produção do M1): categoria "geral" e nenhum evento.
    rodar_alembic(banco_vazio, "upgrade", "0003")
    with psycopg.connect(banco_vazio, autocommit=True) as con:
        con.execute("insert into bloco (numero, nome) values (1, 'Bloco 1')")
        con.execute(
            "insert into unidade (bloco_id, numero, andar, senha_hash)"
            " select id, '101', 1, 'h' from bloco"
        )
        with con.transaction():
            con.execute(
                "insert into aviso (publicado_por, publicado_como, para_todos)"
                " select id, 'comissao', true from unidade"
            )
            con.execute(
                "insert into aviso_versao (aviso_id, versao, titulo, texto, criada_por)"
                " select a.id, 1, 'Bem-vindos', 'Olá', a.publicado_por from aviso a"
            )
        con.execute(
            "insert into aviso_versao (aviso_id, versao, titulo, texto, criada_por)"
            " select a.id, 2, 'Bem-vindos', 'Olá, vizinhos', a.publicado_por from aviso a"
        )
    rodar_alembic(banco_vazio, "upgrade", "head")
    with psycopg.connect(banco_vazio) as con:
        versoes = con.execute(
            "select versao, categoria, evento_quando, evento_onde from aviso_versao order by versao"
        ).fetchall()
    assert versoes == [(1, "geral", None, None), (2, "geral", None, None)]


def test_downgrade_da_0004_volta_a_0003(banco_vazio):
    rodar_alembic(banco_vazio, "upgrade", "head")
    rodar_alembic(banco_vazio, "downgrade", "0003")
    assert not NOVAS_DA_0004 & _colunas(banco_vazio, "aviso_versao")
    rodar_alembic(banco_vazio, "upgrade", "head")
    assert _colunas(banco_vazio, "aviso_versao") >= NOVAS_DA_0004


def test_downgrade_da_0003_volta_a_0002(banco_vazio):
    rodar_alembic(banco_vazio, "upgrade", "head")
    rodar_alembic(banco_vazio, "downgrade", "0002")
    assert "entrada_tentativa" not in _tabelas(banco_vazio)
    with psycopg.connect(banco_vazio) as con:
        colunas = {
            c
            for (c,) in con.execute(
                "select column_name from information_schema.columns where table_name = 'unidade'"
            ).fetchall()
        }
    assert {"tentativas_falhas", "bloqueada_ate"} <= colunas
    rodar_alembic(banco_vazio, "upgrade", "head")
    assert "entrada_tentativa" in _tabelas(banco_vazio)


NOVAS_DA_0005 = {"inscricao_push", "token_recuperacao", "notificacao_envio"}
FUNCOES_DA_0005 = {
    "inscricao_push_conferir",
    "sessao_encerrada_sem_push",
    "token_recuperacao_conferir",
    "notificacao_envio_conferir",
}


def _funcoes(url: str) -> dict[str, list[str] | None]:
    """Funções do schema public e a configuração de cada uma (`proconfig`)."""
    with psycopg.connect(url) as con:
        linhas = con.execute(
            "select p.proname, p.proconfig from pg_proc p"
            " join pg_namespace n on n.oid = p.pronamespace where n.nspname = 'public'"
        ).fetchall()
    return dict(linhas)


def test_downgrade_da_0005_volta_a_0004(banco_vazio):
    rodar_alembic(banco_vazio, "upgrade", "0004")
    funcoes_da_0004 = _funcoes(banco_vazio)
    rodar_alembic(banco_vazio, "upgrade", "head")
    assert _tabelas(banco_vazio) >= NOVAS_DA_0005
    rodar_alembic(banco_vazio, "downgrade", "0004")
    assert not NOVAS_DA_0005 & _tabelas(banco_vazio)
    # Nada da 0005 fica para trás (funções de trigger incluídas).
    assert _funcoes(banco_vazio) == funcoes_da_0004
    rodar_alembic(banco_vazio, "upgrade", "head")
    assert _tabelas(banco_vazio) >= NOVAS_DA_0005


def test_funcoes_de_trigger_da_0005_com_search_path_fixo(banco_vazio):
    rodar_alembic(banco_vazio, "upgrade", "head")
    funcoes = _funcoes(banco_vazio)
    assert set(funcoes) >= FUNCOES_DA_0005
    for nome in FUNCOES_DA_0005:
        assert funcoes[nome] == ["search_path=pg_catalog, public, pg_temp"], nome


def test_0006_unidades_existentes_continuam_recebendo_por_email(banco_vazio):
    # Produção da 1.2.0: quem já cadastrou e-mail continua recebendo depois da 0006.
    rodar_alembic(banco_vazio, "upgrade", "0005")
    with psycopg.connect(banco_vazio, autocommit=True) as con:
        con.execute("insert into bloco (numero, nome) values (1, 'Bloco 1')")
        con.execute(
            "insert into unidade (bloco_id, numero, andar, senha_hash)"
            " select id, n, 1, 'h' from bloco, (values ('101'), ('102')) as v(n)"
        )
    rodar_alembic(banco_vazio, "upgrade", "head")
    with psycopg.connect(banco_vazio) as con:
        valores = con.execute("select receber_avisos_email from unidade").fetchall()
        coluna = con.execute(
            "select is_nullable, column_default from information_schema.columns"
            " where table_name = 'unidade' and column_name = 'receber_avisos_email'"
        ).fetchone()
    assert valores == [(True,), (True,)]
    assert coluna == ("NO", "true")


def test_downgrade_da_0006_volta_a_0005(banco_vazio):
    rodar_alembic(banco_vazio, "upgrade", "head")
    rodar_alembic(banco_vazio, "downgrade", "0005")
    assert "receber_avisos_email" not in _colunas(banco_vazio, "unidade")
    rodar_alembic(banco_vazio, "upgrade", "head")
    assert "receber_avisos_email" in _colunas(banco_vazio, "unidade")


NOVAS_DA_0007 = {"arquivo", "documento", "documento_versao", "aviso_anexo"}
FUNCOES_DA_0007 = {
    "arquivo_conferir",
    "arquivo_conferir_uso",
    "documento_carimbar",
    "documento_conferir_completo",
    "documento_versao_conferir",
    "aviso_anexo_conferir",
}


def test_downgrade_da_0007_volta_a_0006(banco_vazio):
    rodar_alembic(banco_vazio, "upgrade", "0006")
    funcoes_da_0006 = _funcoes(banco_vazio)
    rodar_alembic(banco_vazio, "upgrade", "head")
    assert _tabelas(banco_vazio) >= NOVAS_DA_0007
    rodar_alembic(banco_vazio, "downgrade", "0006")
    assert not NOVAS_DA_0007 & _tabelas(banco_vazio)
    # Nada da 0007 fica para trás (funções de trigger incluídas).
    assert _funcoes(banco_vazio) == funcoes_da_0006
    rodar_alembic(banco_vazio, "upgrade", "head")
    assert _tabelas(banco_vazio) >= NOVAS_DA_0007


def test_funcoes_de_trigger_da_0007_com_search_path_fixo(banco_vazio):
    rodar_alembic(banco_vazio, "upgrade", "head")
    funcoes = _funcoes(banco_vazio)
    assert set(funcoes) >= FUNCOES_DA_0007
    for nome in FUNCOES_DA_0007:
        assert funcoes[nome] == ["search_path=pg_catalog, public, pg_temp"], nome


NOVAS_DA_0008 = {"enquete", "enquete_opcao", "enquete_bloco", "voto", "voto_opcao"}
FUNCOES_DA_0008 = {
    "enquete_conferir",
    "enquete_conferir_completa",
    "enquete_opcao_conferir",
    "enquete_opcao_conferir_completa",
    "enquete_bloco_conferir",
    "voto_conferir",
    "voto_conferir_completo",
    "voto_opcao_conferir",
    "voto_marca_a_enquete",
    "aviso_bloco_da_enquete",
}


def _app_muda_numero_da_unidade(url: str) -> bool:
    with psycopg.connect(url) as con:
        return con.execute(
            "select has_column_privilege('app', 'public.unidade', 'numero', 'UPDATE')"
        ).fetchone()[0]


def test_downgrade_da_0008_volta_a_0007(banco_vazio):
    rodar_alembic(banco_vazio, "upgrade", "0007")
    funcoes_da_0007 = _funcoes(banco_vazio)
    rodar_alembic(banco_vazio, "upgrade", "head")
    assert _tabelas(banco_vazio) >= NOVAS_DA_0008
    assert not _app_muda_numero_da_unidade(banco_vazio)
    rodar_alembic(banco_vazio, "downgrade", "0007")
    assert not NOVAS_DA_0008 & _tabelas(banco_vazio)
    # Nada da 0008 fica para trás (funções de trigger incluídas), e o UPDATE em `unidade` volta
    # a ser o da 0001 (a tabela inteira).
    assert _funcoes(banco_vazio) == funcoes_da_0007
    assert _app_muda_numero_da_unidade(banco_vazio)
    rodar_alembic(banco_vazio, "upgrade", "head")
    assert _tabelas(banco_vazio) >= NOVAS_DA_0008


def test_funcoes_de_trigger_da_0008_com_search_path_fixo(banco_vazio):
    rodar_alembic(banco_vazio, "upgrade", "head")
    funcoes = _funcoes(banco_vazio)
    assert set(funcoes) >= FUNCOES_DA_0008
    for nome in FUNCOES_DA_0008:
        assert funcoes[nome] == ["search_path=pg_catalog, public, pg_temp"], nome


NOVAS_DA_0010 = {"categoria_servico", "prestador", "opiniao_servico", "aviso_servico"}


def test_downgrade_da_0010_volta_a_0009(banco_vazio):
    rodar_alembic(banco_vazio, "upgrade", "0009")
    funcoes_da_0009 = _funcoes(banco_vazio)
    tabelas_da_0009 = _tabelas(banco_vazio)
    rodar_alembic(banco_vazio, "upgrade", "head")
    assert _tabelas(banco_vazio) >= NOVAS_DA_0010
    rodar_alembic(banco_vazio, "downgrade", "0009")
    # As quatro somem, as da 0009 ficam, e nada da 0010 fica para trás (funções incluídas).
    assert _tabelas(banco_vazio) == tabelas_da_0009
    assert _funcoes(banco_vazio) == funcoes_da_0009
    rodar_alembic(banco_vazio, "upgrade", "head")
    assert _tabelas(banco_vazio) >= NOVAS_DA_0010


def test_carga_da_migracao_igual_a_constante():
    # A migração fica congelada; a constante é a que a aplicação (e o `banco_limpo`) usa.
    from app.modelos.indicacoes import CATEGORIAS_INICIAIS
    from testes.apoio import RAIZ_API

    texto = (RAIZ_API / "migracoes" / "versions" / "0010_indicacoes.py").read_text()
    carga = re.findall(r"\('([^']+)', (\d+)\)", texto.split("CARGA", 1)[1])
    assert [(n, int(o)) for n, o in carga] == list(CATEGORIAS_INICIAIS)


FUNCOES_DA_0010 = {"prestador_conferir", "opiniao_conferir", "aviso_servico_conferir"}


def test_funcoes_de_trigger_da_0010_com_search_path_fixo(banco_vazio):
    rodar_alembic(banco_vazio, "upgrade", "head")
    funcoes = _funcoes(banco_vazio)
    assert set(funcoes) >= FUNCOES_DA_0010
    for nome in FUNCOES_DA_0010:
        assert funcoes[nome] == ["search_path=pg_catalog, public, pg_temp"], nome


NOVAS_DA_0011 = {"categoria_classificado", "anuncio", "anuncio_foto", "aviso_anuncio"}
FUNCOES_DA_0011 = {"anuncio_conferir", "anuncio_foto_conferir", "aviso_anuncio_conferir"}


def test_downgrade_da_0011_volta_a_0010(banco_vazio):
    rodar_alembic(banco_vazio, "upgrade", "0010")
    funcoes_da_0010 = _funcoes(banco_vazio)
    tabelas_da_0010 = _tabelas(banco_vazio)
    rodar_alembic(banco_vazio, "upgrade", "head")
    assert _tabelas(banco_vazio) >= NOVAS_DA_0011
    rodar_alembic(banco_vazio, "downgrade", "0010")
    assert _tabelas(banco_vazio) == tabelas_da_0010
    assert _funcoes(banco_vazio) == funcoes_da_0010
    rodar_alembic(banco_vazio, "upgrade", "head")
    assert _tabelas(banco_vazio) >= NOVAS_DA_0011


def test_carga_da_0011_igual_a_constante():
    from app.modelos.classificados import CATEGORIAS_INICIAIS
    from testes.apoio import RAIZ_API

    texto = (RAIZ_API / "migracoes" / "versions" / "0011_classificados.py").read_text()
    carga = re.findall(r"\('([^']+)', (\d+)\)", texto.split("CARGA", 1)[1])
    assert [(n, int(o)) for n, o in carga] == list(CATEGORIAS_INICIAIS)


def test_funcoes_de_trigger_da_0011_com_search_path_fixo(banco_vazio):
    rodar_alembic(banco_vazio, "upgrade", "head")
    funcoes = _funcoes(banco_vazio)
    assert set(funcoes) >= FUNCOES_DA_0011
    for nome in FUNCOES_DA_0011:
        assert funcoes[nome] == ["search_path=pg_catalog, public, pg_temp"], nome
