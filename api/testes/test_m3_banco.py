"""Regras de banco do M3 (migração 0007), como o usuário `app`.

- `arquivo`: chave aleatória única, nome que é só rótulo, só PDF e imagens, 10 MB no aviso e
  20 MB no documento, pendente pode ser corrigido e apagado, confirmado nunca muda nem é
  apagado, até 50 por unidade por dia (RNF-22, ADR-0011).
- `documento` e `documento_versao`: completo no commit, versões em sequência, arquivo
  confirmado e de documento, arquivado não volta nem ganha versão, nada apagado (H-17, H-19,
  RN-05).
- `aviso_anexo`: arquivo confirmado e de aviso, até 5 por versão, só na transação que cria a
  versão, nunca em dois avisos (H-12).
"""

import pytest
from psycopg.errors import InsufficientPrivilege
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError

from testes.apoio import criar_bloco, criar_unidade, restricao

pytestmark = pytest.mark.usefixtures("banco_limpo")

MB = 1024 * 1024
_contador = iter(range(1, 10_000))


def _chave() -> str:
    return f"{next(_contador):032x}"


@pytest.fixture
def ids(engine_app) -> dict[str, int]:
    """Uma unidade ativada (`u`) e um aviso para todos (`a`), com a versão 1."""
    with engine_app.begin() as con:
        b = criar_bloco(con, 1)
        u = criar_unidade(
            con,
            b,
            "101",
            precisa_trocar_senha=False,
            ativada_em="2026-10-01",
            responsavel_nome="Fictício",
            celular="81900000001",
        )
        a = _aviso(con, u)
    return {"u": u, "a": a}


def _aviso(con, unidade: int) -> int:
    a = con.execute(
        text(
            "insert into aviso (publicado_por, publicado_como, para_todos)"
            " values (:u, 'comissao', true) returning id"
        ),
        {"u": unidade},
    ).scalar_one()
    con.execute(
        text(
            "insert into aviso_versao (aviso_id, versao, titulo, texto, criada_por)"
            " values (:a, 1, 'Título', 'Texto', :u)"
        ),
        {"a": a, "u": unidade},
    )
    return a


def _arquivo(
    con,
    unidade: int,
    *,
    finalidade: str = "documento",
    tipo: str = "application/pdf",
    tamanho: int = 1000,
    nome: str = "Regras da obra.pdf",
    confirmar: bool = True,
    chave: str | None = None,
) -> int:
    arquivo = con.execute(
        text(
            "insert into arquivo (chave, nome_original, tipo, finalidade, tamanho_bytes,"
            " enviado_por) values (:c, :n, :t, :f, :tam, :u) returning id"
        ),
        {
            "c": chave or _chave(),
            "n": nome,
            "t": tipo,
            "f": finalidade,
            "tam": tamanho,
            "u": unidade,
        },
    ).scalar_one()
    if confirmar:
        con.execute(text("update arquivo set confirmado_em = now() where id = :a"), {"a": arquivo})
    return arquivo


def _documento(con, unidade: int, arquivo: int, *, acesso: str = "compradores", **extra) -> int:
    colunas = {
        "titulo": "Convenção do condomínio",
        "categoria": "convencao",
        "data_documento": "2026-10-01",
        "acesso": acesso,
        "criado_por": unidade,
        **extra,
    }
    documento = con.execute(
        text(
            f"insert into documento ({', '.join(colunas)})"
            f" values ({', '.join(':' + c for c in colunas)}) returning id"
        ),
        colunas,
    ).scalar_one()
    _versao(con, documento, 1, arquivo, unidade)
    return documento


def _versao(con, documento: int, versao: int, arquivo: int, unidade: int) -> None:
    con.execute(
        text(
            "insert into documento_versao (documento_id, versao, arquivo_id, enviada_por)"
            " values (:d, :v, :a, :u)"
        ),
        {"d": documento, "v": versao, "a": arquivo, "u": unidade},
    )


def _anexo(con, aviso: int, versao: int, arquivo: int, ordem: int = 1) -> None:
    con.execute(
        text(
            "insert into aviso_anexo (aviso_id, versao, arquivo_id, ordem)"
            " values (:a, :v, :arq, :o)"
        ),
        {"a": aviso, "v": versao, "arq": arquivo, "o": ordem},
    )


def _recusado(engine, funcao) -> str | None:
    with pytest.raises(DBAPIError) as erro, engine.begin() as con:
        funcao(con)
    return restricao(erro.value)


