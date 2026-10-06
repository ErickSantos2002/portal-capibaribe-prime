"""Infra dos testes: um Postgres de verdade, com os mesmos papéis da produção.

Produção (ADR-0003) tem dois usuários de banco: `dono` (dono das tabelas, roda as migrações) e
`app` (o que a API usa, sem DELETE no que é oficial). Aqui os dois são criados num Postgres
local ou no service container do CI, e o banco de teste nasce pela migração, como em produção.

Variáveis:
- `PORTAL_TESTE_ADMIN_URL`: superusuário do Postgres de teste. Padrão: o container local
  `portal-pg-m0` na porta 55432.
- `PORTAL_TESTE_BANCO`: nome do banco descartável. Padrão: `portal_teste`. Cópias de trabalho
  rodando em paralelo (um agente por épico) usam nomes diferentes para não apagar o banco umas
  das outras.
"""

import os
from collections.abc import Callable, Iterator
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from psycopg import sql
from sqlalchemy import Engine, create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from testes.apoio import rodar_alembic

ADMIN_URL = os.environ.get(
    "PORTAL_TESTE_ADMIN_URL", "postgresql://postgres:teste@127.0.0.1:55432/postgres"
)
# Senhas só de teste, num banco descartável que escuta apenas em 127.0.0.1.
PAPEIS = {"dono": "dono-teste", "app": "app-teste"}
BANCO = os.environ.get("PORTAL_TESTE_BANCO", "portal_teste")
TABELAS = [
    "aviso_leitura",
    "entrada_tentativa",
    "aviso_bloco",
    "aviso_versao",
    "aviso",
    "erro",
    "historico",
    "sessao",
    "unidade_papel",
    "unidade",
    "bloco",
]


def url_para(usuario: str, banco: str) -> str:
    """URL do Postgres de teste para outro usuário e banco (mesmo host e porta)."""
    partes = urlsplit(ADMIN_URL)
    netloc = f"{usuario}:{PAPEIS[usuario]}@{partes.hostname}:{partes.port or 5432}"
    return urlunsplit(("postgresql", netloc, f"/{banco}", "", ""))


def garantir_papeis() -> None:
    """Cria `dono` e `app` se ainda não existirem (papéis valem para o servidor inteiro)."""
    with psycopg.connect(ADMIN_URL, autocommit=True) as con:
        for nome, senha in PAPEIS.items():
            existe = con.execute("select 1 from pg_roles where rolname = %s", [nome]).fetchone()
            if not existe:
                con.execute(
                    sql.SQL("create role {} login password {}").format(
                        sql.Identifier(nome), sql.Literal(senha)
                    )
                )


def recriar_banco(nome: str) -> None:
    """Banco vazio, de propriedade do `dono` (como o banco do Neon)."""
    with psycopg.connect(ADMIN_URL, autocommit=True) as con:
        con.execute(sql.SQL("drop database if exists {} with (force)").format(sql.Identifier(nome)))
        con.execute(sql.SQL("create database {} owner dono").format(sql.Identifier(nome)))


def apagar_banco(nome: str) -> None:
    with psycopg.connect(ADMIN_URL, autocommit=True) as con:
        con.execute(sql.SQL("drop database if exists {} with (force)").format(sql.Identifier(nome)))


@pytest.fixture(scope="session")
def url_dono() -> Iterator[str]:
    garantir_papeis()
    recriar_banco(BANCO)
    url = url_para("dono", BANCO)
    rodar_alembic(url, "upgrade", "head")
    yield url
    apagar_banco(BANCO)


@pytest.fixture(scope="session")
def url_app(url_dono: str) -> str:
    return url_para("app", BANCO)


def _engine(url: str) -> Engine:
    return create_engine(url.replace("postgresql://", "postgresql+psycopg://"), poolclass=NullPool)


@pytest.fixture(scope="session")
def engine_dono(url_dono: str) -> Engine:
    return _engine(url_dono)


@pytest.fixture(scope="session")
def engine_app(url_app: str) -> Engine:
    return _engine(url_app)


@pytest.fixture(scope="session")
def engine_superusuario(url_dono: str) -> Engine:
    """Superusuário no banco de teste: só para simular ataques que pulam as regras do app."""
    partes = urlsplit(ADMIN_URL)
    return _engine(urlunsplit((partes.scheme, partes.netloc, f"/{BANCO}", "", "")))


