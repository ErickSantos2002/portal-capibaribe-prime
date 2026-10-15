"""Épico A do M4 · criar e editar enquetes (H-20) com o aviso automático (H-13). Spec do épico:
`docs/superpowers/specs/m4-gestao.md`. Sessão, permissão, CSRF e validação do corpo estão em
`test_m4_rotas.py`."""

from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest
from sqlalchemy import Engine, text

from app.servicos.enquetes_gestao import quando_em_texto
from testes.apoio_m4 import votar
from testes.conftest import ADMIN, COMISSAO, COMUM
from testes.test_avisos_apoio import historico

pytestmark = pytest.mark.usefixtures("predio")

RECIFE = timezone(timedelta(hours=-3))
# Daqui a 10 dias, às 20h de Recife: o texto do aviso fica previsível.
TERMINO = (datetime.now(RECIFE) + timedelta(days=10)).replace(
    hour=20, minute=0, second=0, microsecond=0
)
OPCOES = ["Terça à noite", "Quinta à noite", "Sábado de manhã"]
PERGUNTA = "Qual o melhor dia para a reunião com a construtora?"


def corpo(**troca: Any) -> dict[str, Any]:
    dados: dict[str, Any] = {
        "pergunta": PERGUNTA,
        "opcoes": OPCOES,
        "encerra_em": TERMINO.isoformat(),
        "para_todos": True,
    }
    return {**dados, **troca}


def edicao(**troca: Any) -> dict[str, Any]:
    """O corpo de editar: tudo obrigatório, e `editada_em_base` nulo (enquete nunca editada)."""
    dados = {k: v for k, v in corpo().items() if k != "para_todos"}
    dados.update(multipla_escolha=False, mostrar_resultado="durante", editada_em_base=None)
    return {**dados, **troca}


@pytest.fixture
def agendados(monkeypatch) -> list[int]:
    """Os avisos que a rota mandou notificar (depois do commit)."""
    from app.rotas import enquetes_gestao

    chamados: list[int] = []
    monkeypatch.setattr(
        enquetes_gestao.notificacoes,
        "agendar",
        lambda _tarefas, aviso_id: chamados.append(aviso_id),
    )
    return chamados


def criar(logar, login: str = COMISSAO, **troca: Any) -> dict[str, int]:
    resposta = logar(login).post("/api/enquetes", json=corpo(**troca))
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _linha(engine: Engine, sql: str, **parametros) -> Any:
    with engine.connect() as con:
        return con.execute(text(sql), parametros).one()


def _todas(engine: Engine, sql: str, **parametros) -> list[Any]:
    with engine.connect() as con:
        return list(con.execute(text(sql), parametros))


def _opcoes(engine: Engine, enquete: int) -> list[tuple[int, str, int]]:
    return [
        tuple(linha)
        for linha in _todas(
            engine,
            "select id, texto, ordem from enquete_opcao where enquete_id = :e order by ordem",
            e=enquete,
        )
    ]


def _contar(engine: Engine, tabela: str) -> int:
    with engine.connect() as con:
        return con.execute(text(f"select count(*) from {tabela}")).scalar_one()  # noqa: S608


def _texto_esperado(
    pergunta: str = PERGUNTA,
    opcoes: list[str] = OPCOES,
    termino: datetime = TERMINO,
    escolha: str = "Marque uma opção.",
    resultado: str = "O resultado aparece durante a votação.",
) -> str:
    lista = "\n".join(f"- {o}" for o in opcoes)
    return (
        f"Uma enquete nova está aberta no Portal: “{pergunta}”.\n\n"
        f"As opções são:\n\n{lista}\n\n"
        f"Dá para votar até {quando_em_texto(termino)} (horário de"
        f" Recife). {escolha} Vale um voto por apartamento, e dá para trocar o voto até o fim."
        f" {resultado}\n\n"
        "> Enquete é consulta. Não tem valor legal de votação em assembleia.\n\n"
        "O botão “Ir para a enquete”, neste aviso, leva direto a ela."
    )


# --- criar -------------------------------------------------------------------------------------