def _negado(engine, comando: str, **parametros) -> None:
    with pytest.raises(ProgrammingError) as erro, engine.begin() as con:
        con.execute(text(comando), parametros)
    assert isinstance(erro.value.orig, InsufficientPrivilege)


# --- arquivo -----------------------------------------------------------------------------------


def test_arquivo_nasce_pendente_com_a_data_do_banco(engine_app, ids):
    with engine_app.begin() as con:
        arquivo = con.execute(
            text(
                "insert into arquivo (chave, nome_original, tipo, finalidade, tamanho_bytes,"
                " enviado_por, enviado_em, confirmado_em) values (:c, 'a.pdf',"
                " 'application/pdf', 'documento', 10, :u, '2000-01-01', '2000-01-01')"
                " returning id"
            ),
            {"c": _chave(), "u": ids["u"]},
        ).scalar_one()
        enviado, confirmado, agora = con.execute(
            text("select enviado_em, confirmado_em, now() from arquivo where id = :a"),
            {"a": arquivo},
        ).one()
    assert enviado == agora
    assert confirmado is None


@pytest.mark.parametrize("chave", ["ABC", "0" * 31, "0" * 33, "g" * 32, "../" + "0" * 29])
def test_chave_so_hexadecimal_de_32(engine_app, ids, chave):
    assert _recusado(engine_app, lambda con: _arquivo(con, ids["u"], chave=chave)) == (
        "arquivo_chave"
    )


def test_chave_unica(engine_app, ids):
    chave = _chave()
    with engine_app.begin() as con:
        _arquivo(con, ids["u"], chave=chave)
    assert _recusado(engine_app, lambda con: _arquivo(con, ids["u"], chave=chave)) == (
        "arquivo_chave_key"
    )


@pytest.mark.parametrize(
    "nome",
    ["", " a.pdf", "a.pdf ", "../a.pdf", "pasta\\a.pdf", "a\x01.pdf", "a\n.pdf", "x" * 201],
)
def test_nome_e_so_um_rotulo(engine_app, ids, nome):
    assert _recusado(engine_app, lambda con: _arquivo(con, ids["u"], nome=nome)) == ("arquivo_nome")


def test_nome_com_acento_e_espaco_vale(engine_app, ids):
    with engine_app.begin() as con:
        _arquivo(con, ids["u"], nome="Ata de reunião (março) nº 3.pdf")
        _arquivo(con, ids["u"], nome="x" * 200)


@pytest.mark.parametrize(
    "tipo", ["application/x-msdownload", "image/svg+xml", "text/html", "application/zip"]
)
def test_so_pdf_e_imagens(engine_app, ids, tipo):
    assert _recusado(engine_app, lambda con: _arquivo(con, ids["u"], tipo=tipo)) == ("arquivo_tipo")


@pytest.mark.parametrize(
    ("finalidade", "tamanho", "vale"),
    [
        ("documento", 20 * MB, True),
        ("documento", 20 * MB + 1, False),
        ("aviso", 10 * MB, True),
        ("aviso", 10 * MB + 1, False),
        ("aviso", 0, False),
    ],
)
def test_limite_de_tamanho_por_finalidade(engine_app, ids, finalidade, tamanho, vale):
    def criar(con):
        _arquivo(con, ids["u"], finalidade=finalidade, tamanho=tamanho)

    if vale:
        with engine_app.begin() as con:
            criar(con)
    else:
        assert _recusado(engine_app, criar) == "arquivo_tamanho"


def test_finalidade_so_aviso_ou_documento(engine_app, ids):
    assert _recusado(engine_app, lambda con: _arquivo(con, ids["u"], finalidade="foto")) == (
        "arquivo_finalidade"
    )


def test_pendente_corrige_tipo_e_tamanho_e_pode_ser_apagado(engine_app, ids):
    with engine_app.begin() as con:
        arquivo = _arquivo(con, ids["u"], tipo="image/jpeg", confirmar=False)
        con.execute(
            text("update arquivo set tipo = 'image/png', tamanho_bytes = 77 where id = :a"),
            {"a": arquivo},
        )
        assert con.execute(
            text("select tipo, tamanho_bytes from arquivo where id = :a"), {"a": arquivo}
        ).one() == ("image/png", 77)
        con.execute(text("delete from arquivo where id = :a"), {"a": arquivo})


