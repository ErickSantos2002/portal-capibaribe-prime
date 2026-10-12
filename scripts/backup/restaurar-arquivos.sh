#!/usr/bin/env bash
# Desastre: traz os arquivos do Portal de volta da cópia cifrada (ADR-0011) para um bucket NOVO.
# Não precisa do banco: os nomes vêm da própria cópia (`arquivos/<chave>.age` → `arquivos/<chave>`).
#
# Uso (da raiz do repositório):
#   scripts/backup/restaurar-arquivos.sh
#
# Variáveis:
#   COPIA_S3_*     a cópia no B2 (_ENDPOINT, _ACCESS_KEY_ID, _SECRET_ACCESS_KEY e _BUCKET);
#                  basta uma chave de leitura
#   DESTINO_S3_*   o bucket novo (_ENDPOINT, _ACCESS_KEY_ID, _SECRET_ACCESS_KEY e _BUCKET), com
#                  chave de leitura e escrita; nome sem "backup"
#   BACKUP_AGE_KEY_FILE ou BACKUP_AGE_KEY   a chave privada do age (a cópia offline do dono)
#
# Pula o que já está no destino (pode rodar de novo depois de uma queda) e nunca sobrescreve.
# Sai com erro se algum arquivo não voltou. Passo a passo completo: README, seção "Backup".
# shellcheck source=scripts/backup/comum.sh
source "$(dirname "${BASH_SOURCE[0]}")/comum.sh"

case "${1:-}" in
  -h | --help) sed -n '2,17p' "$0"; exit 0 ;;
  "") ;;
  *) falhar "opção desconhecida: $1 (veja --help)" ;;
esac
command -v age >/dev/null || falhar "age não está instalado"

temp="$(mktemp -d)"
trap 'rm -rf "$temp"' EXIT
umask 077

identidade="$(chave_privada_em "$temp")" || exit 1
arquivos_py restaurar --identidade "$identidade"