def test_criar_grava_a_enquete_as_opcoes_e_o_aviso(logar, engine_app, predio, agendados):
    gravada = criar(logar)
    assert set(gravada) == {"id", "aviso_id"}
    enquete = _linha(
        engine_app,
        "select pergunta, multipla_escolha, mostrar_resultado, encerra_em, para_todos,"
        " criada_por, aviso_id, editada_em from enquete where id = :e",
        e=gravada["id"],
    )
    assert enquete.pergunta == PERGUNTA
    assert enquete.multipla_escolha is False
    assert enquete.mostrar_resultado == "durante"
    assert enquete.encerra_em == TERMINO
    assert enquete.para_todos is True
    assert enquete.criada_por == predio[COMISSAO]
    assert enquete.aviso_id == gravada["aviso_id"]
    assert enquete.editada_em is None
    assert [(t, o) for _, t, o in _opcoes(engine_app, gravada["id"])] == [
        ("Terça à noite", 1),
        ("Quinta à noite", 2),
        ("Sábado de manhã", 3),
    ]
    assert _contar(engine_app, "enquete_bloco") == 0


def test_o_aviso_automatico_sai_no_mural_com_a_enquete(logar, agendados, engine_app):
    gravada = criar(logar)
    aviso = logar(COMUM).get(f"/api/avisos/{gravada['aviso_id']}").json()
    assert aviso["titulo"] == f"Enquete nova: {PERGUNTA}"
    assert aviso["texto"] == _texto_esperado()
    assert aviso["categoria"] == "geral"
    assert aviso["para_todos"] is True
    assert aviso["fixado"] is False
    enquete = aviso["enquete"]
    assert {k: enquete[k] for k in ("id", "pergunta", "encerrada")} == {
        "id": gravada["id"],
        "pergunta": PERGUNTA,
        "encerrada": False,
    }
    assert datetime.fromisoformat(enquete["encerra_em"]) == TERMINO
    # H-13: notifica como qualquer aviso, depois do commit (M2).
    assert agendados == [gravada["aviso_id"]]
    assert _contar(engine_app, "notificacao_envio") > 0


def test_o_texto_do_aviso_segue_a_escolha_e_o_resultado(logar, agendados):
    gravada = criar(logar, multipla_escolha=True, mostrar_resultado="so_no_fim")
    aviso = logar(COMUM).get(f"/api/avisos/{gravada['aviso_id']}").json()
    assert aviso["texto"] == _texto_esperado(
        escolha="Pode marcar mais de uma opção.",
        resultado="O resultado só aparece quando a enquete terminar.",
    )


def test_o_termino_vai_no_horario_de_recife(logar, agendados):
    termino_utc = (TERMINO + timedelta(minutes=5)).astimezone(UTC)
    gravada = criar(logar, encerra_em=termino_utc.isoformat())
    aviso = logar(COMUM).get(f"/api/avisos/{gravada['aviso_id']}").json()
    assert "às 20h05 (horário de Recife)" in aviso["texto"]


def test_pergunta_comprida_e_cortada_no_titulo_do_aviso(logar, agendados):
    pergunta = "Vocês " + "x" * 190 + "?"
    gravada = criar(logar, pergunta=pergunta)
    aviso = logar(COMUM).get(f"/api/avisos/{gravada['aviso_id']}").json()
    assert len(aviso["titulo"]) == 120
    assert aviso["titulo"].startswith("Enquete nova: Vocês xxx")
    assert aviso["titulo"].endswith("…")
    assert f"“{pergunta}”" in aviso["texto"]


def test_opcoes_em_branco_sao_descartadas_e_a_ordem_fica(logar, engine_app, agendados):
    gravada = criar(logar, opcoes=["  Sim ", "", "Não", "   "])
    assert [t for _, t, _ in _opcoes(engine_app, gravada["id"])] == ["Sim", "Não"]


def test_para_blocos_grava_o_destino_da_enquete_e_do_aviso(logar, engine_app, predio, agendados):
    gravada = criar(logar, para_todos=False, blocos=[3, 1])
    blocos = [
        n
        for (n,) in _todas(
            engine_app,
            "select b.numero from enquete_bloco eb join bloco b on b.id = eb.bloco_id"
            " where eb.enquete_id = :e order by b.numero",
            e=gravada["id"],
        )
    ]
    assert blocos == [1, 3]
    aviso = logar(COMISSAO).get(f"/api/avisos/{gravada['aviso_id']}").json()
    assert aviso["para_todos"] is False
    assert aviso["blocos"] == [1, 3]
    # 1203 é do Bloco 1: vê; um morador do Bloco 2 não veria.
    assert logar(COMUM).get(f"/api/avisos/{gravada['aviso_id']}").status_code == 200


