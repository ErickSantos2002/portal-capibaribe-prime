#!/usr/bin/env bash
# Cópia diária cifrada dos arquivos do Portal (ADR-0011; hoje no plano B: a pasta `arquivos/` do
# bucket de backups). Roda no workflow
# `Backup` DEPOIS do pg_dump: um arquivo confirmado no banco do backup já está em `arquivos/`.
#
# Variáveis:
#   ARQUIVOS_R2_ENDPOINT, ARQUIVOS_R2_ACCESS_KEY_ID, ARQUIVOS_R2_SECRET_ACCESS_KEY,
#   ARQUIVOS_R2_BUCKET    bucket de arquivos, chave só de leitura
#   COPIA_S3_ENDPOINT, COPIA_S3_ACCESS_KEY_ID, COPIA_S3_SECRET_ACCESS_KEY,
#   COPIA_S3_BUCKET       a cópia: hoje os mesmos valores dos R2_* do backup do banco (a pasta
#                         arquivos/ do bucket de backups tem trava); num outro provedor, uma chave
#                         sem permissão de apagar
#   BACKUP_DESTINATARIOS  chaves públicas do age (padrão: destinatarios.age, ao lado)
#
# Sem as variáveis: avisa e sai com 0 (o backup do banco é mais importante que a cópia de hoje).
# Com elas: sai com erro se algum arquivo não foi copiado (o GitHub manda e-mail).
# shellcheck source=scripts/backup/comum.sh
source "$(dirname "${BASH_SOURCE[0]}")/comum.sh"

command -v age >/dev/null || falhar "age não está instalado"
destinatarios="${BACKUP_DESTINATARIOS:-$PASTA_BACKUP/destinatarios.age}"
[[ -s "$destinatarios" ]] || falhar "arquivo de chaves públicas vazio ou ausente: $destinatarios"
umask 077

arquivos_py copiar --destinatarios "$destinatarios"
