#!/usr/bin/env bash
# Teste do ciclo inteiro do backup, sem tocar no R2 nem no Neon:
#   banco de teste (migração + carga) → papel backup → fazer-backup.sh → S3 falso (moto)
#   → retenção com datas simuladas → restaurar.sh → verificações; e os casos que TÊM de falhar.
#
# Uso (da raiz do repositório):
#   scripts/backup/testes/testar-ciclo.sh
#
# Variáveis:
#   PORTAL_TESTE_ADMIN_URL  superusuário do Postgres 17 de teste (padrão: container local
#                           portal-pg-m0, como os testes da API)
#   PG_BIN                  pasta das ferramentas do Postgres 17. Sem ela, e se as do PATH não
#                           forem 17, o teste usa as da imagem docker postgres:17.
set -euo pipefail
set +x

raiz="$(cd "$(dirname "$0")/../../.." && pwd)"
pasta="$raiz/scripts/backup"
source "$pasta/comum.sh"

ADMIN_URL="${PORTAL_TESTE_ADMIN_URL:-postgresql://postgres:teste@127.0.0.1:55432/postgres}"
[[ "$ADMIN_URL" =~ ^postgresql://([^:]+):([^@]+)@([^:/]+):([0-9]+)/ ]] ||
  falhar "PORTAL_TESTE_ADMIN_URL fora do formato postgresql://usuario:senha@host:porta/banco"
usuario_admin="${BASH_REMATCH[1]}" senha_admin="${BASH_REMATCH[2]}"
host="${BASH_REMATCH[3]}" porta="${BASH_REMATCH[4]}"
url() { echo "postgresql://$1:$2@$host:$porta/$3"; }

ORIGEM=portal_m1_backup
DESTINO=portal_m1_backup_restaurado
# Senhas só de teste, num Postgres que escuta apenas em 127.0.0.1 (as de dono e app são as
# mesmas dos testes da API, api/testes/conftest.py).
URL_DONO="$(url dono dono-teste "$ORIGEM")"
URL_APP="$(url app app-teste "$ORIGEM")"
URL_BACKUP="$(url backup backup-teste "$ORIGEM")"
URL_DESTINO_ADMIN="$(url "$usuario_admin" "$senha_admin" "$DESTINO")"
URL_ORIGEM_ADMIN="$(url "$usuario_admin" "$senha_admin" "$ORIGEM")"

temp="$(mktemp -d)"
moto_pid=""
encerrar() {
  [[ -n "$moto_pid" ]] && kill "$moto_pid" 2>/dev/null
  rm -rf "$temp"
}
trap encerrar EXIT

# --- Ferramentas do Postgres 17 -------------------------------------------------------------
versao_path="$( (pg_dump --version 2>/dev/null || true) | awk '{print $3}' | cut -d. -f1)"
if [[ -z "${PG_BIN:-}" && "$versao_path" != "$PG_VERSAO" ]]; then
  log "pg_dump do PATH é '${versao_path:-nenhum}'; usando as ferramentas da imagem postgres:$PG_VERSAO"
  mkdir -p "$temp/pgbin"
  for f in pg_dump pg_restore psql; do
    printf '#!/bin/sh\nexec docker run --rm -i --network host postgres:%s %s "$@"\n' \
      "$PG_VERSAO" "$f" >"$temp/pgbin/$f"
    chmod +x "$temp/pgbin/$f"
  done
  export PG_BIN="$temp/pgbin"
fi
conferir_versao_pg pg_dump pg_restore psql

# --- Ajudantes de asserção ------------------------------------------------------------------
passou=0
ok() { passou=$((passou + 1)); log "PASSOU: $*"; }
reprovar() { log "REPROVADO: $*"; exit 1; }
admin() { pg psql --no-psqlrc --quiet -v ON_ERROR_STOP=1 --dbname="$ADMIN_URL" "$@"; }
# esperar_falha "descrição" "texto que a saída deve conter" comando...
esperar_falha() {
  local descricao="$1" texto="$2"
  shift 2
  if "$@" >"$temp/saida.txt" 2>&1; then
    cat "$temp/saida.txt" >&2
    reprovar "$descricao: deveria falhar e passou"
  fi
  grep -qF -- "$texto" "$temp/saida.txt" || {
    cat "$temp/saida.txt" >&2
    reprovar "$descricao: falhou, mas sem a mensagem esperada '$texto'"
  }
  ok "$descricao"
}
contar() { s3 listar "$1" | grep -c .; }

# --- 1. Banco de origem: migração + carga + dados fictícios, como em produção ---------------
log "preparando $ORIGEM"
admin <<SQL
do \$\$
begin
    if not exists (select 1 from pg_roles where rolname = 'dono') then
        create role dono login password 'dono-teste';
    end if;
    if not exists (select 1 from pg_roles where rolname = 'app') then
        create role app login password 'app-teste';
    end if;
end;
\$\$;
drop database if exists $ORIGEM with (force);
drop database if exists $DESTINO with (force);
create database $ORIGEM owner dono;
SQL
(
  cd "$raiz/api"
  DATABASE_URL_DONO="$URL_DONO" uv run --quiet --frozen alembic upgrade head
  DATABASE_URL="$URL_APP" uv run --quiet --frozen python -m app.comandos.carga_inicial
  DATABASE_URL="$URL_APP" PORTAL_AMBIENTE=local uv run --quiet --frozen \
    python -m app.comandos.dados_ficticios
) >&2
head="$(cd "$raiz/api" && uv run --quiet --frozen alembic heads | awk '{print $1}')"
[[ -n "$head" ]] || reprovar "não consegui ler o head do Alembic"
log "head do repositório: $head"

# --- 2. Papel backup pelo SQL do repositório; ele lê e não escreve --------------------------
# Em produção quem roda é o dono (neon_superuser); aqui, o superusuário do container.
admin --dbname="$URL_ORIGEM_ADMIN" \
  <"$pasta/criar-papel-backup.sql" >/dev/null
admin --dbname="$URL_ORIGEM_ADMIN" \
  <"$pasta/criar-papel-backup.sql" >/dev/null
ok "criar-papel-backup.sql roda duas vezes sem erro"
admin -c "alter role backup password 'backup-teste'"
psql_backup() { pg psql --no-psqlrc --quiet -v ON_ERROR_STOP=1 --dbname="$URL_BACKUP" "$@"; }
[[ "$(psql_backup -tAc 'select count(*) from unidade')" == 320 ]] ||
  reprovar "o papel backup não lê unidade"
ok "papel backup lê as tabelas"
esperar_falha "papel backup não escreve (transação só leitura)" "read-only transaction" \
  psql_backup -c "update bloco set nome = nome"
esperar_falha "papel backup não escreve (sem permissão)" "permission denied" \
  psql_backup -c "set default_transaction_read_only = off" -c "update bloco set nome = nome"

# --- 3. S3 falso (moto) e chave age só do teste ---------------------------------------------
porta_s3="$(uv run --quiet --no-project python -c \
  'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])')"
uv run --quiet --no-project --python 3.12 --with 'moto[server]==5.2.3' \
  moto_server -H 127.0.0.1 -p "$porta_s3" >"$temp/moto.log" 2>&1 &
moto_pid=$!
export R2_ENDPOINT="http://127.0.0.1:$porta_s3" R2_ACCESS_KEY_ID=teste \
  R2_SECRET_ACCESS_KEY=teste R2_BUCKET=portal-capibaribe-backups R2_REGIAO=us-east-1
for _ in $(seq 1 60); do
  curl -sf "$R2_ENDPOINT" >/dev/null 2>&1 && break
  sleep 0.5
done
uv run --quiet --script "$pasta/s3.py" listar diarios >/dev/null 2>&1 || true
uv run --quiet --no-project --python 3.12 --with boto3==1.43.108 python - <<'PY'
import os, boto3
boto3.client("s3", endpoint_url=os.environ["R2_ENDPOINT"], region_name="us-east-1",
             aws_access_key_id="teste", aws_secret_access_key="teste"
             ).create_bucket(Bucket=os.environ["R2_BUCKET"])
PY
age-keygen -o "$temp/chave-teste.age" 2>/dev/null
age-keygen -y "$temp/chave-teste.age" >"$temp/destinatario-teste.age"
age-keygen -o "$temp/chave-errada.age" 2>/dev/null

# A chave pública do repositório é válida (cifra), mesmo sem a privada aqui.
echo teste | age --encrypt --recipients-file "$pasta/destinatarios.age" >/dev/null
ok "destinatarios.age do repositório é uma chave pública válida"

# --- 4. Retenção: 34 diários e 13 mensais antigos + o backup de 01/10 = 35 e 14 ------------
echo "backup falso" >"$temp/falso"
for i in $(seq 1 34); do
  s3 enviar "$temp/falso" "diarios/$(date -d "2026-10-01 - $i day" +%F).dump.age" 2>/dev/null
done
for i in $(seq 1 13); do
  s3 enviar "$temp/falso" "mensais/$(date -d "2026-10-01 - $i month" +%Y-%m).dump.age" 2>/dev/null
done
# Fora do padrão: a retenção nunca apaga.
s3 enviar "$temp/falso" "diarios/leia-me.txt" 2>/dev/null
s3 enviar "$temp/falso" "outra-pasta/2020-01-01.dump.age" 2>/dev/null

export BACKUP_DATABASE_URL="$URL_BACKUP" BACKUP_DESTINATARIOS="$temp/destinatario-teste.age"
objeto="$(BACKUP_DATA=2026-10-01 "$pasta/fazer-backup.sh")"
[[ "$objeto" == "diarios/2026-10-01.dump.age" ]] || reprovar "chave inesperada: $objeto"
ok "fazer-backup.sh enviou $objeto"

[[ "$(contar diarios)" == 30 ]] || reprovar "esperava 30 diários, há $(contar diarios)"
[[ "$(contar mensais)" == 12 ]] || reprovar "esperava 12 mensais, há $(contar mensais)"
[[ "$(s3 listar diarios | head -1)" == "diarios/2026-09-02.dump.age" ]] ||
  reprovar "o diário mais velho que sobra deveria ser 2026-09-02"
[[ "$(s3 listar mensais | head -1)" == "mensais/2025-11.dump.age" ]] ||
  reprovar "o mensal mais velho que sobra deveria ser 2025-11"
s3 listar mensais | grep -qx "mensais/2026-10.dump.age" || reprovar "o dia 1 não virou mensal"
ok "retenção: 35 diários e 14 mensais viraram 30 e 12, os mais novos"
s3 baixar "diarios/leia-me.txt" "$temp/x" && s3 baixar "outra-pasta/2020-01-01.dump.age" "$temp/x" ||
  reprovar "a retenção apagou chave fora do padrão"
ok "retenção não toca em chave fora do padrão"

s3 baixar "$objeto" "$temp/baixado"
[[ "$(head -c 21 "$temp/baixado")" == "age-encryption.org/v1" ]] || reprovar "o objeto não está cifrado"
! grep -qa PGDMP "$temp/baixado" || reprovar "o objeto tem cabeçalho de dump em claro"
ok "o objeto no bucket está cifrado com age (sem PGDMP em claro)"

# Dia que não é 1: só diário.
BACKUP_DATA=2026-10-02 "$pasta/fazer-backup.sh" >/dev/null
s3 listar mensais | grep -q "2026-10-02" && reprovar "dia 2 não deveria virar mensal"
[[ "$(contar diarios)" == 30 ]] || reprovar "a retenção deveria manter 30 diários"
ok "dia 2 gera só o diário, e a retenção segue em 30"

# --- 5. Restauração do mais recente num banco vazio -----------------------------------------
novo_destino() {
  admin -c "drop database if exists $DESTINO with (force)" -c "create database $DESTINO"
}
novo_destino
BACKUP_AGE_KEY="$(cat "$temp/chave-teste.age")" \
  "$pasta/restaurar.sh" --destino "$URL_DESTINO_ADMIN" --head "$head" >"$temp/restauracao.txt" 2>&1 || {
  cat "$temp/restauracao.txt" >&2
  reprovar "a restauração do backup bom falhou"
}
grep -q "baixando diarios/2026-10-02.dump.age" "$temp/restauracao.txt" ||
  reprovar "a restauração não pegou o diário mais recente"
grep -q "verificações ok: 5 blocos, 320 unidades" "$temp/restauracao.txt" ||
  reprovar "a restauração não mostrou as verificações"
ok "restaurar.sh restaurou o mais recente e passou nas verificações"
[[ "$(pg psql --no-psqlrc -tAc 'select count(*) from unidade' \
  --dbname="$(url app app-teste "$DESTINO")")" == 320 ]] ||
  reprovar "o papel app não lê o banco restaurado"
ok "o papel app lê o banco restaurado (permissões vieram no dump)"

esperar_falha "restaurar em banco que não está vazio é recusado" "não está vazio" \
  env BACKUP_AGE_KEY_FILE="$temp/chave-teste.age" \
  "$pasta/restaurar.sh" --destino "$URL_DESTINO_ADMIN" --objeto "$objeto"

# Também pelo arquivo já baixado, sem bucket (o caminho do desastre à mão).
novo_destino
env -u R2_ENDPOINT -u R2_BUCKET BACKUP_AGE_KEY_FILE="$temp/chave-teste.age" \
  "$pasta/restaurar.sh" --destino "$URL_DESTINO_ADMIN" --arquivo "$temp/baixado" --head "$head" \
  >/dev/null 2>&1 || reprovar "restaurar com --arquivo falhou"
ok "restaurar.sh --arquivo funciona sem acesso ao bucket"

# --- 6. Os casos que têm de falhar ----------------------------------------------------------
novo_destino
esperar_falha "chave privada errada não decifra" "não consegui decifrar" \
  env BACKUP_AGE_KEY_FILE="$temp/chave-errada.age" \
  "$pasta/restaurar.sh" --destino "$URL_DESTINO_ADMIN" --objeto "$objeto"

novo_destino
esperar_falha "migração do backup diferente do repositório reprova" "o repositório na 9999" \
  env BACKUP_AGE_KEY_FILE="$temp/chave-teste.age" \
  "$pasta/restaurar.sh" --destino "$URL_DESTINO_ADMIN" --objeto "$objeto" --head 9999

# Um backup com 319 unidades: apaga uma unidade sem nenhuma referência na origem.
# Unidade nunca ativada e fora do histórico: nada aponta para ela, e as chaves estrangeiras
# continuam valendo (se algo apontasse, o DELETE falharia aqui, não na restauração).
admin --dbname="$URL_ORIGEM_ADMIN" -c "
  delete from unidade where id = (
    select u.id from unidade u
     where u.ativada_em is null
       and not exists (select 1 from historico h where h.unidade_id = u.id)
     order by u.id desc limit 1)" >/dev/null
[[ "$(admin --dbname="$URL_ORIGEM_ADMIN" -tAc 'select count(*) from unidade')" == 319 ]] ||
  reprovar "não consegui deixar a origem com 319 unidades"
BACKUP_DATA=2026-10-03 "$pasta/fazer-backup.sh" >/dev/null
novo_destino
esperar_falha "backup com 319 unidades reprova na restauração" "esperava 320 unidades, o banco restaurado tem 319" \
  env BACKUP_AGE_KEY_FILE="$temp/chave-teste.age" \
  "$pasta/restaurar.sh" --destino "$URL_DESTINO_ADMIN" --head "$head"

# Dump que não se lê não sobe (e não estraga o mais recente).
esperar_falha "fazer-backup.sh para se o pg_dump falha" "password authentication failed" \
  env BACKUP_DATA=2026-10-04 BACKUP_DATABASE_URL="$(url backup senha-errada "$ORIGEM")" \
  "$pasta/fazer-backup.sh"
s3 listar diarios | grep -q 2026-10-04 && reprovar "um backup que falhou foi enviado"
ok "backup que falhou não chega ao bucket"

# --- Limpeza ---------------------------------------------------------------------------------
admin -c "drop database if exists $DESTINO with (force)" -c "drop database if exists $ORIGEM with (force)"
log "TUDO PASSOU ($passou verificações)"
