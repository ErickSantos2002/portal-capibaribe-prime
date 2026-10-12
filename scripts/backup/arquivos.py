# /// script
# requires-python = "==3.12.*"
# dependencies = ["boto3==1.43.108"]
# ///
"""Proteção dos arquivos (ADR-0011): cópia cifrada do bucket de arquivos num segundo provedor.
Uso: `uv run --frozen --script arquivos.py <comando>` (as dependências vêm de arquivos.py.lock).

Comandos:
  copiar --destinatarios ARQUIVO
      para cada `arquivos/<chave>` do bucket de arquivos que ainda não está na cópia: baixa,
      cifra com `age` para os destinatários e envia `arquivos/<chave>.age`. Nunca apaga nem
      sobrescreve nada. Sem as variáveis, só avisa (sai com 0).
  conferir --lista ARQUIVO [--identidade CHAVE_PRIVADA]
      a lista (uma linha por arquivo confirmado no banco restaurado: chave, tipo e tamanho,
      separados por tabulação) inteira tem cópia; um deles, ao acaso, decifra com o tamanho e
      a assinatura do tipo registrado. Lista vazia: passa com aviso.
  restaurar --identidade CHAVE_PRIVADA
      desastre: decifra a cópia inteira (`arquivos/<chave>.age`) para `arquivos/<chave>` no
      bucket DESTINO_S3_*, com o Content-Type pela assinatura. Pula o que já está no destino
      (dá para rodar de novo depois de uma queda); nunca sobrescreve.

Variáveis (só o NOME aparece em mensagens; nenhum valor é impresso). Cada grupo tem quatro:
<GRUPO>_ENDPOINT, <GRUPO>_ACCESS_KEY_ID, <GRUPO>_SECRET_ACCESS_KEY e <GRUPO>_BUCKET.
  ARQUIVOS_R2_*   o bucket de arquivos do Portal (chave só de leitura)
  COPIA_S3_*      a cópia (Backblaze B2; chave sem deleteFiles)
  DESTINO_S3_*    o bucket novo de um desastre (só `restaurar`)
  <GRUPO>_REGIAO  opcional; padrão: a região de `s3.<região>.backblazeb2.com`, senão "auto"

Saída: o andamento vai para stderr. No GitHub Actions (GITHUB_ACTIONS=true), avisos viram
`::warning::` e o resumo vai para $GITHUB_STEP_SUMMARY.
"""

import argparse
import contextlib
import os
import re
import secrets
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from urllib.parse import urlparse

ORIGEM = "ARQUIVOS_R2"
COPIA = "COPIA_S3"
DESTINO = "DESTINO_S3"
# A API só cria `arquivos/<32 hexadecimais>` (m3-contrato, seção 2.1).
CHAVE_ORIGEM = re.compile(r"^arquivos/([0-9a-f]{32})$")
CHAVE_COPIA = re.compile(r"^arquivos/([0-9a-f]{32})\.age$")
BLOCO = 1024 * 1024
# Bytes que bastam para reconhecer os quatro tipos (o WEBP precisa de 12).
BYTES_DA_ASSINATURA = 16


def tipo_pelo_conteudo(inicio: bytes) -> str | None:
    """Os mesmos bytes mágicos da conferência do envio (`api/app/servicos/arquivos.py`)."""
    if inicio.startswith(b"%PDF-"):
        return "application/pdf"
    if inicio.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if inicio.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(inicio) >= 12 and inicio[:4] == b"RIFF" and inicio[8:12] == b"WEBP":
        return "image/webp"
    return None


class Falha(Exception):
    """Falha de um arquivo; a mensagem nunca leva segredo."""


# --- Mensagens -------------------------------------------------------------------------------
def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def no_actions() -> bool:
    return os.environ.get("GITHUB_ACTIONS") == "true"


def avisar(msg: str) -> None:
    log(f"AVISO: {msg}")
    if no_actions():
        print(f"::warning::{msg}", flush=True)


