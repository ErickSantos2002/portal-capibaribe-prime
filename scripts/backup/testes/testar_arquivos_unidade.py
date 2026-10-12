# /// script
# requires-python = "==3.12.*"
# dependencies = []
# ///
"""Testes de unidade das funções puras de `scripts/backup/arquivos.py` (sem S3, sem banco).
Rodado pelo `testar-ciclo.sh`; sozinho: `uv run --frozen --script testar_arquivos_unidade.py`.
Sai com 1 se algum falhar."""

import importlib.util
import os
import subprocess
import sys
import tempfile
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


@teste
def tamanho_da_copia_contra_o_age_de_verdade():
    """A fórmula confere com o que o `age` instalado gera, para 1 e 2 destinatários e nos
    limites do bloco de 64 KiB (inclusive o arquivo vazio, que ainda tem um bloco)."""
    with tempfile.TemporaryDirectory() as temp:
        destinatarios = []
        for i in (1, 2):
            subprocess.run(["age-keygen", "-o", f"{temp}/k{i}"], check=True, capture_output=True)
            pub = subprocess.run(
                ["age-keygen", "-y", f"{temp}/k{i}"], check=True, capture_output=True, text=True
            ).stdout
            destinatarios.append(pub)
            Path(f"{temp}/r{i}").write_text("".join(destinatarios))
        for i in (1, 2):
            for t in (0, 1, 10, 65535, 65536, 65537, 131072, 200000):
                cifrado = subprocess.run(
                    ["age", "--encrypt", "--recipients-file", f"{temp}/r{i}"],
                    input=os.urandom(t),
                    check=True,
                    capture_output=True,
                ).stdout
                assert arquivos.tamanho_da_copia_confere(len(cifrado), t), (i, t, len(cifrado))
                for errado in (len(cifrado) - 1, len(cifrado) + 1, len(cifrado) - 16):
                    assert not arquivos.tamanho_da_copia_confere(errado, t), (i, t, errado)


@teste
def tamanho_da_copia_recusa_lixo():
    # Lixo de 300 bytes no lugar de um arquivo de 10 (o achado da revisão), e o maior.
    assert not arquivos.tamanho_da_copia_confere(300, 10)
    assert not arquivos.tamanho_da_copia_confere(5000, 1016)
    assert not arquivos.tamanho_da_copia_confere(10, 10)
    assert not arquivos.tamanho_da_copia_confere(0, 0)


@teste
def mesmo_bucket_com_endpoint_escrito_diferente():
    b2 = "https://s3.us-east-005.backblazeb2.com"
    iguais = (
        b2,
        b2 + "/",
        "HTTPS://S3.us-east-005.BackBlazeB2.com",
        "https://s3.us-east-005.backblazeb2.com:443",
        "https://s3.us-east-005.backblazeb2.com:443//",
    )
    for outro in iguais:
        assert arquivos.mesmo_bucket(b2, "copia", outro, "copia"), outro
    assert not arquivos.mesmo_bucket(b2, "copia", b2, "outro")
    assert not arquivos.mesmo_bucket(b2, "copia", "https://conta.r2.cloudflarestorage.com", "copia")
    assert not arquivos.mesmo_bucket(
        b2, "copia", "https://s3.us-east-005.backblazeb2.com:8443", "copia"
    )
    assert arquivos.mesmo_bucket("http://127.0.0.1:9000", "b", "http://127.0.0.1:9000/", "b")
    assert arquivos.mesmo_bucket("http://localhost", "b", "http://localhost:80", "b")


falhas = 0
for f in testes:
    try:
        f()
        print(f"ok     {f.__name__}")
    except Exception as erro:  # noqa: BLE001 (o teste mostra qualquer erro)
        falhas += 1
        print(f"FALHOU {f.__name__}: {erro}")
sys.exit(1 if falhas else 0)
