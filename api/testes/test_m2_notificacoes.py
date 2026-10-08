"""Peça comum do M2: notificar a publicação de um aviso (spec do M2, seção 5).

Os canais de verdade (push do épico A, e-mail do épico B) entram depois; aqui eles são falsos,
para provar a orquestração: caixa de saída na mesma transação, no máximo uma vez por aviso e
canal, falha de um canal não derruba o outro, faxina do que morreu, quem recebe (H-13) e a cota
do Gmail.
"""

import asyncio
import threading
from dataclasses import dataclass, field

import pytest
from fastapi import BackgroundTasks
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.modelos import Canal, Sessao, Unidade
from app.servicos import notificacoes, segundo_plano
from app.servicos.notificacoes import AvisoParaNotificar, Resultado
from testes.test_avisos_apoio import ADMIN, COMISSAO, COMUM, NAO_ATIVADA, ativar, publicar

pytestmark = pytest.mark.usefixtures("predio")

P256DH = "B" + "A" * 86
AUTH = "C" * 22


@dataclass
class CanalFalso:
    canal: Canal
    esta_ligado: bool = True
    falhar: bool = False
    chamadas: list[AvisoParaNotificar] = field(default_factory=list)

    def ligado(self) -> bool:
        return self.esta_ligado

    def enviar(self, db: Session, aviso: AvisoParaNotificar, resultado: Resultado) -> None:
        self.chamadas.append(aviso)
        resultado.destinos = 3
        if self.canal is Canal.email:
            # Como o épico B tem de fazer: reservar a cota antes de mandar (o banco exige).
            assert resultado.reservar(3) == 3
        resultado.entregues = 2
        if self.falhar:
            raise RuntimeError("SMTP caiu ao mandar para alguem@example.com")
        resultado.falhas = 1
        resultado.removidas = 1


@pytest.fixture
def canais(monkeypatch) -> dict[Canal, CanalFalso]:
    falsos = {c: CanalFalso(c) for c in Canal}
    monkeypatch.setattr(notificacoes, "enviadores", lambda: list(falsos.values()))
    return falsos


@pytest.fixture
def fabrica(engine_app) -> sessionmaker[Session]:
    return sessionmaker(engine_app, expire_on_commit=False)


def envios(engine, aviso_id: int) -> dict[str, dict]:
    with engine.connect() as con:
        linhas = con.execute(
            text(
                "select canal, situacao, destinos, entregues, falhas, removidas, pulados"
                " from notificacao_envio where aviso_id = :a"
            ),
            {"a": aviso_id},
        ).mappings()
        return {linha["canal"]: dict(linha) for linha in linhas}


def _sem_registro(engine_dono, aviso_id: int) -> None:
    """Apaga os envios do aviso (como um aviso do M1, publicado antes da 0005). Só o dono
    consegue: o `app` não apaga envio."""
    with engine_dono.begin() as con:
        con.execute(text("delete from notificacao_envio where aviso_id = :a"), {"a": aviso_id})


# --- publicação → caixa de saída → processar ---------------------------------------------------


def test_publicar_sem_canais_configurados_registra_desligado(logar, engine_app):
    # Sem variáveis de ambiente (os testes não têm): push e e-mail desligados, e publicar
    # funciona igual ao M1.
    aviso = publicar(logar(COMISSAO))
    assert {c: e["situacao"] for c, e in envios(engine_app, aviso["id"]).items()} == {
        "push": "desligado",
        "email": "desligado",
    }


def test_publicar_notifica_depois_da_resposta_e_grava_as_contagens(logar, engine_app, canais):
    aviso = publicar(logar(COMISSAO), para_todos=False, blocos=[1])
    registro = envios(engine_app, aviso["id"])
    assert registro["push"] == {
        "canal": "push",
        "situacao": "concluido",
        "destinos": 3,
        "entregues": 2,
        "falhas": 1,
        "removidas": 1,
        "pulados": 0,
    }
    assert registro["email"]["situacao"] == "concluido"
    enviado = canais[Canal.push].chamadas[0]
    assert enviado.aviso_id == aviso["id"]
    assert enviado.titulo == "Vistoria da obra"
    assert enviado.blocos == (1,)
    assert enviado.para_todos is False
    assert enviado.caminho == f"/avisos/{aviso['id']}"


