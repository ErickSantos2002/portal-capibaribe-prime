#!/usr/bin/env bash
# Confere a cópia dos arquivos contra um banco RESTAURADO (ADR-0011): roda na restauração de
# teste do dia 2, depois do restaurar.sh.
#
# Uso:
#   conferir-arquivos.sh --destino URL
#
#   --destino   o banco restaurado (o mesmo do restaurar.sh)
#
# Variáveis:
#   COPIA_S3_*   a cópia (_ENDPOINT, _ACCESS_KEY_ID, _SECRET_ACCESS_KEY e _BUCKET)
#   BACKUP_AGE_KEY_FILE ou BACKUP_AGE_KEY   a chave privada do age (como no restaurar.sh)
#   PG_BIN                                  pasta das ferramentas do Postgres 17
#
# Todo arquivo confirmado no banco precisa ter `arquivos/<chave>.age` na cópia, e um deles, ao
# acaso, precisa decifrar com o tamanho e a assinatura do tipo registrado. Banco sem arquivo
# confirmado: passa com aviso. Só chave, tipo e tamanho saem do banco (nada de nome de arquivo).
# shellcheck source=scripts/backup/comum.sh
source "$(dirname "${BASH_SOURCE[0]}")/comum.sh"

destino=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --destino) destino="${2:-}"; shift 2 ;;
    -h | --help) sed -n '2,19p' "$0"; exit 0 ;;
    *) falhar "opção desconhecida: $1 (veja --help)" ;;
  esac
done
[[ -n "$destino" ]] || falhar "falta --destino (veja --help)"
conferir_versao_pg psql
command -v age >/dev/null || falhar "age não está instalado"

temp="$(mktemp -d)"
trap 'rm -rf "$temp"' EXIT
umask 077

pg psql --no-psqlrc --quiet --no-password -v ON_ERROR_STOP=1 --tuples-only --no-align \
  --field-separator=$'\t' --dbname="$destino" \
  -c "select chave, tipo, tamanho_bytes from arquivo where confirmado_em is not null order by chave" \
  >"$temp/confirmados.tsv" || falhar "não consegui ler a tabela arquivo do banco restaurado"

identidade=()
if [[ -n "${BACKUP_AGE_KEY_FILE:-}${BACKUP_AGE_KEY:-}" ]]; then
  identidade=(--identidade "$(chave_privada_em "$temp")")
fi
arquivos_py conferir --lista "$temp/confirmados.tsv" "${identidade[@]}"