def resumo(*linhas: str) -> None:
    arquivo = os.environ.get("GITHUB_STEP_SUMMARY")
    if arquivo:
        with open(arquivo, "a", encoding="utf-8") as f:
            f.write("\n".join(linhas) + "\n")


# --- Buckets ---------------------------------------------------------------------------------
NOMES = ("ENDPOINT", "ACCESS_KEY_ID", "SECRET_ACCESS_KEY", "BUCKET")


def faltando(grupo: str) -> list[str]:
    return [f"{grupo}_{n}" for n in NOMES if not os.environ.get(f"{grupo}_{n}")]


def regiao(grupo: str, endpoint: str) -> str:
    """A região da assinatura: a do endpoint do B2 (`s3.<região>.backblazeb2.com`), ou "auto"
    (a única que o R2 aceita). `<GRUPO>_REGIAO` manda em qualquer caso."""
    if os.environ.get(f"{grupo}_REGIAO"):
        return os.environ[f"{grupo}_REGIAO"]
    m = re.fullmatch(r"s3\.([a-z0-9-]+)\.backblazeb2\.com", urlparse(endpoint).hostname or "")
    return m.group(1) if m else "auto"


@dataclass(frozen=True)
class Bucket:
    s3: object
    nome: str

    def listar(self, prefixo: str) -> dict[str, int]:
        """Chave → tamanho, de todas as páginas."""
        chaves: dict[str, int] = {}
        for pagina in self.s3.get_paginator("list_objects_v2").paginate(
            Bucket=self.nome, Prefix=prefixo
        ):
            chaves |= {o["Key"]: o["Size"] for o in pagina.get("Contents", [])}
        return chaves

    def enviar(self, arquivo: str, chave: str, tipo: str | None = None) -> None:
        """Envia e confere o tamanho no destino."""
        extra = {"ContentType": tipo} if tipo else None
        self.s3.upload_file(arquivo, self.nome, chave, ExtraArgs=extra)
        tamanho = self.s3.head_object(Bucket=self.nome, Key=chave)["ContentLength"]
        if tamanho != os.path.getsize(arquivo):
            raise Falha(f"envio incompleto de {chave}: {tamanho} bytes no destino")


def abrir(grupo: str) -> Bucket:
    if falta := faltando(grupo):
        sys.exit(f"Faltam as variáveis: {', '.join(falta)}")
    import boto3
    from botocore.config import Config

    endpoint = os.environ[f"{grupo}_ENDPOINT"]
    config = Config(
        signature_version="s3v4",
        # O R2 (e o B2) não aceitam todos os checksums novos do boto3; só quando a operação exige.
        request_checksum_calculation="when_required",
        response_checksum_validation="when_required",
        retries={"max_attempts": 5, "mode": "standard"},
    )
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.environ[f"{grupo}_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ[f"{grupo}_SECRET_ACCESS_KEY"],
        region_name=regiao(grupo, endpoint),
        config=config,
    )
    return Bucket(s3, os.environ[f"{grupo}_BUCKET"])


def primeira_linha(texto: str) -> str:
    linhas = texto.strip().splitlines()
    return linhas[0] if linhas else "sem mensagem"


def descrever(erro: Exception) -> str:
    """Uma linha sobre o erro. As mensagens do boto3 e do age não trazem as chaves de acesso."""
    return f"{type(erro).__name__}: {primeira_linha(str(erro))}"