def test_nao_manda_duas_vezes(logar, engine_app, canais, fabrica):
    aviso = publicar(logar(COMISSAO))
    notificacoes.processar(aviso["id"], fabrica)
    notificacoes.processar(aviso["id"], fabrica)
    assert len(canais[Canal.push].chamadas) == 1
    assert len(canais[Canal.email].chamadas) == 1


def test_canal_que_cai_fica_interrompido_e_o_outro_segue(logar, engine_app, canais, caplog):
    canais[Canal.push].falhar = True
    aviso = publicar(logar(COMISSAO))
    registro = envios(engine_app, aviso["id"])
    # O que já tinha contado fica gravado.
    assert (registro["push"]["situacao"], registro["push"]["entregues"]) == ("interrompido", 2)
    assert registro["email"]["situacao"] == "concluido"
    # O log não leva a mensagem do erro (pode ter o e-mail de alguém).
    assert "alguem@example.com" not in caplog.text


def test_canal_desligado_nao_e_chamado(logar, engine_app, canais):
    canais[Canal.email].esta_ligado = False
    aviso = publicar(logar(COMISSAO))
    assert envios(engine_app, aviso["id"])["email"]["situacao"] == "desligado"
    assert canais[Canal.email].chamadas == []


def test_aviso_arquivado_antes_de_notificar_nao_chama_ninguem(engine_app, canais, fabrica):
    aviso_id = _aviso_no_banco(engine_app, fabrica)
    with engine_app.begin() as con:
        con.execute(text("update aviso set arquivado_em = now() where id = :a"), {"a": aviso_id})
    notificacoes.processar(aviso_id, fabrica)
    assert {e["situacao"] for e in envios(engine_app, aviso_id).values()} == {"interrompido"}
    assert canais[Canal.push].chamadas == []


def _aviso_no_banco(engine, fabrica, *, para_todos: bool = True, blocos=(), por=COMISSAO) -> int:
    """Publica direto no banco com a caixa de saída, sem processar (função "morreu")."""
    with fabrica() as db:
        publicado_por = db.scalar(select(Unidade.id).where(Unidade.login == por))
        aviso_id = db.execute(
            text(
                "insert into aviso (publicado_por, publicado_como, para_todos)"
                " values (:u, 'comissao', :t) returning id"
            ),
            {"u": publicado_por, "t": para_todos},
        ).scalar_one()
        db.execute(
            text(
                "insert into aviso_versao (aviso_id, versao, titulo, texto, criada_por)"
                " values (:a, 1, 'Título', 'Texto', :u)"
            ),
            {"a": aviso_id, "u": publicado_por},
        )
        for numero in blocos:
            db.execute(
                text(
                    "insert into aviso_bloco (aviso_id, bloco_id)"
                    " select :a, id from bloco where numero = :n"
                ),
                {"a": aviso_id, "n": numero},
            )
        notificacoes.registrar_publicacao(db, aviso_id)
        db.commit()
    return aviso_id


def test_pendente_de_outro_aviso_sai_na_proxima_publicacao(engine_app, canais, fabrica):
    perdido = _aviso_no_banco(engine_app, fabrica)
    novo = _aviso_no_banco(engine_app, fabrica)
    notificacoes.processar(novo, fabrica)
    assert [a.aviso_id for a in canais[Canal.push].chamadas] == [novo, perdido]
    assert envios(engine_app, perdido)["push"]["situacao"] == "concluido"


def test_faxina_interrompe_o_que_morreu_e_o_que_venceu(engine_app, engine_superusuario, fabrica):
    morto = _aviso_no_banco(engine_app, fabrica)
    velho = _aviso_no_banco(engine_app, fabrica)
    with engine_app.begin() as con:
        con.execute(
            text("update notificacao_envio set situacao = 'enviando' where aviso_id = :a"),
            {"a": morto},
        )
    with engine_superusuario.begin() as con:
        con.execute(text("set local session_replication_role = replica"))
        con.execute(
            text(
                "update notificacao_envio set iniciado_em = now() - interval '11 minutes'"
                " where aviso_id = :a"
            ),
            {"a": morto},
        )
        con.execute(
            text(
                "update notificacao_envio set criado_em = now() - interval '25 hours'"
                " where aviso_id = :a"
            ),
            {"a": velho},
        )
    novo = _aviso_no_banco(engine_app, fabrica)
    notificacoes.processar(novo, fabrica)
    for aviso_id in (morto, velho):
        assert {e["situacao"] for e in envios(engine_app, aviso_id).values()} == {"interrompido"}


