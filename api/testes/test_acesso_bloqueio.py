"""H-03 · Bloqueio por tentativas, por (login, IP) (revisão do M1, C2 e U3).

Antes, 5 senhas erradas de qualquer pessoa trancavam a unidade inteira por 15 minutos: bastava
saber o bloco e o apartamento de alguém para deixá-lo do lado de fora (negação de serviço). Agora
o bloqueio é daquele IP naquele login; o dono, de outro lugar, entra. O firewall da Vercel (20
logins por IP a cada 10 minutos, ADR-0005) continua sendo a barreira contra tentativa em massa.

Na Vercel o IP vem de `x-real-ip` (a Vercel sobrescreve o cabeçalho; ver `app/seguranca/ip.py`).
Os testes ligam `VERCEL=1` e mandam o cabeçalho para simular aparelhos diferentes.
"""

from datetime import timedelta

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.modelos import EntradaTentativa, Historico
from app.seguranca.senhas import SENHA_INICIAL
from testes.conftest import ADMIN, CABECALHO_PORTAL, COMUM, NAO_ATIVADA

MSG_CREDENCIAIS = "Bloco, apartamento ou senha incorretos. Confira e tente de novo."
IP_ATACANTE = "203.0.113.7"
IP_DONO = "198.51.100.20"

pytestmark = pytest.mark.usefixtures("predio")


