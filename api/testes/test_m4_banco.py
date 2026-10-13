"""Regras de banco do M4 (migração 0008), com SQL direto: as tentativas de burlar.

Roadmap do M4: "as regras que o banco garante (um voto por unidade, nada de voto depois do
prazo, nada de editar depois do 1º voto) ganham teste que tenta burlar cada uma direto no
banco". Cada tentativa roda como `app` (o que a API usa) **e** como `dono` (quem roda as
migrações): as triggers valem para os dois. Spec: `docs/superpowers/specs/m4-contrato.md`,
seção 2.
"""

import threading
import time

import pytest
from psycopg.errors import InsufficientPrivilege
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError, ProgrammingError

from testes.apoio import criar_bloco, criar_unidade, restricao

pytestmark = pytest.mark.usefixtures("banco_limpo")


@pytest.fixture(params=["app", "dono"])
def engine(request, engine_app, engine_dono) -> Engine:
    """As tentativas de burlar rodam com os dois papéis."""
    return engine_app if request.param == "app" else engine_dono


@pytest.fixture
def ids(engine_app) -> dict[str, int]:
    """Bloco 1 com a unidade `u` (ativada) e `u2`; bloco 2 com `v`."""
    with engine_app.begin() as con:
        b1, b2 = criar_bloco(con, 1), criar_bloco(con, 2)
        ativada = {
            "precisa_trocar_senha": False,
            "ativada_em": "2026-10-01",
            "responsavel_nome": "Fictício",
            "celular": "81900000001",
        }
        u = criar_unidade(con, b1, "101", **ativada)
        u2 = criar_unidade(con, b1, "102", **ativada)
        v = criar_unidade(con, b2, "201", **ativada)
    return {"b1": b1, "b2": b2, "u": u, "u2": u2, "v": v}


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
            " values (:a, 1, 'Enquete nova', 'Vote', :u)"
        ),
        {"a": a, "u": unidade},
    )
    return a


def _enquete(
    con,
    autor: int,
    *,
    opcoes: tuple[str, ...] = ("Terça à noite", "Quinta à noite", "Sábado de manhã"),
    blocos: tuple[int, ...] = (),
    multipla: bool = False,
    encerra: str = "now() + interval '7 days'",
    pergunta: str = "Qual o melhor dia para a reunião?",
    para_todos: bool | None = None,
) -> int:
    """Cria a enquete inteira na transação de `con` (aviso, enquete, opções, blocos)."""
    enquete = con.execute(
        text(
            "insert into enquete (pergunta, multipla_escolha, mostrar_resultado, encerra_em,"
            f" para_todos, criada_por, aviso_id) values (:p, :m, 'durante', {encerra},"
            " :todos, :u, :a) returning id"
        ),
        {
            "p": pergunta,
            "m": multipla,
            "todos": (not blocos) if para_todos is None else para_todos,
            "u": autor,
            "a": _aviso(con, autor),
        },
    ).scalar_one()
    for ordem, texto in enumerate(opcoes, start=1):
        con.execute(
            text("insert into enquete_opcao (enquete_id, texto, ordem) values (:e, :t, :o)"),
            {"e": enquete, "t": texto, "o": ordem},
        )
    for bloco in blocos:
        con.execute(
            text("insert into enquete_bloco (enquete_id, bloco_id) values (:e, :b)"),
            {"e": enquete, "b": bloco},
        )
    return enquete


def _opcoes(con, enquete: int) -> list[int]:
    return list(
        con.execute(
            text("select id from enquete_opcao where enquete_id = :e order by ordem"),
            {"e": enquete},
        ).scalars()
    )


def _votar(con, enquete: int, unidade: int, *opcoes: int) -> None:
    """A gravação do voto como o épico B faz (spec, seção 2.6)."""
    con.execute(
        text(
            "insert into voto (enquete_id, unidade_id) values (:e, :u)"
            " on conflict (enquete_id, unidade_id) do update set votado_em = excluded.votado_em"
        ),
        {"e": enquete, "u": unidade},
    )
    con.execute(
        text("delete from voto_opcao where enquete_id = :e and unidade_id = :u"),
        {"e": enquete, "u": unidade},
    )
    for opcao in opcoes:
        con.execute(
            text("insert into voto_opcao (enquete_id, unidade_id, opcao_id) values (:e, :u, :o)"),
            {"e": enquete, "u": unidade, "o": opcao},
        )