def test_registrar_duas_vezes_nao_duplica(engine_app, fabrica):
    aviso_id = _aviso_no_banco(engine_app, fabrica)
    with fabrica() as db:
        notificacoes.registrar_publicacao(db, aviso_id)
        db.commit()
    assert len(envios(engine_app, aviso_id)) == 2


# --- quem recebe (H-13) ------------------------------------------------------------------------


def _sessao_inscrita(engine, login: str, n: int) -> int:
    with Session(engine) as db:
        unidade_id = db.scalar(select(Unidade.id).where(Unidade.login == login))
        sessao = Sessao(unidade_id=unidade_id, token_hash=f"{n:064x}", aparelho="Android · Chrome")
        db.add(sessao)
        db.flush()
        db.execute(
            text(
                "insert into inscricao_push (sessao_id, endpoint, chave_p256dh, chave_auth)"
                " values (:s, :e, :p, :a)"
            ),
            {
                "s": sessao.id,
                "e": f"https://fcm.googleapis.com/fcm/send/{n}",
                "p": P256DH,
                "a": AUTH,
            },
        )
        db.commit()
        return sessao.id


def test_push_so_para_os_aparelhos_do_bloco_de_destino(engine_app, fabrica):
    casal = [_sessao_inscrita(engine_app, COMUM, 1), _sessao_inscrita(engine_app, COMUM, 2)]
    admin = _sessao_inscrita(engine_app, ADMIN, 3)
    _sessao_inscrita(engine_app, COMISSAO, 4)  # quem publica (Bloco 2)
    ativar(engine_app, "2101")
    _sessao_inscrita(engine_app, "2101", 5)  # Bloco 2
    aviso_id = _aviso_no_banco(engine_app, fabrica, para_todos=False, blocos=[1])
    with fabrica() as db:
        destinos = notificacoes.destinos_push(db, notificacoes.carregar_aviso(db, aviso_id))
    # Os dois celulares do casal recebem (H-05); o Bloco 2 não (H-13).
    assert [d.sessao_id for d in destinos] == sorted([*casal, admin])
    assert destinos[0].endpoint == "https://fcm.googleapis.com/fcm/send/1"
    assert (destinos[0].chave_p256dh, destinos[0].chave_auth) == (P256DH, AUTH)


def test_push_tambem_para_quem_publicou_em_todos_os_aparelhos(engine_app, fabrica):
    # Resposta do Erick ao item 4 de duvidas-m2.md: quem publica recebe também, e os outros
    # aparelhos da unidade dele (o cônjuge) também.
    publicou = [_sessao_inscrita(engine_app, ADMIN, 1), _sessao_inscrita(engine_app, ADMIN, 3)]
    comissao = _sessao_inscrita(engine_app, COMISSAO, 2)
    aviso_id = _aviso_no_banco(engine_app, fabrica, por=ADMIN)
    with fabrica() as db:
        destinos = notificacoes.destinos_push(db, notificacoes.carregar_aviso(db, aviso_id))
    assert [d.sessao_id for d in destinos] == sorted([*publicou, comissao])


def test_push_so_para_sessao_que_ainda_vale(engine_app, fabrica):
    valendo = _sessao_inscrita(engine_app, COMUM, 1)
    parada = _sessao_inscrita(engine_app, COMUM, 2)
    antiga = _sessao_inscrita(engine_app, ADMIN, 3)
    with engine_app.begin() as con:
        con.execute(
            text("update sessao set ultimo_uso_em = now() - interval '181 days' where id = :s"),
            {"s": parada},
        )
        # Senha trocada depois da sessão: a sessão não vale mais (spec do M1, 2.4).
        con.execute(text("update unidade set senha_hash = 'outra' where login = :l"), {"l": ADMIN})
    aviso_id = _aviso_no_banco(engine_app, fabrica)
    with fabrica() as db:
        destinos = notificacoes.destinos_push(db, notificacoes.carregar_aviso(db, aviso_id))
    assert [d.sessao_id for d in destinos] == [valendo]
    assert antiga not in [d.sessao_id for d in destinos]


