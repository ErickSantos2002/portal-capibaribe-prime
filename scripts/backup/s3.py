# /// script
# requires-python = "==3.12.*"
# dependencies = ["boto3==1.43.108"]
# ///
"""Conversa com o bucket de backups (R2, API compatível com S3). Uso: `uv run s3.py <comando>`.

Comandos:
  enviar ARQUIVO CHAVE      envia o arquivo (sobrescreve a chave, se já existir)
  baixar CHAVE ARQUIVO      baixa a chave para o arquivo
  mais-recente PREFIXO      imprime a chave mais nova de `diarios` ou `mensais`
  listar PREFIXO            lista as chaves de backup de `diarios` ou `mensais`, da mais velha
  reter --diarios N --mensais M [--simular]
                            apaga os backups além dos N diários e M mensais mais novos

Configuração por variável de ambiente: R2_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY,
R2_BUCKET (opcional: R2_REGIAO, padrão "auto"). Nada disso é impresso.

A ordem dos backups vem do NOME (`diarios/AAAA-MM-DD.dump.age`, `mensais/AAAA-MM.dump.age`),
não da data de modificação: reenviar um backup antigo não o torna "o mais novo". Chave fora
desse padrão nunca é apagada pela retenção.
"""

import argparse
import os
import re
import sys
from collections.abc import Iterable

PADROES = {
    "diarios": re.compile(r"^diarios/(\d{4}-\d{2}-\d{2})\.dump\.age$"),
    "mensais": re.compile(r"^mensais/(\d{4}-\d{2})\.dump\.age$"),
}


def backups_do_tipo(chaves: Iterable[str], tipo: str) -> list[str]:
    """Só as chaves no padrão do tipo, da mais velha para a mais nova (pelo nome)."""
    padrao = PADROES[tipo]
    return sorted(c for c in chaves if padrao.match(c))


def escolher_para_apagar(chaves: Iterable[str], diarios: int, mensais: int) -> list[str]:
    """Os backups que sobram além dos `diarios` e `mensais` mais novos. O resto fica."""
    if diarios < 1 or mensais < 1:
        raise ValueError("a retenção precisa guardar pelo menos 1 de cada tipo")
    chaves = list(chaves)
    apagar: list[str] = []
    for tipo, manter in (("diarios", diarios), ("mensais", mensais)):
        lista = backups_do_tipo(chaves, tipo)
        apagar += lista[: max(0, len(lista) - manter)]
    return apagar


def cliente():
    import boto3
    from botocore.config import Config

    faltando = [
        v
        for v in ("R2_ENDPOINT", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET")
        if not os.environ.get(v)
    ]
    if faltando:
        sys.exit(f"Faltam as variáveis: {', '.join(faltando)}")
    config = Config(
        signature_version="s3v4",
        # O R2 não aceita todos os checksums novos do boto3; só quando a operação exige.
        request_checksum_calculation="when_required",
        response_checksum_validation="when_required",
        retries={"max_attempts": 5, "mode": "standard"},
    )
    return boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name=os.environ.get("R2_REGIAO", "auto"),
        config=config,
    )


def todas_as_chaves(s3, bucket: str, prefixo: str) -> list[str]:
    chaves: list[str] = []
    for pagina in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefixo):
        chaves += [o["Key"] for o in pagina.get("Contents", [])]
    return chaves


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = p.add_subparsers(dest="comando", required=True)
    e = sub.add_parser("enviar")
    e.add_argument("arquivo")
    e.add_argument("chave")
    b = sub.add_parser("baixar")
    b.add_argument("chave")
    b.add_argument("arquivo")
    for nome in ("mais-recente", "listar"):
        sub.add_parser(nome).add_argument("tipo", choices=sorted(PADROES))
    r = sub.add_parser("reter")
    r.add_argument("--diarios", type=int, required=True)
    r.add_argument("--mensais", type=int, required=True)
    r.add_argument("--simular", action="store_true", help="só mostra o que seria apagado")
    args = p.parse_args(argv)

    s3 = cliente()
    bucket = os.environ["R2_BUCKET"]

    if args.comando == "enviar":
        s3.upload_file(args.arquivo, bucket, args.chave)
        tamanho = s3.head_object(Bucket=bucket, Key=args.chave)["ContentLength"]
        if tamanho != os.path.getsize(args.arquivo):
            sys.exit(f"Envio incompleto de {args.chave}: {tamanho} bytes no bucket.")
        print(f"enviado {args.chave} ({tamanho} bytes)", file=sys.stderr)
    elif args.comando == "baixar":
        s3.download_file(bucket, args.chave, args.arquivo)
    elif args.comando in ("mais-recente", "listar"):
        lista = backups_do_tipo(todas_as_chaves(s3, bucket, args.tipo + "/"), args.tipo)
        if not lista:
            sys.exit(f"Nenhum backup em {args.tipo}/.")
        print(lista[-1] if args.comando == "mais-recente" else "\n".join(lista))
    elif args.comando == "reter":
        chaves = todas_as_chaves(s3, bucket, "diarios/") + todas_as_chaves(s3, bucket, "mensais/")
        apagar = escolher_para_apagar(chaves, args.diarios, args.mensais)
        for chave in apagar:
            if not args.simular:
                s3.delete_object(Bucket=bucket, Key=chave)
            print(f"{'apagaria' if args.simular else 'apagado'} {chave}", file=sys.stderr)
        print(f"retenção: {len(apagar)} backup(s) fora da janela", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