def _vencer(engine: Engine, enquete: int) -> None:
    """Simula o prazo passando: só o superusuário consegue (sem as triggers)."""
    with engine.begin() as con:
        con.execute(text("set local session_replication_role = replica"))
        con.execute(
            text(
                "update enquete set encerra_em = now() - interval '1 minute',"
                " criada_em = now() - interval '2 days' where id = :e"
            ),
            {"e": enquete},
        )


def _recusado(engine: Engine, nome: str, comando: str, **parametros) -> None:
    with pytest.raises(DBAPIError) as erro, engine.begin() as con:
        con.execute(text(comando), parametros)
    assert restricao(erro.value) == nome, erro.value


@pytest.fixture
def aberta(engine_app, ids) -> dict[str, int]:
    with engine_app.begin() as con:
        e = _enquete(con, ids["u"])
        a, b, c = _opcoes(con, e)
    return {**ids, "e": e, "a": a, "b": b, "c": c}


@pytest.fixture
def votada(engine_app, aberta) -> dict[str, int]:
    with engine_app.begin() as con:
        _votar(con, aberta["e"], aberta["u"], aberta["a"])
    return aberta


def _votos(engine: Engine, enquete: int) -> list[tuple[int, list[int]]]:
    with engine.connect() as con:
        return [
            (u, list(o))
            for u, o in con.execute(
                text(
                    "select v.unidade_id, array_agg(o.opcao_id order by o.opcao_id)"
                    " from voto v join voto_opcao o using (enquete_id, unidade_id)"
                    " where v.enquete_id = :e group by v.unidade_id order by v.unidade_id"
                ),
                {"e": enquete},
            )
        ]


# --- a enquete -----------------------------------------------------------------------------------


def test_datas_da_enquete_sao_do_banco(engine_app, ids):
    with engine_app.begin() as con:
        e = _enquete(con, ids["u"])
        linha = con.execute(
            text("select criada_em = now(), editada_em from enquete where id = :e"), {"e": e}
        ).one()
    assert tuple(linha) == (True, None)


@pytest.mark.parametrize("opcoes", [("Só uma",), ()])
def test_enquete_precisa_de_duas_opcoes_no_commit(engine, ids, opcoes):
    with pytest.raises(DBAPIError) as erro, engine.begin() as con:
        _enquete(con, ids["u"], opcoes=opcoes)
    assert restricao(erro.value) == "enquete_completa"


def test_onze_opcoes_recusadas(engine, ids):
    with pytest.raises(DBAPIError) as erro, engine.begin() as con:
        _enquete(con, ids["u"], opcoes=tuple(f"Opção {n}" for n in range(1, 12)))
    # A 11ª é recusada já na inserção (pela trigger ou pelo CHECK da ordem).
    assert restricao(erro.value) in {"enquete_opcoes", "enquete_opcao_ordem"}


def test_dez_opcoes_passam(engine_app, ids):
    with engine_app.begin() as con:
        e = _enquete(con, ids["u"], opcoes=tuple(f"Opção {n}" for n in range(1, 11)))
        assert len(_opcoes(con, e)) == 10


@pytest.mark.parametrize(
    ("troca", "nome"),
    [
        ({"pergunta": "   "}, "enquete_pergunta_tamanho"),
        ({"pergunta": "x" * 201}, "enquete_pergunta_tamanho"),
        ({"opcoes": ("A", "A")}, "enquete_opcao_texto_unico"),
        ({"opcoes": ("A", " ")}, "enquete_opcao_texto_tamanho"),
        ({"opcoes": ("A", "x" * 101)}, "enquete_opcao_texto_tamanho"),
        ({"encerra": "now() - interval '1 minute'"}, "enquete_encerramento"),
        ({"encerra": "now()"}, "enquete_encerramento"),
        ({"encerra": "now() + interval '367 days'"}, "enquete_encerramento"),
    ],
)
def test_campos_da_enquete(engine, ids, troca, nome):
    with pytest.raises(DBAPIError) as erro, engine.begin() as con:
        _enquete(con, ids["u"], **troca)
    assert restricao(erro.value) == nome