def test_confirmar_carimba_a_data_do_banco(engine_app, ids):
    with engine_app.begin() as con:
        arquivo = _arquivo(con, ids["u"], confirmar=False)
        con.execute(
            text("update arquivo set confirmado_em = '2000-01-01' where id = :a"), {"a": arquivo}
        )
        confirmado, agora = con.execute(
            text("select confirmado_em, now() from arquivo where id = :a"), {"a": arquivo}
        ).one()
    assert confirmado == agora


@pytest.mark.parametrize(
    "comando",
    [
        "update arquivo set tamanho_bytes = 5 where id = :a",
        "update arquivo set tipo = 'image/png' where id = :a",
        "update arquivo set confirmado_em = null where id = :a",
        "delete from arquivo where id = :a",
    ],
)
def test_confirmado_nunca_muda_nem_e_apagado(engine_app, ids, comando):
    with engine_app.begin() as con:
        arquivo = _arquivo(con, ids["u"])
    assert (
        _recusado(engine_app, lambda con: con.execute(text(comando), {"a": arquivo}))
        == "arquivo_confirmado"
    )


@pytest.mark.parametrize(
    "coluna", ["chave = 'ff'", "nome_original = 'x'", "finalidade = 'aviso'", "enviado_por = 1"]
)
def test_app_nao_muda_o_que_identifica_o_arquivo(engine_app, ids, coluna):
    with engine_app.begin() as con:
        _arquivo(con, ids["u"], confirmar=False)
    _negado(engine_app, f"update arquivo set {coluna}")


def test_ate_50_arquivos_por_unidade_por_dia(engine_app, ids):
    with engine_app.begin() as con:
        for _ in range(50):
            _arquivo(con, ids["u"], confirmar=False)
    assert _recusado(engine_app, lambda con: _arquivo(con, ids["u"])) == "arquivo_limite_dia"
    # Os apagados (recusados) não contam.
    with engine_app.begin() as con:
        con.execute(text("delete from arquivo where id = (select min(id) from arquivo)"))
        _arquivo(con, ids["u"])


# --- documento ---------------------------------------------------------------------------------


def test_documento_sem_versao_1_nao_fecha_a_transacao(engine_app, ids):
    def sem_versao(con):
        con.execute(
            text(
                "insert into documento (titulo, categoria, data_documento, acesso, criado_por)"
                " values ('Ata', 'ata', '2026-10-01', 'compradores', :u)"
            ),
            {"u": ids["u"]},
        )

    assert _recusado(engine_app, sem_versao) == "documento_completo"


def test_documento_completo_com_datas_do_banco(engine_app, ids):
    with engine_app.begin() as con:
        documento = _documento(
            con,
            ids["u"],
            _arquivo(con, ids["u"]),
            criado_em="2000-01-01",
            arquivado_em="2000-01-01",
        )
        criado, arquivado, enviada, agora = con.execute(
            text(
                "select d.criado_em, d.arquivado_em, v.enviada_em, now() from documento d"
                " join documento_versao v on v.documento_id = d.id where d.id = :d"
            ),
            {"d": documento},
        ).one()
    assert (criado, arquivado, enviada) == (agora, None, agora)


@pytest.mark.parametrize(
    ("coluna", "valor", "nome"),
    [
        ("categoria", "foto", "documento_categoria"),
        ("acesso", "todos", "documento_acesso"),
        ("data_documento", "1989-12-31", "documento_data"),
        ("data_documento", "2101-01-01", "documento_data"),
        ("titulo", "   ", "documento_titulo_tamanho"),
        ("titulo", "x" * 121, "documento_titulo_tamanho"),
    ],
)
def test_documento_campos_no_formato(engine_app, ids, coluna, valor, nome):
    def criar(con):
        _documento(con, ids["u"], _arquivo(con, ids["u"]), **{coluna: valor})

    assert _recusado(engine_app, criar) == nome


@pytest.mark.parametrize(
    "categoria", ["convencao", "regimento", "ata", "contrato", "obra", "orientacao", "outro"]
)
def test_categorias_do_documento(engine_app, ids, categoria):
    with engine_app.begin() as con:
        _documento(con, ids["u"], _arquivo(con, ids["u"]), categoria=categoria)


