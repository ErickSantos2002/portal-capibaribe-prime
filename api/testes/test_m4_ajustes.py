"""M4 · ajustes das revisões finais (costura entre os épicos A e B, e telas). Cada teste aqui
falhava antes da correção. Itens na ordem do pedido de ajustes (`duvidas-m4.md`, seção
"Revisões finais")."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.servicos import enquetes_banco
from app.servicos.enquetes_gestao import quando_em_texto
from testes.apoio import restricao
from testes.conftest import COMISSAO, COMUM
from testes.test_enquetes_gestao import agendados, corpo, edicao  # noqa: F401
from testes.test_enquetes_voto_apoio import nova, vencer, votar_no_banco

pytestmark = pytest.mark.usefixtures("predio", "agendados")

RECIFE = timezone(timedelta(hours=-3))


def _criar(g, **troca) -> int:
    r = g.post("/api/enquetes", json=corpo(**troca))
    assert r.status_code == 201, r.text
    return r.json()["id"]


# --- 1. trocar o tipo de escolha recria as opções ---------------------------------------------


@pytest.mark.parametrize("antes", [True, False])
def test_trocar_o_tipo_de_escolha_recria_as_opcoes(logar, antes):
    """Múltipla virando única (ou o contrário) com a tela do morador aberta: o voto da tela velha
    recebe 409 `enquete_mudou` (a tela recarrega), não um 422 que a deixa presa."""
    g, m = logar(COMISSAO), logar(COMUM)
    e = _criar(g, multipla_escolha=antes)
    velhas = [o["id"] for o in m.get(f"/api/enquetes/{e}").json()["opcoes"]]
    r = g.put(f"/api/enquetes/{e}", json=edicao(multipla_escolha=not antes))
    assert r.status_code == 200, r.text
    novas = [o["id"] for o in m.get(f"/api/enquetes/{e}").json()["opcoes"]]
    assert set(novas).isdisjoint(velhas)
    r = m.put(f"/api/enquetes/{e}/voto", json={"opcoes": velhas[:2] if antes else velhas[:1]})
    assert (r.status_code, r.json()["codigo"]) == (409, "enquete_mudou")


def test_so_o_termino_mudando_mantem_as_opcoes(logar):
    g, m = logar(COMISSAO), logar(COMUM)
    e = _criar(g)
    velhas = [o["id"] for o in m.get(f"/api/enquetes/{e}").json()["opcoes"]]
    termino = datetime.fromisoformat(corpo()["encerra_em"]) + timedelta(days=1)
    r = g.put(f"/api/enquetes/{e}", json=edicao(encerra_em=termino.isoformat()))
    assert r.status_code == 200, r.text
    assert [o["id"] for o in m.get(f"/api/enquetes/{e}").json()["opcoes"]] == velhas


# --- 3. a frase da corrida serve aos dois casos ------------------------------------------------


def test_voto_mudou_agora_nao_culpa_outro_aparelho():
    for regra in ("voto_completo", "voto_pkey", "voto_opcao_pkey", "voto_opcao_do_voto"):
        status, codigo, frase = enquetes_banco.RESTRICOES[regra]
        assert (status, codigo) == (409, "voto_mudou_agora")
        assert "outro aparelho" not in frase
        assert frase == (
            "A enquete ou o voto do seu apartamento mudou agora há pouco. Confira e vote de novo."
        )


# --- 4. a 0009 tem regra e frase próprias -----------------------------------------------------


def test_0009_recusa_com_regra_propria(engine_app, engine_dono, predio):
    criada = nova(engine_app, predio)
    with engine_dono.begin() as con:
        con.execute(text("update unidade set ativa = false where login = :l"), {"l": COMUM})
    with pytest.raises(DBAPIError) as erro:
        votar_no_banco(engine_app, criada.id, predio[COMUM], criada.opcoes[0])
    assert restricao(erro.value) == "voto_de_unidade_inativa"
    traduzido = enquetes_banco.traduzir(erro.value)
    assert traduzido is not None
    assert traduzido.status == 403
    assert traduzido.codigo == "unidade_inativa"
    assert "bloco" not in traduzido.mensagem


# --- 11. o cartão do aviso diz se a enquete terminou --------------------------------------------


def test_o_aviso_diz_se_a_enquete_esta_aberta_ou_terminou(
    logar, engine_app, engine_superusuario, predio
):
    criada = nova(engine_app, predio)
    with engine_app.connect() as con:
        aviso_id = con.execute(
            text("select aviso_id from enquete where id = :e"), {"e": criada.id}
        ).scalar_one()
    m = logar(COMUM)
    aberta = m.get(f"/api/avisos/{aviso_id}").json()["enquete"]
    assert aberta["encerrada"] is False
    assert datetime.fromisoformat(aberta["encerra_em"]) > datetime.now(RECIFE)
    vencer(engine_superusuario, criada.id)
    assert m.get(f"/api/avisos/{aviso_id}").json()["enquete"]["encerrada"] is True


# --- 16. data por extenso no aviso automático --------------------------------------------------


@pytest.mark.parametrize(
    ("quando", "esperado"),
    [
        (datetime(2026, 10, 16, 20, 0, tzinfo=RECIFE), "16 de outubro, às 20h"),
        (datetime(2026, 3, 5, 19, 30, tzinfo=RECIFE), "5 de março, às 19h30"),
        (datetime(2026, 10, 16, 8, 5, tzinfo=RECIFE), "16 de outubro, às 8h05"),
        (datetime(2027, 1, 5, 12, 0, tzinfo=RECIFE), "5 de janeiro de 2027, às 12h"),
        # Em UTC, mas o texto é no horário de Recife.
        (datetime(2026, 10, 17, 2, 0, tzinfo=UTC), "16 de outubro, às 23h"),
    ],
)
def test_quando_em_texto(quando, esperado):
    agora = datetime(2026, 10, 14, 9, 0, tzinfo=RECIFE)
    assert quando_em_texto(quando, agora) == esperado


def test_o_aviso_automatico_diz_a_data_por_extenso(logar):
    g = logar(COMISSAO)
    termino = (datetime.now(RECIFE) + timedelta(days=3)).replace(
        hour=20, minute=0, second=0, microsecond=0
    )
    e = _criar(g, encerra_em=termino.isoformat())
    aviso_id = g.get(f"/api/enquetes/{e}").json()["aviso_id"]
    texto = g.get(f"/api/avisos/{aviso_id}").json()["texto"]
    assert f"Dá para votar até {quando_em_texto(termino)} (horário de Recife)." in texto
    assert "/" not in texto.split("Dá para votar até")[1].split("(")[0]
