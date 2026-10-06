#!/usr/bin/env bash
# Backup do banco: pg_dump (formato custom) → cifra com age → bucket → retenção.
#
# Variáveis:
#   BACKUP_DATABASE_URL   URL do papel `backup` (só leitura), conexão direta, sslmode=require
#   R2_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET
#   PG_BIN                pasta do pg_dump 17 (opcional se o do PATH já for 17)
#   BACKUP_DATA           AAAA-MM-DD (opcional; padrão: hoje em Recife; os testes simulam datas)
#   BACKUP_DESTINATARIOS  arquivo de chaves públicas do age (padrão: destinatarios.age, ao lado)
#   BACKUP_RETER_DIARIOS / BACKUP_RETER_MENSAIS   padrão 30 e 12 (ADR-0007)
#
# Envia `diarios/AAAA-MM-DD.dump.age`; no dia 1 envia também `mensais/AAAA-MM.dump.age`.
# A chave diária é impressa na saída padrão (o workflow a passa para a restauração).
source "$(dirname "${BASH_SOURCE[0]}")/comum.sh"

exigir_variaveis BACKUP_DATABASE_URL R2_ENDPOINT R2_ACCESS_KEY_ID R2_SECRET_ACCESS_KEY R2_BUCKET
conferir_versao_pg pg_dump pg_restore
command -v age >/dev/null || falhar "age não está instalado"

data="${BACKUP_DATA:-$(hoje_recife)}"
[[ "$data" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || falhar "BACKUP_DATA fora do formato AAAA-MM-DD"
destinatarios="${BACKUP_DESTINATARIOS:-$PASTA_BACKUP/destinatarios.age}"
[[ -s "$destinatarios" ]] || falhar "arquivo de chaves públicas vazio ou ausente: $destinatarios"

temp="$(mktemp -d)"
trap 'rm -rf "$temp"' EXIT
umask 077

log "pg_dump (formato custom)"
# --no-password: sem senha na URL, falha na hora em vez de esperar um prompt.
pg pg_dump --format=custom --no-password --dbname="$BACKUP_DATABASE_URL" >"$temp/portal.dump"

# Antes de cifrar: o arquivo abre e tem os dados da tabela principal. Um dump truncado ou vazio
# para aqui, e o backup bom de ontem continua sendo o mais recente.
# (Pela entrada padrão: assim as ferramentas também podem rodar dentro de um container.)
pg pg_restore --list <"$temp/portal.dump" >"$temp/indice.txt" ||
  falhar "o pg_restore não conseguiu ler o dump recém-gerado"
grep -q 'TABLE DATA public unidade ' "$temp/indice.txt" ||
  falhar "o dump não tem os dados da tabela unidade"
log "dump ok: $(wc -l <"$temp/indice.txt") entradas no índice, $(du -h "$temp/portal.dump" | cut -f1)"

age --encrypt --recipients-file "$destinatarios" --output "$temp/portal.dump.age" "$temp/portal.dump"
rm -f "$temp/portal.dump"

diario="diarios/$data.dump.age"
s3 enviar "$temp/portal.dump.age" "$diario"
if [[ "${data:8:2}" == "01" ]]; then
  s3 enviar "$temp/portal.dump.age" "mensais/${data:0:7}.dump.age"
fi

s3 reter --diarios "${BACKUP_RETER_DIARIOS:-30}" --mensais "${BACKUP_RETER_MENSAIS:-12}"

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  {
    echo "### Backup $data"
    echo "- objeto: \`$diario\` ($(du -h "$temp/portal.dump.age" | cut -f1), cifrado com age)"
    [[ "${data:8:2}" == "01" ]] && echo "- também guardado como mensal \`mensais/${data:0:7}.dump.age\`"
    echo "- retenção aplicada: ${BACKUP_RETER_DIARIOS:-30} diários + ${BACKUP_RETER_MENSAIS:-12} mensais"
  } >>"$GITHUB_STEP_SUMMARY"
fi

log "backup concluído: $diario"
echo "$diario"