def test_historico_da_criacao(logar, engine_app, predio, agendados):
    gravada = criar(logar, para_todos=False, blocos=[2], multipla_escolha=True)
    assert historico(engine_app, "enquete_criada") == [
        {
            "unidade_id": predio[COMISSAO],
            "entidade": "enquete",
            "entidade_id": gravada["id"],
            "detalhes": {
                "pergunta": PERGUNTA,
                "opcoes": 3,
                "multipla_escolha": True,
                "mostrar_resultado": "durante",
                "para_todos": False,
                "blocos": [2],
            },
        }
    ]
    # O aviso automático registra a publicação dele, como qualquer aviso.
    assert len(historico(engine_app, "aviso_publicado")) == 1


def test_o_admin_tambem_cria(logar, agendados):
    assert criar(logar, ADMIN)["id"] > 0


def test_bloco_inexistente_nao_grava_nada(logar, engine_app, agendados):
    resposta = logar(COMISSAO).post("/api/enquetes", json=corpo(para_todos=False, blocos=[9]))
    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "bloco_inexistente"
    assert _contar(engine_app, "enquete") == 0
    assert _contar(engine_app, "aviso") == 0
    assert agendados == []


# --- editar ------------------------------------------------------------------------------------


def editar(logar, enquete: int, login: str = COMISSAO, **troca: Any):
    return logar(login).put(f"/api/enquetes/{enquete}", json=edicao(**troca))


def test_editar_troca_tudo_e_corrige_o_aviso(logar, engine_app, predio, agendados):
    gravada = criar(logar)
    novo_termino = TERMINO + timedelta(days=2, hours=1)
    resposta = editar(
        logar,
        gravada["id"],
        ADMIN,
        pergunta="Qual dia é melhor para a vistoria?",
        opcoes=["Sábado", "Domingo"],
        multipla_escolha=True,
        encerra_em=novo_termino.isoformat(),
        mostrar_resultado="so_no_fim",
    )
    assert resposta.status_code == 200, resposta.text
    assert resposta.json() == gravada
    enquete = _linha(
        engine_app,
        "select pergunta, multipla_escolha, mostrar_resultado, encerra_em, editada_em"
        " from enquete where id = :e",
        e=gravada["id"],
    )
    assert enquete.pergunta == "Qual dia é melhor para a vistoria?"
    assert enquete.multipla_escolha is True
    assert enquete.mostrar_resultado == "so_no_fim"
    assert enquete.encerra_em == novo_termino
    assert enquete.editada_em is not None
    assert [(t, o) for _, t, o in _opcoes(engine_app, gravada["id"])] == [
        ("Sábado", 1),
        ("Domingo", 2),
    ]
    aviso = logar(COMUM).get(f"/api/avisos/{gravada['aviso_id']}").json()
    assert aviso["titulo"] == "Enquete nova: Qual dia é melhor para a vistoria?"
    assert aviso["texto"] == _texto_esperado(
        pergunta="Qual dia é melhor para a vistoria?",
        opcoes=["Sábado", "Domingo"],
        termino=novo_termino,
        escolha="Pode marcar mais de uma opção.",
        resultado="O resultado só aparece quando a enquete terminar.",
    )
    assert len(aviso["versoes_anteriores"]) == 1
    assert aviso["editado_em"] is not None
    # Correção não notifica de novo (só a criação agendou).
    assert agendados == [gravada["aviso_id"]]


def test_historico_da_edicao(logar, engine_app, predio, agendados):
    gravada = criar(logar, para_todos=False, blocos=[1, 2])
    editar(logar, gravada["id"], opcoes=["Sim", "Não"])
    assert historico(engine_app, "enquete_editada") == [
        {
            "unidade_id": predio[COMISSAO],
            "entidade": "enquete",
            "entidade_id": gravada["id"],
            "detalhes": {
                "pergunta": PERGUNTA,
                "opcoes": 2,
                "multipla_escolha": False,
                "mostrar_resultado": "durante",
                "para_todos": False,
                "blocos": [1, 2],
            },
        }
    ]
    assert len(historico(engine_app, "aviso_corrigido")) == 1


def test_opcoes_iguais_mantem_os_ids(logar, engine_app, agendados):
    """Mesma pergunta e mesmas opções: os ids ficam (a pergunta nova recria; ver a revisão)."""
    gravada = criar(logar)
    antes = _opcoes(engine_app, gravada["id"])
    resposta = editar(logar, gravada["id"], mostrar_resultado="so_no_fim")
    assert resposta.status_code == 200, resposta.text
    assert _opcoes(engine_app, gravada["id"]) == antes


