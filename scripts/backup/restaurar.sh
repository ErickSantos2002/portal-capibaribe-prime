#!/usr/bin/env bash
# Restaura um backup num banco VAZIO e confere o resultado (ADR-0009).
#
# Uso:
#   restaurar.sh --destino URL [--objeto CHAVE | --arquivo ARQUIVO.dump.age] [--head REVISAO]
#
#   --destino   URL de um banco vazio (o script recusa banco que já tem tabela em public).
#               Os papéis do dump (dono, app) precisam existir no servidor de destino.
#   --objeto    chave no bucket (ex.: diarios/2026-10-05.dump.age). Padrão: o diário mais novo.
#   --arquivo   um .dump.age já baixado (dispensa as variáveis R2_*).
#   --head      revisão do Alembic esperada (`uv run --directory api alembic heads`). Sem ela,
#               a comparação com o repositório é pulada.
#
# Variáveis:
#   BACKUP_AGE_KEY_FILE   arquivo com a chave privada do age, ou
#   BACKUP_AGE_KEY        o conteúdo da chave (segredo do GitHub); vira arquivo temporário 600
#   R2_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET   (sem --arquivo)
#   PG_BIN                pasta das ferramentas do Postgres 17
#
# Sai com erro se a decifragem, o pg_restore ou qualquer verificação falhar.
# shellcheck source=scripts/backup/comum.sh
source "$(dirname "${BASH_SOURCE[0]}")/comum.sh"

destino="" objeto="" arquivo="" head=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --destino) destino="${2:-}"; shift 2 ;;
    --objeto) objeto="${2:-}"; shift 2 ;;
    --arquivo) arquivo="${2:-}"; shift 2 ;;
    --head) head="${2:-}"; shift 2 ;;
    -h | --help) sed -n '2,22p' "$0"; exit 0 ;;
    *) falhar "opção desconhecida: $1 (veja --help)" ;;
  esac
done
[[ -n "$destino" ]] || falhar "falta --destino (veja --help)"
[[ -z "$objeto" || -z "$arquivo" ]] || falhar "use --objeto ou --arquivo, não os dois"
conferir_versao_pg pg_restore psql
command -v age >/dev/null || falhar "age não está instalado"

temp="$(mktemp -d)"
trap 'rm -rf "$temp"' EXIT
umask 077

if [[ -n "${BACKUP_AGE_KEY_FILE:-}" ]]; then
  chave_privada="$BACKUP_AGE_KEY_FILE"
elif [[ -n "${BACKUP_AGE_KEY:-}" ]]; then
  chave_privada="$temp/chave.age"
  printf '%s\n' "$BACKUP_AGE_KEY" >"$chave_privada"
else
  falhar "defina BACKUP_AGE_KEY_FILE (caminho) ou BACKUP_AGE_KEY (conteúdo da chave privada)"
fi

# Destino precisa estar vazio: este script nunca escreve por cima de um banco em uso.
psql_destino() { pg psql --no-psqlrc --quiet --no-password -v ON_ERROR_STOP=1 --dbname="$destino" "$@"; }
tabelas="$(psql_destino -tAc "select count(*) from pg_tables where schemaname = 'public'")" ||
  falhar "não consegui conectar no banco de destino"
[[ "$tabelas" == "0" ]] ||
  falhar "o banco de destino não está vazio ($tabelas tabelas em public); use um banco novo"

if [[ -z "$arquivo" ]]; then
  exigir_variaveis R2_ENDPOINT R2_ACCESS_KEY_ID R2_SECRET_ACCESS_KEY R2_BUCKET
  objeto="${objeto:-$(s3 mais-recente diarios)}"
  log "baixando $objeto"
  arquivo="$temp/backup.dump.age"
  s3 baixar "$objeto" "$arquivo"
fi

log "decifrando"
age --decrypt --identity "$chave_privada" --output "$temp/portal.dump" "$arquivo" ||
  falhar "não consegui decifrar (chave privada errada ou arquivo corrompido)"

log "pg_restore (uma transação só: ou volta tudo, ou nada)"
pg pg_restore --no-password --exit-on-error --single-transaction --dbname="$destino" \
  <"$temp/portal.dump" || falhar "o pg_restore falhou"

# Permissão do próprio banco (não vai no dump): a migração 0001 tira de todo mundo a tabela
# temporária. Reaplicada aqui, igual à migração.
psql_destino <<'SQL'
do $$
begin
    execute format('revoke temporary on database %I from public', current_database());
end;
$$;
SQL

log "verificando"
psql_destino -v head="$head" <"$PASTA_BACKUP/verificacoes.sql" ||
  falhar "o banco restaurado NÃO passou nas verificações"
[[ -n "$head" ]] || log "aviso: sem --head, a migração do backup não foi comparada com o repositório"
log "restauração ok${objeto:+: $objeto}"