# --- copiar ----------------------------------------------------------------------------------
def copiar_um(
    origem: Bucket, copia: Bucket, chave: str, tamanho: int, destinatarios: str, temp: str
) -> None:
    """Baixa em fluxo direto para a entrada do `age` (o conteúdo em claro nunca toca o disco),
    grava só o cifrado no diretório temporário e o envia."""
    cifrado = os.path.join(temp, f"{chave}.age")
    log(f"baixando e cifrando {chave}")
    try:
        with open(cifrado, "wb") as saida:
            age = subprocess.Popen(
                ["age", "--encrypt", "--recipients-file", destinatarios],
                stdin=subprocess.PIPE,
                stdout=saida,
                stderr=subprocess.PIPE,
            )
            baixados = 0
            try:
                corpo = origem.s3.get_object(Bucket=origem.nome, Key=f"arquivos/{chave}")["Body"]
                for bloco in corpo.iter_chunks(BLOCO):
                    age.stdin.write(bloco)
                    baixados += len(bloco)
            except BrokenPipeError:
                pass  # o age parou; o código de saída abaixo diz por quê
            finally:
                with contextlib.suppress(BrokenPipeError):
                    age.stdin.close()
                erro_age = age.stderr.read().decode(errors="replace").strip()
                age.wait()
        if age.returncode != 0:
            raise Falha(f"o age não cifrou ({primeira_linha(erro_age)})")
        if baixados != tamanho:
            raise Falha(f"baixou {baixados} bytes, a listagem dizia {tamanho}")
        copia.enviar(cifrado, f"arquivos/{chave}.age")
    finally:
        if os.path.exists(cifrado):
            os.remove(cifrado)


def copiar(destinatarios: str) -> int:
    falta = faltando(ORIGEM) + faltando(COPIA)
    if falta:
        msg = (
            "cópia dos arquivos não configurada (faltam as variáveis "
            f"{', '.join(falta)}); os arquivos de hoje NÃO foram copiados. "
            "O backup do banco não é afetado."
        )
        avisar(msg)
        resumo("### Cópia dos arquivos", f"- :warning: {msg}")
        return 0

    origem, copia = abrir(ORIGEM), abrir(COPIA)
    na_origem = origem.listar("arquivos/")
    publicados = {m.group(1): t for k, t in na_origem.items() if (m := CHAVE_ORIGEM.match(k))}
    ignorados = len(na_origem) - len(publicados)
    ja_copiados = {m.group(1) for k in copia.listar("arquivos/") if (m := CHAVE_COPIA.match(k))}
    faltam = sorted(set(publicados) - ja_copiados)
    if ignorados:
        # Sem o nome: o log de repositório público é público, e um nome fora do padrão da API
        # pode ser qualquer coisa.
        avisar(f"{ignorados} objeto(s) em arquivos/ fora do padrão da API, não copiado(s)")

    falhas: list[str] = []
    copiados = 0
    with tempfile.TemporaryDirectory(prefix="copia-arquivos-") as temp:
        os.chmod(temp, 0o700)
        for chave in faltam:
            try:
                copiar_um(origem, copia, chave, publicados[chave], destinatarios, temp)
                copiados += 1
            except Exception as erro:  # um arquivo ruim não para os outros
                log(f"FALHOU {chave}: {descrever(erro)}")
                falhas.append(chave)

    linha = (
        f"copiados agora: {copiados} · já na cópia: {len(publicados) - len(faltam)} · "
        f"ignorados (fora do padrão): {ignorados}"
    )
    log(f"cópia dos arquivos: {linha}")
    resumo("### Cópia dos arquivos", f"- {linha}")
    if falhas:
        resumo(f"- :x: falharam: {', '.join(falhas)}")
        log(f"ERRO: {len(falhas)} arquivo(s) não copiado(s): {', '.join(falhas)}")
        return 1
    return 0


# --- conferir --------------------------------------------------------------------------------
def ler_lista(caminho: str) -> list[tuple[str, str, int]]:
    """`chave<TAB>tipo<TAB>tamanho` por linha (a saída do psql em conferir-arquivos.sh)."""
    arquivos = []
    with open(caminho, encoding="utf-8") as f:
        for numero, linha in enumerate(f, 1):
            if not linha.strip():
                continue
            partes = linha.rstrip("\n").split("\t")
            if len(partes) != 3 or not re.fullmatch(r"[0-9a-f]{32}", partes[0]):
                sys.exit(f"linha {numero} da lista fora do formato chave<TAB>tipo<TAB>tamanho")
            arquivos.append((partes[0], partes[1], int(partes[2])))
    return arquivos