def test_mostrar_resultado_so_os_dois_valores(engine_app, ids):
    with pytest.raises(IntegrityError) as erro, engine_app.begin() as con:
        e = _enquete(con, ids["u"])
        con.execute(text("update enquete set mostrar_resultado = 'nunca' where id = :e"), {"e": e})
    assert restricao(erro.value) == "enquete_mostrar_resultado"


def test_enquete_por_bloco_precisa_de_bloco(engine, ids):
    with pytest.raises(DBAPIError) as erro, engine.begin() as con:
        _enquete(con, ids["u"], para_todos=False)
    assert restricao(erro.value) == "enquete_completa"


def test_enquete_para_todos_nao_tem_bloco(engine, ids):
    with pytest.raises(DBAPIError) as erro, engine.begin() as con:
        e = _enquete(con, ids["u"])
        con.execute(
            text("insert into enquete_bloco (enquete_id, bloco_id) values (:e, :b)"),
            {"e": e, "b": ids["b1"]},
        )
    assert restricao(erro.value) == "enquete_bloco_destino"


def test_destino_so_na_criacao(engine, ids):
    with engine.begin() as con:
        e = _enquete(con, ids["u"], blocos=(ids["b1"],))
    _recusado(
        engine,
        "enquete_destino_fechado",
        "insert into enquete_bloco (enquete_id, bloco_id) values (:e, :b)",
        e=e,
        b=ids["b2"],
    )


def test_aviso_obrigatorio_e_unico(engine_app, engine_dono, ids):
    with pytest.raises(IntegrityError), engine_app.begin() as con:
        con.execute(
            text(
                "insert into enquete (pergunta, encerra_em, para_todos, criada_por)"
                " values ('P', now() + interval '1 day', true, :u)"
            ),
            {"u": ids["u"]},
        )
    with engine_app.begin() as con:
        e = _enquete(con, ids["u"])
        aviso = con.execute(
            text("select aviso_id from enquete where id = :e"), {"e": e}
        ).scalar_one()
    # Uma enquete por aviso (o `app` nem pode mudar o `aviso_id`; o `dono` bate na unicidade).
    with pytest.raises(IntegrityError), engine_dono.begin() as con:
        outra = _enquete(con, ids["u"])
        con.execute(
            text("update enquete set aviso_id = :a where id = :e"), {"a": aviso, "e": outra}
        )


# --- editar antes do 1º voto pode ----------------------------------------------------------------


def test_editar_antes_do_primeiro_voto(engine_app, aberta):
    with engine_app.begin() as con:
        con.execute(
            text(
                "update enquete set pergunta = 'Qual o melhor horário?', multipla_escolha = true,"
                " mostrar_resultado = 'so_no_fim', encerra_em = now() + interval '3 days'"
                " where id = :e"
            ),
            {"e": aberta["e"]},
        )
        con.execute(text("delete from enquete_opcao where enquete_id = :e"), {"e": aberta["e"]})
        for ordem, texto in enumerate(("Manhã", "Noite"), start=1):
            con.execute(
                text("insert into enquete_opcao (enquete_id, texto, ordem) values (:e, :t, :o)"),
                {"e": aberta["e"], "t": texto, "o": ordem},
            )
        editada = con.execute(
            text("select editada_em = now() from enquete where id = :e"), {"e": aberta["e"]}
        ).scalar_one()
    assert editada is True


def test_editar_deixando_uma_opcao_recusado_no_commit(engine_app, aberta):
    with pytest.raises(DBAPIError) as erro, engine_app.begin() as con:
        con.execute(
            text("delete from enquete_opcao where id in (:a, :b)"),
            {"a": aberta["a"], "b": aberta["b"]},
        )
    assert restricao(erro.value) == "enquete_completa"


# --- regra 1: um voto por unidade (RN-01) --------------------------------------------------------


def test_segundo_voto_da_unidade_recusado(engine, votada):
    _recusado(
        engine,
        "voto_pkey",
        "insert into voto (enquete_id, unidade_id) values (:e, :u)",
        e=votada["e"],
        u=votada["u"],
    )


