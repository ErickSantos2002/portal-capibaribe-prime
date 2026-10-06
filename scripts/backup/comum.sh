# Funções comuns dos scripts de backup. Carregado com `source`, nunca executado sozinho.
# Regra: nenhum script de backup liga `set -x` (as URLs de banco têm senha).
set -euo pipefail
set +x

PASTA_BACKUP="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Versão das ferramentas do Postgres: a mesma do Neon de produção (ADR-0003).
PG_VERSAO="${PG_VERSAO:-17}"

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*" >&2; }
falhar() { log "ERRO: $*"; exit 1; }

# Roda uma ferramenta do Postgres. PG_BIN aponta para a pasta da versão certa
# (no Actions: /usr/lib/postgresql/17/bin); sem ele, usa a do PATH.
pg() {
  local ferramenta="$1"
  shift
  if [[ -n "${PG_BIN:-}" ]]; then "$PG_BIN/$ferramenta" "$@"; else "$ferramenta" "$@"; fi
}

# pg_dump de uma versão gera arquivo que o pg_restore de versão mais velha não lê: as três
# ferramentas precisam ser da versão do servidor.
conferir_versao_pg() {
  local ferramenta versao
  for ferramenta in "$@"; do
    versao="$(pg "$ferramenta" --version | awk '{print $3}' | cut -d. -f1)"
    [[ "$versao" == "$PG_VERSAO" ]] ||
      falhar "$ferramenta é da versão $versao; precisa ser $PG_VERSAO (defina PG_BIN)"
  done
}

exigir_variaveis() {
  local v
  for v in "$@"; do
    [[ -n "${!v:-}" ]] || falhar "defina a variável $v"
  done
}

# Bucket de backups (s3.py, boto3 pela versão fixada no próprio arquivo).
s3() { uv run --quiet --script "$PASTA_BACKUP/s3.py" "$@"; }

# Data de hoje no fuso do condomínio (o agendamento das 06:00 UTC é 03:00 em Recife).
hoje_recife() { TZ=America/Recife date +%F; }
