# /// script
# requires-python = "==3.12.*"
# dependencies = ["boto3==1.43.108"]
# ///
"""Ajudante SÓ do teste local (`testar-ciclo.sh`): mexe num S3 falso (`moto`) por fora dos
scripts de backup, para preparar e conferir o cenário. Nunca aponte para um bucket de verdade.

Uso: uv run --frozen --script s3_teste.py ENDPOINT BUCKET <comando>
  criar                     cria o bucket
  gravar ARQUIVO CHAVE [TIPO]
  ler CHAVE ARQUIVO
  apagar CHAVE              (o teste simula um objeto que sumiu da cópia)
  listar PREFIXO            uma linha por objeto: chave, tamanho, ETag e data
  tipo CHAVE                o Content-Type guardado
"""

import sys

import boto3

if not sys.argv[1].startswith("http://127.0.0.1:"):
    sys.exit("s3_teste.py só fala com um S3 falso em 127.0.0.1")
s3 = boto3.client(
    "s3",
    endpoint_url=sys.argv[1],
    region_name="us-east-1",
    aws_access_key_id="teste",
    aws_secret_access_key="teste",
)
bucket, comando, args = sys.argv[2], sys.argv[3], sys.argv[4:]

if comando == "criar":
    s3.create_bucket(Bucket=bucket)
elif comando == "gravar":
    extra = {"ContentType": args[2]} if len(args) > 2 else {}
    with open(args[0], "rb") as f:
        s3.put_object(Bucket=bucket, Key=args[1], Body=f.read(), **extra)
elif comando == "ler":
    s3.download_file(bucket, args[0], args[1])
elif comando == "apagar":
    s3.delete_object(Bucket=bucket, Key=args[0])
elif comando == "listar":
    for pagina in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=args[0]):
        for o in pagina.get("Contents", []):
            print(o["Key"], o["Size"], o["ETag"], o["LastModified"].isoformat())
elif comando == "tipo":
    print(s3.head_object(Bucket=bucket, Key=args[0])["ContentType"])
else:
    sys.exit(f"comando desconhecido: {comando}")