def test_trocar_o_voto_vale_o_ultimo(engine_app, votada):
    with engine_app.begin() as con:
        _votar(con, votada["e"], votada["u"], votada["c"])
    assert _votos(engine_app, votada["e"]) == [(votada["u"], [votada["c"]])]


def test_escolha_unica_com_duas_opcoes_recusada_no_commit(engine, votada):
    _recusado(
        engine,
        "voto_completo",
        "insert into voto_opcao (enquete_id, unidade_id, opcao_id) values (:e, :u, :o)",
        e=votada["e"],
        u=votada["u"],
        o=votada["b"],
    )


def test_voto_sem_opcao_recusado_no_commit(engine, aberta):
    _recusado(
        engine,
        "voto_completo",
        "insert into voto (enquete_id, unidade_id) values (:e, :u)",
        e=aberta["e"],
        u=aberta["u"],
    )


def test_multipla_escolha_aceita_varias(engine_app, ids):
    with engine_app.begin() as con:
        e = _enquete(con, ids["u"], multipla=True)
        a, b, c = _opcoes(con, e)
        _votar(con, e, ids["u"], a, c)
    assert _votos(engine_app, e) == [(ids["u"], [a, c])]


def test_opcao_de_outra_enquete_recusada(engine, aberta):
    with engine.begin() as con:
        outra = _enquete(con, aberta["u"])
        [alheia, *_] = _opcoes(con, outra)
    with pytest.raises(IntegrityError), engine.begin() as con:
        _votar(con, aberta["e"], aberta["u"], alheia)


def test_voto_fora_do_destino_recusado(engine, ids):
    with engine.begin() as con:
        e = _enquete(con, ids["u"], blocos=(ids["b1"],))
        [a, *_] = _opcoes(con, e)
    with pytest.raises(DBAPIError) as erro, engine.begin() as con:
        _votar(con, e, ids["v"], a)
    assert restricao(erro.value) == "voto_fora_do_destino"
    with engine.begin() as con:
        _votar(con, e, ids["u2"], a)


def test_dois_celulares_da_mesma_unidade_ao_mesmo_tempo(engine_app, aberta):
    """Critério de pronto do M4: um voto só, com as opções inteiras de um dos dois."""
    barreira = threading.Barrier(2)
    erros: list[BaseException] = []

    def celular(opcao: int, espera: float) -> None:
        try:
            with engine_app.begin() as con:
                barreira.wait()
                _votar(con, aberta["e"], aberta["u"], opcao)
                time.sleep(espera)
        except BaseException as erro:  # noqa: BLE001
            erros.append(erro)

    fios = [
        threading.Thread(target=celular, args=(aberta["a"], 0.3)),
        threading.Thread(target=celular, args=(aberta["b"], 0.0)),
    ]
    for fio in fios:
        fio.start()
    for fio in fios:
        fio.join()
    assert erros == []
    [(unidade, opcoes)] = _votos(engine_app, aberta["e"])
    assert unidade == aberta["u"] and opcoes in ([aberta["a"]], [aberta["b"]])


def test_mesma_unidade_multipla_escolha_nao_mistura(engine_app, ids):
    with engine_app.begin() as con:
        e = _enquete(con, ids["u"], multipla=True)
        a, b, c = _opcoes(con, e)
    barreira = threading.Barrier(2)

    def celular(*opcoes: int) -> None:
        with engine_app.begin() as con:
            barreira.wait()
            _votar(con, e, ids["u"], *opcoes)

    fios = [
        threading.Thread(target=celular, args=(a, b)),
        threading.Thread(target=celular, args=(c,)),
    ]
    for fio in fios:
        fio.start()
    for fio in fios:
        fio.join()
    [(_, opcoes)] = _votos(engine_app, e)
    assert opcoes in ([a, b], [c])


# --- regra 2: nada de voto depois do prazo -------------------------------------------------------


def test_voto_depois_do_prazo_recusado(engine, engine_superusuario, aberta):
    _vencer(engine_superusuario, aberta["e"])
    with pytest.raises(DBAPIError) as erro, engine.begin() as con:
        _votar(con, aberta["e"], aberta["u"], aberta["a"])
    assert restricao(erro.value) == "enquete_encerrada"