def test_unidade_desativada_nao_recebe(engine_app, fabrica):
    _sessao_inscrita(engine_app, COMUM, 1)
    with engine_app.begin() as con:
        con.execute(text("update unidade set ativa = false where login = :l"), {"l": COMUM})
    aviso_id = _aviso_no_banco(engine_app, fabrica)
    with fabrica() as db:
        aviso = notificacoes.carregar_aviso(db, aviso_id)
        assert notificacoes.destinos_push(db, aviso) == []


def _email(engine, login: str, email: str) -> None:
    with engine.begin() as con:
        con.execute(
            text("update unidade set email = :e where login = :l"), {"e": email, "l": login}
        )


def test_email_so_para_unidades_do_destino_com_email(engine_app, fabrica):
    _email(engine_app, COMUM, "comum@example.com")
    _email(engine_app, COMISSAO, "comissao@example.com")
    _email(engine_app, NAO_ATIVADA, "nao-ativada@example.com")
    aviso_id = _aviso_no_banco(engine_app, fabrica, para_todos=False, blocos=[1, 4])
    with fabrica() as db:
        destinos = notificacoes.destinos_email(db, notificacoes.carregar_aviso(db, aviso_id))
    # 1101 (Bloco 1) não tem e-mail; 4203 ainda não entrou; 2304 é de outro bloco.
    assert [(d.login, d.email) for d in destinos] == [(COMUM, "comum@example.com")]


def test_email_tambem_para_quem_publicou(engine_app, fabrica):
    _email(engine_app, COMISSAO, "comissao@example.com")
    _email(engine_app, COMUM, "comum@example.com")
    aviso_id = _aviso_no_banco(engine_app, fabrica, por=COMISSAO)
    with fabrica() as db:
        destinos = notificacoes.destinos_email(db, notificacoes.carregar_aviso(db, aviso_id))
    assert sorted(d.login for d in destinos) == sorted([COMISSAO, COMUM])


# --- cota do Gmail ---------------------------------------------------------------------------


def test_cota_do_gmail_guarda_reserva_para_a_recuperacao(engine_app, fabrica):
    aviso_id = _aviso_no_banco(engine_app, fabrica)
    with fabrica() as db:
        assert notificacoes.emails_nas_ultimas_24h(db) == 0
        assert notificacoes.cota_email_avisos(db) == 400
        assert notificacoes.cota_email_recuperacao(db) == 450
    with engine_app.begin() as con:
        con.execute(
            text(
                "update notificacao_envio set situacao = 'enviando' where aviso_id = :a"
                " and canal = 'email'"
            ),
            {"a": aviso_id},
        )
        # A cota conta o que foi **reservado** (antes de mandar), não o que já saiu.
        con.execute(
            text(
                "update notificacao_envio set destinos = 400, reservados = 400, entregues = 10"
                " where aviso_id = :a and canal = 'email'"
            ),
            {"a": aviso_id},
        )
    _email(engine_app, COMUM, "comum@example.com")
    with engine_app.begin() as con:
        con.execute(
            text(
                "insert into token_recuperacao (unidade_id, token_hash)"
                " select id, repeat('a', 64) from unidade where login = :l"
            ),
            {"l": COMUM},
        )
    with fabrica() as db:
        assert notificacoes.emails_nas_ultimas_24h(db) == 401
        assert notificacoes.cota_email_avisos(db) == 0
        assert notificacoes.cota_email_recuperacao(db) == 49


# --- segundo plano --------------------------------------------------------------------------


