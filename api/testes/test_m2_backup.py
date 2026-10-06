"""As verificações da restauração (`scripts/backup/verificacoes.sql`) cobrem toda tabela que as
migrações criam (revisão do contrato do M2, achado 6). Migração nova com tabela nova e o
arquivo esquecido: este teste falha.
"""

import re
from pathlib import Path

import psycopg

VERIFICACOES = Path(__file__).resolve().parents[2] / "scripts" / "backup" / "verificacoes.sql"


def _esperadas() -> set[str]:
    texto = VERIFICACOES.read_text(encoding="utf-8")
    bloco = re.search(r"esperadas constant text\[\] := array\[(.*?)\];", texto, re.S)
    assert bloco, "lista `esperadas` não encontrada em verificacoes.sql"
    return set(re.findall(r"'([a-z_]+)'", bloco.group(1)))


def test_verificacoes_do_backup_conhecem_todas_as_tabelas(url_dono):
    with psycopg.connect(url_dono) as con:
        tabelas = {
            t for (t,) in con.execute("select tablename from pg_tables where schemaname = 'public'")
        }
    assert _esperadas() == tabelas