def test_troca_depois_do_prazo_recusada(engine, engine_superusuario, votada):
    _vencer(engine_superusuario, votada["e"])
    for comando in (
        "update voto set votado_em = now() where enquete_id = :e and unidade_id = :u",
        "delete from voto_opcao where enquete_id = :e and unidade_id = :u",
    ):
        _recusado(engine, "enquete_encerrada", comando, e=votada["e"], u=votada["u"])
    # Mexendo só em `voto_opcao`, sem tocar no `voto`.
    _recusado(
        engine,
        "enquete_encerrada",
        "insert into voto_opcao (enquete_id, unidade_id, opcao_id) values (:e, :u, :o)",
        e=votada["e"],
        u=votada["u"],
        o=votada["b"],
    )
    assert _votos(engine, votada["e"]) == [(votada["u"], [votada["a"]])]


def test_encerrada_sem_voto_nao_reabre(engine, engine_superusuario, aberta):
    _vencer(engine_superusuario, aberta["e"])
    _recusado(
        engine,
        "enquete_encerrada",
        "update enquete set encerra_em = now() + interval '1 day' where id = :e",
        e=aberta["e"],
    )
    _recusado(engine, "enquete_encerrada", "delete from enquete_opcao where id = :a", a=aberta["a"])


# --- regra 3: nada de editar depois do 1º voto ---------------------------------------------------


@pytest.mark.parametrize(
    "mudanca",
    [
        "pergunta = 'Outra pergunta'",
        "multipla_escolha = true",
        "mostrar_resultado = 'so_no_fim'",
        "encerra_em = encerra_em + interval '1 day'",
        "encerra_em = now() + interval '1 hour'",
    ],
)
def test_editar_depois_do_primeiro_voto_recusado(engine, votada, mudanca):
    _recusado(
        engine, "enquete_com_voto", f"update enquete set {mudanca} where id = :e", e=votada["e"]
    )


def test_opcoes_nao_mudam_depois_do_primeiro_voto(engine, votada):
    _recusado(
        engine,
        "enquete_com_voto",
        "insert into enquete_opcao (enquete_id, texto, ordem) values (:e, 'Domingo', 4)",
        e=votada["e"],
    )
    _recusado(engine, "enquete_com_voto", "delete from enquete_opcao where id = :c", c=votada["c"])


def test_editar_com_voto_em_andamento_espera_e_e_recusado(engine_app, aberta):
    """O voto começa (trava a enquete em modo compartilhado); a edição espera e, quando o voto
    termina, é recusada: não passa por baixo do primeiro voto."""
    votou = threading.Event()
    resultado: list[str | None] = []

    def editar() -> None:
        votou.wait()
        try:
            with engine_app.begin() as con:
                con.execute(
                    text("update enquete set pergunta = 'Mudou' where id = :e"), {"e": aberta["e"]}
                )
            resultado.append(None)
        except DBAPIError as erro:
            resultado.append(restricao(erro))

    fio = threading.Thread(target=editar)
    fio.start()
    with engine_app.begin() as con:
        _votar(con, aberta["e"], aberta["u"], aberta["a"])
        votou.set()
        time.sleep(0.4)
        assert resultado == []  # a edição está esperando
    fio.join()
    assert resultado == ["enquete_com_voto"]


# --- permissões do `app` -------------------------------------------------------------------------


def _negado(engine: Engine, comando: str, **parametros) -> None:
    with pytest.raises(ProgrammingError) as erro, engine.begin() as con:
        con.execute(text(comando), parametros)
    assert isinstance(erro.value.orig, InsufficientPrivilege)


@pytest.mark.parametrize(
    "comando",
    [
        "delete from enquete",
        "delete from voto",
        "delete from enquete_bloco",
        "update enquete set para_todos = false",
        "update enquete set criada_por = criada_por",
        "update enquete set aviso_id = aviso_id",
        "update enquete set criada_em = now()",
        "update enquete set editada_em = now()",
        "update enquete_opcao set texto = 'Outra'",
        "update enquete_bloco set bloco_id = bloco_id",
        "update voto set unidade_id = unidade_id",
        "update voto_opcao set opcao_id = opcao_id",
    ],
)
def test_app_sem_permissao(engine_app, votada, comando):
    _negado(engine_app, comando)