def test_arquivado_nao_volta(engine_app, ids):
    with engine_app.begin() as con:
        documento = _documento(con, ids["u"], _arquivo(con, ids["u"]))
        con.execute(
            text("update documento set arquivado_em = '2000-01-01' where id = :d"),
            {"d": documento},
        )
        arquivado, agora = con.execute(
            text("select arquivado_em, now() from documento where id = :d"), {"d": documento}
        ).one()
    assert arquivado == agora
    assert (
        _recusado(
            engine_app,
            lambda con: con.execute(
                text("update documento set arquivado_em = null where id = :d"), {"d": documento}
            ),
        )
        == "documento_arquivado"
    )


@pytest.mark.parametrize(
    "coluna",
    ["titulo = 'Outro'", "acesso = 'publico'", "categoria = 'ata'", "data_documento = now()"],
)
def test_app_nao_muda_os_dados_do_documento(engine_app, ids, coluna):
    with engine_app.begin() as con:
        _documento(con, ids["u"], _arquivo(con, ids["u"]))
    _negado(engine_app, f"update documento set {coluna}")


@pytest.mark.parametrize("tabela", ["documento", "documento_versao", "aviso_anexo"])
def test_app_nao_apaga_documento_versao_nem_anexo(engine_app, ids, tabela):
    _negado(engine_app, f"delete from {tabela}")


@pytest.mark.parametrize(("acesso", "vale"), [("publico", True), ("compradores", True)])
def test_aviso_automatico_de_documento_que_as_unidades_veem(engine_app, ids, acesso, vale):
    with engine_app.begin() as con:
        _documento(con, ids["u"], _arquivo(con, ids["u"]), acesso=acesso, aviso_id=ids["a"])


def test_aviso_automatico_nunca_de_documento_da_gestao(engine_app, ids):
    def criar(con):
        _documento(con, ids["u"], _arquivo(con, ids["u"]), acesso="gestao", aviso_id=ids["a"])

    assert _recusado(engine_app, criar) == "documento_aviso_gestao"


def test_um_aviso_automatico_por_documento(engine_app, ids):
    with engine_app.begin() as con:
        _documento(con, ids["u"], _arquivo(con, ids["u"]), aviso_id=ids["a"])
    assert (
        _recusado(
            engine_app,
            lambda con: _documento(con, ids["u"], _arquivo(con, ids["u"]), aviso_id=ids["a"]),
        )
        == "documento_aviso_id_key"
    )


# --- documento_versao --------------------------------------------------------------------------


def test_versoes_em_sequencia(engine_app, ids):
    with engine_app.begin() as con:
        documento = _documento(con, ids["u"], _arquivo(con, ids["u"]))
        _versao(con, documento, 2, _arquivo(con, ids["u"]), ids["u"])
    assert (
        _recusado(
            engine_app,
            lambda con: _versao(con, documento, 4, _arquivo(con, ids["u"]), ids["u"]),
        )
        == "documento_versao_sequencia"
    )


def test_versao_so_com_arquivo_confirmado(engine_app, ids):
    def criar(con):
        _documento(con, ids["u"], _arquivo(con, ids["u"], confirmar=False))

    assert _recusado(engine_app, criar) == "arquivo_nao_confirmado"


def test_versao_so_com_arquivo_de_documento(engine_app, ids):
    def criar(con):
        _documento(con, ids["u"], _arquivo(con, ids["u"], finalidade="aviso"))

    assert _recusado(engine_app, criar) == "arquivo_finalidade_errada"


def test_o_mesmo_arquivo_nao_serve_a_duas_versoes(engine_app, ids):
    with engine_app.begin() as con:
        arquivo = _arquivo(con, ids["u"])
        documento = _documento(con, ids["u"], arquivo)
    assert (
        _recusado(engine_app, lambda con: _versao(con, documento, 2, arquivo, ids["u"]))
        == "arquivo_em_uso"
    )
    assert _recusado(engine_app, lambda con: _documento(con, ids["u"], arquivo)) == "arquivo_em_uso"


def test_documento_arquivado_nao_ganha_versao(engine_app, ids):
    with engine_app.begin() as con:
        documento = _documento(con, ids["u"], _arquivo(con, ids["u"]))
        con.execute(
            text("update documento set arquivado_em = now() where id = :d"), {"d": documento}
        )
    assert (
        _recusado(
            engine_app,
            lambda con: _versao(con, documento, 2, _arquivo(con, ids["u"]), ids["u"]),
        )
        == "documento_arquivado"
    )


# --- aviso_anexo -------------------------------------------------------------------------------