@pytest.fixture(autouse=True)
def hasher_rapido(monkeypatch: pytest.MonkeyPatch) -> PasswordHasher:
    """Argon2id com custo baixo em todo teste (o padrão leva ~50 ms por hash)."""
    from app.seguranca import senhas

    rapido = PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1)
    monkeypatch.setattr(senhas, "_hasher", rapido)
    return rapido


# Endereço https: o cookie de sessão é `Secure` e o cliente HTTP não o devolve por http://.
BASE_URL = "https://testserver"
# Toda alteração de dados exige este cabeçalho (CSRF, spec do M1, seção 3.3).
CABECALHO_PORTAL = {"X-Portal": "1"}


@pytest.fixture
def cliente(url_app: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """A API como em produção: conectada como `app`. Erro 500 vira resposta, não exceção.

    Sem cookie e sem o cabeçalho `X-Portal`: é o visitante que ainda não entrou.
    """
    from app import banco
    from app.main import app

    monkeypatch.setenv("DATABASE_URL", url_app)
    banco.obter_engine.cache_clear()
    yield TestClient(app, base_url=BASE_URL, raise_server_exceptions=False)
    banco.obter_engine.cache_clear()


# Unidades fictícias do prédio de teste (os mesmos personagens do protótipo).
ADMIN, COMISSAO, COMUM, NAO_ATIVADA = "1101", "2304", "1203", "4203"


@pytest.fixture
def predio(banco_limpo, engine_app, hasher_rapido) -> dict[str, int]:
    """O prédio inteiro (5 blocos, 320 unidades, senha `mudar123`), carregado como `app`, e:

    - 1101: administrador, ativada;
    - 2304: Comissão, ativada;
    - 1203: unidade comum, ativada;
    - 4203: ainda não ativada (primeiro acesso pendente).

    As ativadas têm a senha `senha-<login>` (ex.: `senha-1203`). Devolve `{login: id}`.
    """
    from app.modelos import Papel, Unidade, UnidadePapel
    from app.seguranca.senhas import gerar_hash
    from app.servicos.carga_inicial import carregar

    with Session(engine_app) as db:
        carregar(db, hasher=hasher_rapido)
        ids = dict(
            db.execute(
                select(Unidade.login, Unidade.id).where(
                    Unidade.login.in_([ADMIN, COMISSAO, COMUM, NAO_ATIVADA])
                )
            ).all()
        )
        for posicao, login in enumerate([ADMIN, COMISSAO, COMUM]):
            unidade = db.get_one(Unidade, ids[login])
            unidade.senha_hash = gerar_hash(f"senha-{login}")
            unidade.precisa_trocar_senha = False
            unidade.ativada_em = func.now()
            unidade.responsavel_nome = f"Responsável {login} (fictício)"
            unidade.celular = f"819000000{posicao:02d}"
        db.flush()
        # Papel só em unidade já ativada (banco): depois de ativar. O admin vem de fora da
        # carga, como em produção (`promover_admin`).
        db.add(UnidadePapel(unidade_id=ids[ADMIN], papel=Papel.admin))
        db.add(UnidadePapel(unidade_id=ids[COMISSAO], papel=Papel.comissao))
        db.commit()
    return ids


@pytest.fixture
def logar(cliente: TestClient, engine_app) -> Callable[[str], TestClient]:
    """`logar("1203")` devolve um cliente com sessão daquela unidade (sem passar pela rota de
    entrar, que é do épico A) e com `X-Portal: 1` em toda requisição."""
    from app.main import app
    from app.modelos import Unidade
    from app.seguranca.sessoes import NOME_COOKIE, criar_sessao

    def _logar(login: str) -> TestClient:
        with Session(engine_app) as db:
            unidade_id = db.scalars(select(Unidade.id).where(Unidade.login == login)).one()
            token = criar_sessao(db, unidade_id, "Mozilla/5.0 (Linux; Android 14) Chrome/130")
            db.commit()
        logado = TestClient(
            app, base_url=BASE_URL, raise_server_exceptions=False, headers=CABECALHO_PORTAL
        )
        logado.cookies.set(NOME_COOKIE, token)
        return logado

    return _logar


@pytest.fixture
def banco_limpo(url_dono: str) -> None:
    """Esvazia as tabelas (como `dono`) antes do teste. O `app` não poderia fazer isso."""
    with psycopg.connect(url_dono, autocommit=True) as con:
        tabelas = sql.SQL(", ").join(sql.Identifier(t) for t in TABELAS)
        con.execute(sql.SQL("truncate {} restart identity cascade").format(tabelas))