def decifrar_inicio(copia: Bucket, chave: str, identidade: str, temp: str) -> tuple[bytes, int]:
    """Baixa a cópia cifrada e a decifra em fluxo: devolve o começo e o tamanho do conteúdo,
    sem gravar o claro em lugar nenhum."""
    cifrado = os.path.join(temp, f"{chave}.age")
    copia.s3.download_file(copia.nome, f"arquivos/{chave}.age", cifrado)
    age = subprocess.Popen(
        ["age", "--decrypt", "--identity", identidade, cifrado],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    inicio, tamanho = b"", 0
    while bloco := age.stdout.read(BLOCO):
        if len(inicio) < BYTES_DA_ASSINATURA:
            inicio = (inicio + bloco)[:BYTES_DA_ASSINATURA]
        tamanho += len(bloco)
    age.wait()
    os.remove(cifrado)
    if age.returncode != 0:
        raise Falha(
            f"não consegui decifrar a cópia de {chave} (chave privada errada ou cópia corrompida)"
        )
    return inicio, tamanho


def conferir(lista: str, identidade: str | None) -> int:
    arquivos = ler_lista(lista)
    if not arquivos:
        msg = "nenhum arquivo confirmado no banco restaurado: nada a conferir na cópia dos arquivos"
        avisar(msg)
        resumo("### Cópia dos arquivos", f"- :warning: {msg}")
        return 0
    if falta := faltando(COPIA):
        sys.exit(
            f"Há {len(arquivos)} arquivo(s) confirmado(s) no banco e faltam as variáveis da cópia "
            f"({', '.join(falta)}): não dá para provar que estão protegidos."
        )
    if not identidade:
        sys.exit("Falta a chave privada do age (BACKUP_AGE_KEY ou BACKUP_AGE_KEY_FILE).")

    copia = abrir(COPIA)
    na_copia = copia.listar("arquivos/")
    sem_copia = [c for c, _, _ in arquivos if f"arquivos/{c}.age" not in na_copia]
    # O age só acrescenta (cabeçalho e 16 bytes por bloco): menor ou igual é cópia truncada.
    truncadas = [
        c for c, _, t in arquivos if c not in sem_copia and na_copia[f"arquivos/{c}.age"] <= t
    ]
    if sem_copia:
        log(f"ERRO: sem cópia: {', '.join(sem_copia)}")
    if truncadas:
        log(f"ERRO: cópia menor que o arquivo: {', '.join(truncadas)}")
    if sem_copia or truncadas:
        resumo(
            "### Cópia dos arquivos",
            f"- :x: sem cópia ou truncados: {len(sem_copia) + len(truncadas)}",
        )
        sys.exit(
            f"A cópia dos arquivos está incompleta: {len(sem_copia)} sem cópia e "
            f"{len(truncadas)} truncado(s), de {len(arquivos)} confirmado(s)."
        )

    chave, tipo, tamanho = secrets.SystemRandom().choice(arquivos)
    log(f"conferindo ao acaso {chave}")
    with tempfile.TemporaryDirectory(prefix="conferir-arquivos-") as temp:
        os.chmod(temp, 0o700)
        try:
            inicio, decifrado = decifrar_inicio(copia, chave, identidade, temp)
        except Falha as erro:
            sys.exit(str(erro))
        except Exception as erro:
            sys.exit(f"Não consegui baixar a cópia de {chave}: {descrever(erro)}")
    achado = tipo_pelo_conteudo(inicio)
    if achado != tipo:
        sys.exit(
            f"A cópia de {chave} decifra, mas não tem a assinatura de {tipo} "
            f"(achei {achado or 'nenhum tipo conhecido'})."
        )
    if decifrado != tamanho:
        sys.exit(f"A cópia de {chave} decifra com {decifrado} bytes; o banco diz {tamanho}.")

    linha = (
        f"{len(arquivos)} arquivo(s) confirmado(s), todos com cópia; conferido ao acaso: "
        f"{chave} ({tipo}, {tamanho} bytes) decifra com a assinatura certa"
    )
    log(f"conferência ok: {linha}")
    resumo("### Cópia dos arquivos", f"- {linha}")
    return 0


# --- restaurar -------------------------------------------------------------------------------
def restaurar_um(copia: Bucket, destino: Bucket, chave: str, identidade: str, temp: str) -> bool:
    """Decifra uma cópia e a envia ao destino. O claro fica só no diretório temporário 700 e é
    apagado logo depois do envio. Devolve se o conteúdo tem uma assinatura conhecida."""
    cifrado = os.path.join(temp, f"{chave}.age")
    claro = os.path.join(temp, chave)
    try:
        copia.s3.download_file(copia.nome, f"arquivos/{chave}.age", cifrado)
        decifrado = subprocess.run(
            ["age", "--decrypt", "--identity", identidade, "--output", claro, cifrado],
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if decifrado.returncode != 0:
            raise Falha(
                f"não consegui decifrar a cópia de {chave} "
                "(chave privada errada ou cópia corrompida)"
            )
        with open(claro, "rb") as f:
            tipo = tipo_pelo_conteudo(f.read(BYTES_DA_ASSINATURA))
        destino.enviar(claro, f"arquivos/{chave}", tipo or "application/octet-stream")
        return tipo is not None
    finally:
        for caminho in (cifrado, claro):
            if os.path.exists(caminho):
                os.remove(caminho)


def restaurar(identidade: str) -> int:
    copia, destino = abrir(COPIA), abrir(DESTINO)
    if "backup" in destino.nome.lower():
        sys.exit(
            "O destino tem 'backup' no nome: os arquivos voltam para um bucket NOVO de arquivos, "
            "nunca para o de backups (a API também recusa esse nome)."
        )
    na_copia = copia.listar("arquivos/")
    chaves = sorted(m.group(1) for k in na_copia if (m := CHAVE_COPIA.match(k)))
    ignorados = len(na_copia) - len(chaves)
    no_destino = destino.listar("arquivos/")

    restaurados = ja = sem_assinatura = 0
    falhas: list[str] = []
    with tempfile.TemporaryDirectory(prefix="restaurar-arquivos-") as temp:
        os.chmod(temp, 0o700)
        for chave in chaves:
            # O PUT do S3 é atômico: um envio interrompido não deixa objeto pela metade.
            if f"arquivos/{chave}" in no_destino:
                ja += 1
                continue
            log(f"restaurando {chave}")
            try:
                if not restaurar_um(copia, destino, chave, identidade, temp):
                    sem_assinatura += 1
                restaurados += 1
            except Exception as erro:
                log(f"FALHOU {chave}: {descrever(erro)}")
                falhas.append(chave)

    linha = (
        f"restaurados agora: {restaurados} · já no destino: {ja} · "
        f"sem assinatura conhecida: {sem_assinatura} · ignorados (fora do padrão): {ignorados}"
    )
    log(f"restauração dos arquivos: {linha}")
    if sem_assinatura:
        avisar(
            f"{sem_assinatura} arquivo(s) sem assinatura de PDF/JPEG/PNG/WEBP, "
            "restaurado(s) como application/octet-stream"
        )
    if falhas:
        log(f"ERRO: {len(falhas)} arquivo(s) não restaurado(s): {', '.join(falhas)}")
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = p.add_subparsers(dest="comando", required=True)
    c = sub.add_parser("copiar")
    c.add_argument("--destinatarios", required=True)
    f = sub.add_parser("conferir")
    f.add_argument("--lista", required=True)
    f.add_argument("--identidade")
    r = sub.add_parser("restaurar")
    r.add_argument("--identidade", required=True)
    args = p.parse_args(argv)

    if args.comando == "copiar":
        return copiar(args.destinatarios)
    if args.comando == "conferir":
        return conferir(args.lista, args.identidade)
    if args.comando == "restaurar":
        return restaurar(args.identidade)
    return 2


if __name__ == "__main__":
    sys.exit(main())