def test_so_as_opcoes_mudam_e_a_enquete_fica_editada(logar, engine_app, agendados):
    gravada = criar(logar)
    resposta = editar(logar, gravada["id"], opcoes=[*OPCOES, "Domingo de manhã"])
    assert resposta.status_code == 200, resposta.text
    assert len(_opcoes(engine_app, gravada["id"])) == 4
    editada_em = _linha(
        engine_app, "select editada_em from enquete where id = :e", e=gravada["id"]
    ).editada_em
    assert editada_em is not None


def test_nada_mudou(logar, agendados):
    gravada = criar(logar)
    # O mesmo instante, escrito em outro fuso, e as opções com espaço sobrando: nada mudou.
    resposta = editar(
        logar,
        gravada["id"],
        encerra_em=TERMINO.astimezone(UTC).isoformat(),
        opcoes=[f" {o} " for o in OPCOES],
    )
    assert resposta.status_code == 409
    assert resposta.json() == {"codigo": "sem_mudanca", "mensagem": "Nada mudou na enquete."}


def test_segundos_no_termino_nao_corrigem_o_aviso(logar, engine_app, agendados):
    gravada = criar(logar)
    resposta = editar(
        logar, gravada["id"], encerra_em=(TERMINO + timedelta(seconds=30)).isoformat()
    )
    assert resposta.status_code == 200, resposta.text
    aviso = logar(COMUM).get(f"/api/avisos/{gravada['aviso_id']}").json()
    assert aviso["versoes_anteriores"] == []
    assert historico(engine_app, "aviso_corrigido") == []


def test_com_voto_nao_edita(logar, engine_app, predio, agendados):
    gravada = criar(logar)
    opcao = _opcoes(engine_app, gravada["id"])[0][0]
    with engine_app.begin() as con:
        votar(con, gravada["id"], predio[COMUM], opcao)
    resposta = editar(logar, gravada["id"], pergunta="Outra pergunta?")
    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "enquete_com_voto"
    assert (
        _linha(engine_app, "select pergunta from enquete where id = :e", e=gravada["id"]).pergunta
        == PERGUNTA
    )
    aviso = logar(COMUM).get(f"/api/avisos/{gravada['aviso_id']}").json()
    assert aviso["versoes_anteriores"] == []
    assert historico(engine_app, "enquete_editada") == []


def test_encerrada_nao_edita(logar, engine_app, engine_superusuario, agendados):
    gravada = criar(logar)
    with engine_superusuario.begin() as con:
        con.execute(text("set local session_replication_role = replica"))
        con.execute(
            text(
                "update enquete set encerra_em = now() - interval '1 minute',"
                " criada_em = now() - interval '2 days' where id = :e"
            ),
            {"e": gravada["id"]},
        )
    resposta = editar(logar, gravada["id"], pergunta="Outra pergunta?")
    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "enquete_encerrada"


def test_inexistente_e_404(logar):
    resposta = editar(logar, 999)
    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "enquete_nao_encontrada"


def test_aviso_arquivado_nao_impede_editar(logar, engine_app, agendados):
    gravada = criar(logar)
    comissao = logar(COMISSAO)
    assert comissao.post(f"/api/avisos/{gravada['aviso_id']}/arquivar").status_code == 200
    resposta = editar(logar, gravada["id"], pergunta="Outra pergunta?")
    assert resposta.status_code == 200, resposta.text
    assert (
        _linha(engine_app, "select pergunta from enquete where id = :e", e=gravada["id"]).pergunta
        == "Outra pergunta?"
    )
    assert comissao.get(f"/api/avisos/{gravada['aviso_id']}").json()["versoes_anteriores"] == []


def test_erro_no_meio_da_edicao_desfaz_tudo(logar, engine_app, agendados, monkeypatch):
    from app.servicos import enquetes_gestao

    gravada = criar(logar)
    antes = _opcoes(engine_app, gravada["id"])

    def falhar(*_args, **_kwargs):
        raise RuntimeError("falha de propósito")

    monkeypatch.setattr(enquetes_gestao.avisos, "gravar_correcao", falhar)
    resposta = editar(logar, gravada["id"], pergunta="Outra?", opcoes=["Sim", "Não"])
    assert resposta.status_code == 500
    assert _opcoes(engine_app, gravada["id"]) == antes
    assert _linha(
        engine_app, "select pergunta, editada_em from enquete where id = :e", e=gravada["id"]
    ) == (PERGUNTA, None)
