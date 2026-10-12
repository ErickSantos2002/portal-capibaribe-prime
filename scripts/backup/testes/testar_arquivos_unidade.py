# /// script
# requires-python = "==3.12.*"
# dependencies = []
# ///
"""Testes de unidade das funções puras de `scripts/backup/arquivos.py` (sem S3, sem banco).
Rodado pelo `testar-ciclo.sh`; sozinho: `uv run --frozen --script testar_arquivos_unidade.py`.
Sai com 1 no primeiro que falhar."""

import importlib.util
import sys
from pathlib import Path

caminho = Path(__file__).resolve().parents[1] / "arquivos.py"
spec = importlib.util.spec_from_file_location("arquivos", caminho)
arquivos = importlib.util.module_from_spec(spec)
spec.loader.exec_module(arquivos)

HEX = "0123456789abcdef" * 2
testes = []


def teste(f):
    testes.append(f)
    return f


@teste
def padrao_das_chaves():
    assert arquivos.chave_publicada(f"arquivos/{HEX}") == HEX
    assert arquivos.chave_da_copia(f"arquivos/{HEX}.age") == HEX
    # `$` do `re` aceita um \n no fim; a chave seguinte já seria outro objeto.
    for ruim in (
        f"arquivos/{HEX}\n",
        f"arquivos/{HEX}.age",
        f"arquivos/{HEX.upper()}",
        f"arquivos/{HEX}0",
        f"envios/{HEX}",
        f"x/arquivos/{HEX}",
    ):
        assert arquivos.chave_publicada(ruim) is None, repr(ruim)
    for ruim in (f"arquivos/{HEX}.age\n", f"arquivos/{HEX}", f"arquivos/{HEX}.age.age"):
        assert arquivos.chave_da_copia(ruim) is None, repr(ruim)


falhas = 0
for f in testes:
    try:
        f()
        print(f"ok     {f.__name__}")
    except Exception as erro:  # noqa: BLE001 (o teste mostra qualquer erro)
        falhas += 1
        print(f"FALHOU {f.__name__}: {erro}")
sys.exit(1 if falhas else 0)