def test_fora_da_vercel_usa_background_tasks(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    chamadas: list[int] = []
    tarefas = BackgroundTasks()
    segundo_plano.agendar(tarefas, chamadas.append, 7)
    assert chamadas == []
    asyncio.run(tarefas())
    assert chamadas == [7]


def test_na_vercel_usa_wait_until(monkeypatch):
    import vercel.functions

    monkeypatch.setenv("VERCEL", "1")
    pendentes = []
    monkeypatch.setattr(vercel.functions, "wait_until", pendentes.append)
    chamadas: list[int] = []
    tarefas = BackgroundTasks()
    segundo_plano.agendar(tarefas, chamadas.append, 7)
    assert tarefas.tasks == [] and chamadas == []
    asyncio.run(pendentes[0])
    assert chamadas == [7]


# --- rota de envios (medir a entrega) ---------------------------------------------------------


def test_gestao_ve_os_envios_do_aviso(logar, canais):
    comissao = logar(COMISSAO)
    aviso = publicar(comissao)
    resposta = comissao.get(f"/api/avisos/{aviso['id']}/envios")
    assert resposta.status_code == 200
    itens = resposta.json()["itens"]
    assert [i["canal"] for i in itens] == ["push", "email"]
    assert itens[0] | {"criado_em": None, "concluido_em": None} == {
        "canal": "push",
        "situacao": "concluido",
        "destinos": 3,
        "entregues": 2,
        "falhas": 1,
        "removidas": 1,
        "pulados": 0,
        "criado_em": None,
        "concluido_em": None,
    }
    assert itens[0]["concluido_em"]


def test_envios_so_para_a_gestao(logar):
    aviso = publicar(logar(COMISSAO))
    resposta = logar(COMUM).get(f"/api/avisos/{aviso['id']}/envios")
    assert (resposta.status_code, resposta.json()["codigo"]) == (403, "sem_permissao")


def test_envios_de_aviso_inexistente(logar):
    resposta = logar(COMISSAO).get("/api/avisos/999999/envios")
    assert (resposta.status_code, resposta.json()["codigo"]) == (404, "aviso_nao_encontrado")


def test_aviso_antigo_sem_registro_de_envio_lista_vazia(logar, engine_dono):
    aviso = publicar(logar(COMISSAO))
    _sem_registro(engine_dono, aviso["id"])
    resposta = logar(COMISSAO).get(f"/api/avisos/{aviso['id']}/envios")
    assert resposta.json() == {"itens": []}


def test_sessao_criada_agora_vale_para_push(engine_app):
    # Sanidade do apoio: a sessão criada no teste vale (criada_em >= senha_trocada_em).
    sessao = _sessao_inscrita(engine_app, COMUM, 1)
    with Session(engine_app) as db:
        criada, trocada = db.execute(
            select(Sessao.criada_em, Unidade.senha_trocada_em)
            .join(Unidade, Unidade.id == Sessao.unidade_id)
            .where(Sessao.id == sessao)
        ).one()
        assert criada >= trocada
        assert db.scalar(select(func.count()).select_from(Sessao)) >= 1


# --- revisão do contrato: cota reservada, progresso gravado, tempo e paralelo ----------------


def _envio_email_enviando(engine_app, fabrica) -> tuple[int, int]:
    aviso_id = _aviso_no_banco(engine_app, fabrica)
    with engine_app.begin() as con:
        envio_id = con.execute(
            text(
                "update notificacao_envio set situacao = 'enviando' where aviso_id = :a"
                " and canal = 'email' returning id"
            ),
            {"a": aviso_id},
        ).scalar_one()
    return aviso_id, envio_id


def test_reserva_da_cota_vale_na_hora_mesmo_se_a_funcao_morrer(engine_app, fabrica, canais):
    # Achado 2: as contagens só iam para o banco no fim; uma função morta não gastava cota, e o
    # aviso seguinte estourava o Gmail.
    visto: dict[str, int] = {}

    def enviar(db, aviso, resultado):
        resultado.destinos = 300
        assert resultado.reservar(300) == 300
        with fabrica() as outra:  # outra conexão, outra transação
            visto["usados"] = notificacoes.emails_nas_ultimas_24h(outra)
        raise SystemExit  # a função "morre": nada depois disto roda

    canais[Canal.email].enviar = enviar
    aviso_id = _aviso_no_banco(engine_app, fabrica)
    with pytest.raises(SystemExit):
        notificacoes.processar(aviso_id, fabrica)
    assert visto["usados"] == 300
    with fabrica() as db:
        assert notificacoes.emails_nas_ultimas_24h(db) == 300
        assert notificacoes.cota_email_avisos(db) == 100


def test_reserva_nao_passa_da_cota(engine_app, fabrica):
    _, envio_id = _envio_email_enviando(engine_app, fabrica)
    assert notificacoes.reservar_cota_email(fabrica, envio_id, 500) == 400
    assert notificacoes.reservar_cota_email(fabrica, envio_id, 10) == 0


def test_reservas_ao_mesmo_tempo_nao_passam_da_cota(engine_app, fabrica):
    envios_ids = [_envio_email_enviando(engine_app, fabrica)[1] for _ in range(6)]
    barreira = threading.Barrier(len(envios_ids))
    concedidos: list[int] = []

    def reservar(envio_id: int) -> None:
        barreira.wait()
        concedidos.append(notificacoes.reservar_cota_email(fabrica, envio_id, 100))

    fios = [threading.Thread(target=reservar, args=(e,)) for e in envios_ids]
    for fio in fios:
        fio.start()
    for fio in fios:
        fio.join(10)
    assert sum(concedidos) == 400
    with fabrica() as db:
        assert notificacoes.emails_nas_ultimas_24h(db) == 400


def test_progresso_gravado_aos_poucos(engine_app, fabrica, canais):
    visto: dict[str, object] = {}

    def enviar(db, aviso, resultado):
        resultado.destinos = 10
        resultado.reservar(10)
        resultado.entregues = 4
        resultado.salvar()
        visto["meio"] = envios(engine_app, aviso.aviso_id)["email"]
        resultado.entregues = 10

    canais[Canal.email].enviar = enviar
    aviso_id = _aviso_no_banco(engine_app, fabrica)
    notificacoes.processar(aviso_id, fabrica)
    assert (visto["meio"]["situacao"], visto["meio"]["entregues"]) == ("enviando", 4)
    assert envios(engine_app, aviso_id)["email"]["entregues"] == 10


def test_sobra_da_reserva_volta_para_a_cota(engine_app, fabrica, canais):
    def enviar(db, aviso, resultado):
        resultado.destinos = 50
        resultado.reservar(50)
        resultado.entregues = 3
        resultado.pulados = 47  # o tempo acabou, por exemplo

    canais[Canal.email].enviar = enviar
    aviso_id = _aviso_no_banco(engine_app, fabrica)
    notificacoes.processar(aviso_id, fabrica)
    with fabrica() as db:
        assert notificacoes.emails_nas_ultimas_24h(db) == 3


def test_tempo_do_envio(monkeypatch):
    agora = [1000.0]
    monkeypatch.setattr(notificacoes.time, "monotonic", lambda: agora[0])
    resultado = Resultado(prazo=agora[0] + notificacoes.TEMPO_MAXIMO.total_seconds())
    assert not resultado.tempo_esgotado()
    agora[0] += notificacoes.TEMPO_MAXIMO.total_seconds() + 1
    assert resultado.tempo_esgotado()
    # O prazo cabe na função da Vercel (300 s), com folga para gravar o fim.
    assert notificacoes.TEMPO_MAXIMO.total_seconds() <= 240


def test_push_e_email_em_paralelo(engine_app, fabrica, canais):
    # O e-mail (lento) não atrasa o push, e o push não come o tempo do e-mail.
    email_comecou = threading.Event()
    push_viu: list[bool] = []
    enviar_email = canais[Canal.email].enviar

    def enviar_push(db, aviso, resultado):
        push_viu.append(email_comecou.wait(5))

    def enviar_email_marcando(db, aviso, resultado):
        email_comecou.set()
        enviar_email(db, aviso, resultado)

    canais[Canal.push].enviar = enviar_push
    canais[Canal.email].enviar = enviar_email_marcando
    notificacoes.processar(_aviso_no_banco(engine_app, fabrica), fabrica)
    assert push_viu == [True]


def test_log_do_canal_interrompido_traz_o_tipo_do_erro(logar, canais, caplog):
    # Achado 8: só o tipo, nunca a mensagem (pode ter o e-mail de alguém).
    canais[Canal.push].falhar = True
    publicar(logar(COMISSAO))
    assert "RuntimeError" in caplog.text
    assert "alguem@example.com" not in caplog.text


def test_reservar_email_de_recuperacao(engine_app, fabrica):
    with fabrica() as db:
        assert notificacoes.reservar_email_recuperacao(db) is True
        db.rollback()
    _, envio_id = _envio_email_enviando(engine_app, fabrica)
    notificacoes.reservar_cota_email(fabrica, envio_id, 400)
    with engine_app.begin() as con:
        con.execute(
            text("update notificacao_envio set reservados = 450 where id = :e"), {"e": envio_id}
        )
    with fabrica() as db:
        assert notificacoes.reservar_email_recuperacao(db) is False