def _aviso_com_anexos(con, unidade: int, arquivos: list[int]) -> int:
    aviso = _aviso(con, unidade)
    for ordem, arquivo in enumerate(arquivos, start=1):
        _anexo(con, aviso, 1, arquivo, ordem)
    return aviso


def test_anexo_entra_junto_com_a_versao(engine_app, ids):
    with engine_app.begin() as con:
        aviso = _aviso_com_anexos(
            con, ids["u"], [_arquivo(con, ids["u"], finalidade="aviso") for _ in range(5)]
        )
        quantos = con.execute(
            text("select count(*) from aviso_anexo where aviso_id = :a"), {"a": aviso}
        ).scalar_one()
    assert quantos == 5


def test_versao_publicada_nao_ganha_anexo_depois(engine_app, ids):
    # O aviso da fixture foi publicado em outra transação.
    def anexar(con):
        _anexo(con, ids["a"], 1, _arquivo(con, ids["u"], finalidade="aviso"))

    assert _recusado(engine_app, anexar) == "aviso_anexo_versao_fechada"


def test_no_maximo_5_anexos_por_versao(engine_app, ids):
    def seis(con):
        aviso = _aviso(con, ids["u"])
        _anexo(con, aviso, 1, _arquivo(con, ids["u"], finalidade="aviso"), 6)

    assert _recusado(engine_app, seis) == "aviso_anexo_ordem"

    def ordem_repetida(con):
        aviso = _aviso(con, ids["u"])
        _anexo(con, aviso, 1, _arquivo(con, ids["u"], finalidade="aviso"), 1)
        _anexo(con, aviso, 1, _arquivo(con, ids["u"], finalidade="aviso"), 1)

    assert _recusado(engine_app, ordem_repetida) == "aviso_anexo_ordem_unica"


@pytest.mark.parametrize(
    ("argumentos", "nome"),
    [
        ({"finalidade": "documento"}, "arquivo_finalidade_errada"),
        ({"finalidade": "aviso", "confirmar": False}, "arquivo_nao_confirmado"),
    ],
)
def test_anexo_so_com_arquivo_de_aviso_confirmado(engine_app, ids, argumentos, nome):
    def anexar(con):
        _aviso_com_anexos(con, ids["u"], [_arquivo(con, ids["u"], **argumentos)])

    assert _recusado(engine_app, anexar) == nome


def test_correcao_repete_os_anexos_do_mesmo_aviso(engine_app, ids):
    with engine_app.begin() as con:
        arquivo = _arquivo(con, ids["u"], finalidade="aviso")
        aviso = _aviso_com_anexos(con, ids["u"], [arquivo])
    with engine_app.begin() as con:
        con.execute(
            text(
                "insert into aviso_versao (aviso_id, versao, titulo, texto, criada_por)"
                " values (:a, 2, 'Título', 'Corrigido', :u)"
            ),
            {"a": aviso, "u": ids["u"]},
        )
        _anexo(con, aviso, 2, arquivo)


def test_anexo_de_um_aviso_nao_vai_para_outro_nem_para_documento(engine_app, ids):
    with engine_app.begin() as con:
        arquivo = _arquivo(con, ids["u"], finalidade="aviso")
        _aviso_com_anexos(con, ids["u"], [arquivo])
    assert (
        _recusado(engine_app, lambda con: _aviso_com_anexos(con, ids["u"], [arquivo]))
        == "arquivo_em_uso"
    )


def test_arquivo_de_documento_nao_vira_anexo(engine_app, ids):
    # Mesmo que a finalidade fosse trocada à força: o documento já usa o arquivo.
    with engine_app.begin() as con:
        arquivo = _arquivo(con, ids["u"])
        _documento(con, ids["u"], arquivo)

    def anexar(con):
        _aviso_com_anexos(con, ids["u"], [arquivo])

    assert _recusado(engine_app, anexar) in {"arquivo_finalidade_errada", "arquivo_em_uso"}


def test_arquivo_em_uso_nao_e_apagado_nem_pendente_vira_anexo_por_engano(engine_app, ids):
    with engine_app.begin() as con:
        arquivo = _arquivo(con, ids["u"], finalidade="aviso")
        _aviso_com_anexos(con, ids["u"], [arquivo])
    assert (
        _recusado(
            engine_app,
            lambda con: con.execute(text("delete from arquivo where id = :a"), {"a": arquivo}),
        )
        == "arquivo_confirmado"
    )
