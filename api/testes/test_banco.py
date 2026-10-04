import pytest
from sqlalchemy.pool import NullPool

from app import banco
from app.banco import url_sqlalchemy


@pytest.mark.parametrize(
    ("entrada", "saida"),
    [
        # Formato que o Neon entrega (pooler, sslmode=require).
        (
            "postgres://app:s3nh4@ep-x-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require",
            "postgresql+psycopg://app:s3nh4@ep-x-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require",
        ),
        (
            "postgresql://app:s@localhost:55432/portal?sslmode=require&channel_binding=require",
            "postgresql+psycopg://app:s@localhost:55432/portal?sslmode=require&channel_binding=require",
        ),
        ("postgresql+psycopg://app:s@h/db", "postgresql+psycopg://app:s@h/db"),
        ("  postgresql://app:s@h/db\n", "postgresql+psycopg://app:s@h/db"),
    ],
)
def test_url_sqlalchemy_usa_psycopg3(entrada, saida):
    assert url_sqlalchemy(entrada) == saida


@pytest.mark.parametrize("entrada", ["", "   ", "mysql://u:s@h/db", "sqlite:///x.db"])
def test_url_sqlalchemy_recusa_o_que_nao_e_postgres(entrada):
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        url_sqlalchemy(entrada)


def test_engine_sem_pool_e_sem_prepared_statements(monkeypatch, url_app):
    # Conexão de verdade: o que vale é o que o psycopg recebeu, não a configuração.
    monkeypatch.setenv("DATABASE_URL", url_app)
    banco.obter_engine.cache_clear()
    try:
        engine = banco.obter_engine()
        assert isinstance(engine.pool, NullPool)
        assert engine.dialect.driver == "psycopg"
        with engine.connect() as con:
            psycopg_con = con.connection.driver_connection
            assert psycopg_con is not None
            # None = nunca prepara (o pooler do Neon em modo transação não suporta bem).
            assert psycopg_con.prepare_threshold is None
            con.exec_driver_sql("select 1")
    finally:
        banco.obter_engine.cache_clear()


def test_engine_sem_database_url_explica_o_que_falta(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    banco.obter_engine.cache_clear()
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        banco.obter_engine()