@pytest.fixture(autouse=True)
def na_vercel(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")


def entrar(cliente, login: str, senha: str, ip: str = IP_ATACANTE):
    return cliente.post(
        "/api/acesso/entrar",
        json={"login": login, "senha": senha},
        headers={**CABECALHO_PORTAL, "x-real-ip": ip},
    )


def errar(cliente, login: str, vezes: int, ip: str = IP_ATACANTE):
    return [entrar(cliente, login, "senha-errada", ip) for _ in range(vezes)]


def tentativas(engine_app) -> list[EntradaTentativa]:
    with Session(engine_app) as db:
        return list(db.scalars(select(EntradaTentativa)))


# --- C2: o bloqueio é do IP, não da unidade ----------------------------------------------------


def test_cinco_erros_bloqueiam_aquele_ip_e_o_dono_entra_de_outro(cliente):
    respostas = errar(cliente, ADMIN, 5)
    assert [r.status_code for r in respostas] == [401, 401, 401, 401, 423]
    # Do mesmo IP, nem a senha certa entra.
    assert entrar(cliente, ADMIN, f"senha-{ADMIN}").status_code == 423
    # O dono, de outro lugar, entra normalmente.
    assert entrar(cliente, ADMIN, f"senha-{ADMIN}", ip=IP_DONO).status_code == 200


def test_bloqueio_de_um_login_nao_atinge_outro_login_do_mesmo_ip(cliente):
    errar(cliente, ADMIN, 5)
    assert entrar(cliente, COMUM, f"senha-{COMUM}").status_code == 200


def test_erros_de_ips_diferentes_nao_somam(cliente):
    errar(cliente, ADMIN, 4)
    errar(cliente, ADMIN, 4, ip=IP_DONO)
    assert entrar(cliente, ADMIN, f"senha-{ADMIN}").status_code == 200


def test_erros_com_mais_de_15_minutos_deixam_de_contar(cliente, engine_dono):
    errar(cliente, ADMIN, 4)
    with engine_dono.begin() as con:
        con.execute(
            text(
                "update entrada_tentativa set falhas_em = array("
                "select f - interval '16 minutes' from unnest(falhas_em) f)"
            )
        )
    # As 4 de antes já não contam: esta é a primeira de novo.
    resposta = entrar(cliente, ADMIN, "senha-errada")
    assert resposta.status_code == 401
    assert resposta.json()["tentativas_restantes"] == 4


def test_senha_certa_zera_so_aquele_ip(cliente):
    errar(cliente, ADMIN, 4)
    errar(cliente, ADMIN, 4, ip=IP_DONO)
    assert entrar(cliente, ADMIN, f"senha-{ADMIN}").status_code == 200
    # O atacante recomeça do zero; o outro IP continua com 4 erros (a 5ª bloqueia).
    assert [r.status_code for r in errar(cliente, ADMIN, 4)] == [401] * 4
    assert errar(cliente, ADMIN, 1, ip=IP_DONO)[0].status_code == 423


def test_tentativa_durante_o_bloqueio_nao_estende_o_prazo(cliente, engine_app):
    errar(cliente, ADMIN, 5)
    [antes] = tentativas(engine_app)
    errar(cliente, ADMIN, 3)
    [depois] = tentativas(engine_app)
    assert depois.bloqueada_ate == antes.bloqueada_ate


def test_passados_os_15_minutos_volta_a_entrar(cliente, engine_dono):
    errar(cliente, ADMIN, 5)
    with engine_dono.begin() as con:
        con.execute(text("update entrada_tentativa set bloqueada_ate = now() - interval '1 s'"))
    assert entrar(cliente, ADMIN, f"senha-{ADMIN}").status_code == 200


def test_bloqueio_dura_15_minutos_pelo_relogio_do_banco(cliente, engine_app):
    errar(cliente, ADMIN, 5)
    with Session(engine_app) as db:
        agora = db.scalars(select(func.now())).one()
    [linha] = tentativas(engine_app)
    assert linha.bloqueada_ate is not None
    assert timedelta(minutes=14) < linha.bloqueada_ate - agora <= timedelta(minutes=15)


def test_bloqueio_fica_no_historico_como_acao_do_sistema(cliente, predio, engine_app):
    errar(cliente, ADMIN, 5)
    with Session(engine_app) as db:
        registro = db.scalars(select(Historico).where(Historico.acao == "unidade_bloqueada")).one()
    assert registro.unidade_id is None
    assert (registro.entidade, registro.entidade_id) == ("unidade", predio[ADMIN])
    # O IP não vai para o histórico.
    assert IP_ATACANTE not in str(registro.detalhes)


def test_bloqueio_vale_tambem_para_unidade_nao_ativada(cliente):
    errar(cliente, NAO_ATIVADA, 5)
    assert entrar(cliente, NAO_ATIVADA, SENHA_INICIAL).status_code == 423


def test_login_inexistente_conta_e_bloqueia_igual(cliente):
    """A resposta não pode revelar se o apartamento existe: as mesmas contas, o mesmo bloqueio."""
    existe = [(r.status_code, r.json()) for r in errar(cliente, COMUM, 5)]
    nao_existe = [(r.status_code, r.json()) for r in errar(cliente, "5799", 5)]
    sem_data = [
        [(s, {k: v for k, v in c.items() if k != "bloqueada_ate"}) for s, c in lista]
        for lista in (existe, nao_existe)
    ]
    assert sem_data[0] == sem_data[1]


# --- U3: quantas tentativas faltam, e até quando bloqueou --------------------------------------


def test_a_partir_do_terceiro_erro_diz_quantas_faltam(cliente):
    corpos = [r.json() for r in errar(cliente, COMUM, 4)]
    assert [c["tentativas_restantes"] for c in corpos] == [4, 3, 2, 1]
    assert corpos[0]["mensagem"] == MSG_CREDENCIAIS
    assert corpos[1]["mensagem"] == MSG_CREDENCIAIS
    assert corpos[2]["mensagem"] == (
        f"{MSG_CREDENCIAIS} Faltam 2 tentativas antes de a entrada ser bloqueada por 15 minutos."
    )
    assert corpos[3]["mensagem"] == (
        f"{MSG_CREDENCIAIS} Falta 1 tentativa antes de a entrada ser bloqueada por 15 minutos."
    )


def test_bloqueio_traz_o_horario_e_os_minutos(cliente):
    corpo = errar(cliente, COMUM, 5)[-1].json()
    assert corpo["codigo"] == "unidade_bloqueada"
    assert corpo["minutos_restantes"] == 15
    assert corpo["bloqueada_ate"]
    assert corpo["mensagem"] == (
        "Entrada bloqueada por 15 minutos depois de várias senhas erradas. Se não foi você, "
        "avise a administração do Portal no grupo do WhatsApp."
    )


def test_um_minuto_no_singular(cliente, engine_dono):
    errar(cliente, ADMIN, 5)
    with engine_dono.begin() as con:
        con.execute(
            text("update entrada_tentativa set bloqueada_ate = now() + interval '30 seconds'")
        )
    corpo = entrar(cliente, ADMIN, "x").json()
    assert corpo["minutos_restantes"] == 1
    assert corpo["mensagem"].startswith("Entrada bloqueada por 1 minuto depois")


# --- IP: só o hash, com expiração, e da fonte certa --------------------------------------------


def test_guarda_so_o_hash_do_ip_e_a_linha_expira(cliente, engine_app):
    errar(cliente, ADMIN, 2)
    [linha] = tentativas(engine_app)
    assert IP_ATACANTE not in linha.ip_hash
    assert len(linha.ip_hash) == 64
    assert linha.expira_em > max(linha.falhas_em)


def test_linhas_vencidas_somem_na_proxima_tentativa(cliente, engine_dono, engine_app):
    errar(cliente, ADMIN, 2)
    with engine_dono.begin() as con:
        con.execute(text("update entrada_tentativa set expira_em = now() - interval '1 s'"))
    errar(cliente, COMUM, 1, ip=IP_DONO)
    assert [t.login for t in tentativas(engine_app)] == [COMUM]


def test_fora_da_vercel_o_cabecalho_e_ignorado(cliente, monkeypatch):
    """Sem a Vercel na frente, `x-real-ip` é do cliente e não vale: conta o endereço da
    conexão. Trocar o cabeçalho não escapa do bloqueio."""
    monkeypatch.delenv("VERCEL")
    errar(cliente, ADMIN, 5, ip=IP_ATACANTE)
    assert entrar(cliente, ADMIN, f"senha-{ADMIN}", ip=IP_DONO).status_code == 423
