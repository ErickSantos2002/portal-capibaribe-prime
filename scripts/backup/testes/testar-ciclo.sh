#!/usr/bin/env bash
# Teste do ciclo inteiro do backup, sem tocar no R2 nem no Neon:
#   banco de teste (migração + carga) → papel backup → fazer-backup.sh → S3 falso (moto)
#   → retenção com datas simuladas → restaurar.sh → verificações; e os casos que TÊM de falhar.
#   Também a proteção dos arquivos (ADR-0011): cópia cifrada do bucket de arquivos para um
#   segundo S3 falso (com versões, como o Backblaze B2 do plano A), conferência na restauração e
#   restauração dos arquivos para um bucket novo; e o plano B escolhido (a cópia na pasta
#   arquivos/ do bucket de backups, no mesmo S3 falso da Cloudflare, sem tocar nos dumps).
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
# shellcheck source=scripts/backup/comum.sh
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
moto_pid="" moto_b2_pid=""
encerrar() {
  [[ -n "$moto_pid" ]] && kill "$moto_pid" 2>/dev/null
  [[ -n "$moto_b2_pid" ]] && kill "$moto_b2_pid" 2>/dev/null
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

# --- 0. Funções puras do arquivos.py (padrões, tamanhos, endpoints) ------------------------
uv run --quiet --frozen --script "$pasta/testes/testar_arquivos_unidade.py" >&2 ||
  reprovar "testes de unidade do arquivos.py"
ok "testes de unidade do arquivos.py"

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

# --- 3. Dois S3 falsos (moto) e chave age só do teste ---------------------------------------
# Um faz o papel da Cloudflare (bucket de backups, bucket de arquivos e o bucket novo de um
# desastre); o outro, o do Backblaze B2 (a cópia dos arquivos).
porta_livre() {
  uv run --quiet --no-project python -c \
    'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])'
}
subir_moto() { # porta log
  uv run --quiet --no-project --python 3.12 --with 'moto[server]==5.2.3' \
    moto_server -H 127.0.0.1 -p "$1" >"$2" 2>&1 &
}
esperar_moto() {
  for _ in $(seq 1 60); do
    curl -sf "$1" >/dev/null 2>&1 && return 0
    sleep 0.5
  done
  reprovar "o S3 falso em $1 não subiu"
}
porta_s3="$(porta_livre)"
subir_moto "$porta_s3" "$temp/moto.log"
moto_pid=$!
porta_b2="$(porta_livre)"
subir_moto "$porta_b2" "$temp/moto-b2.log"
moto_b2_pid=$!
export R2_ENDPOINT="http://127.0.0.1:$porta_s3" R2_ACCESS_KEY_ID=teste \
  R2_SECRET_ACCESS_KEY=teste R2_BUCKET=portal-capibaribe-backups R2_REGIAO=us-east-1
B2_ENDPOINT="http://127.0.0.1:$porta_b2"
esperar_moto "$R2_ENDPOINT"
esperar_moto "$B2_ENDPOINT"
uv run --quiet --script "$pasta/s3.py" listar diarios >/dev/null 2>&1 || true
# Ajudante do teste: mexe nos S3 falsos por fora dos scripts (preparar e conferir).
s3t() { uv run --quiet --frozen --script "$pasta/testes/s3_teste.py" "$@"; }
s3t "$R2_ENDPOINT" "$R2_BUCKET" criar
BUCKET_ARQUIVOS=portal-capibaribe-arquivos BUCKET_COPIA=portal-capibaribe-copia-arquivos
s3t "$R2_ENDPOINT" "$BUCKET_ARQUIVOS" criar
s3t "$B2_ENDPOINT" "$BUCKET_COPIA" criar
# Como um bucket do B2 com "Keep all versions" (plano A da ADR-0011): reenviar ou esconder não
# perde a versão.
s3t "$B2_ENDPOINT" "$BUCKET_COPIA" versionar
arq() { s3t "$R2_ENDPOINT" "$BUCKET_ARQUIVOS" "$@"; }
b2() { s3t "$B2_ENDPOINT" "$BUCKET_COPIA" "$@"; }
# As variáveis do workflow para o bucket de arquivos (chave só de leitura) e para a cópia (B2).
VARS_ARQUIVOS=(ARQUIVOS_R2_ENDPOINT="$R2_ENDPOINT" ARQUIVOS_R2_ACCESS_KEY_ID=teste
  ARQUIVOS_R2_SECRET_ACCESS_KEY=teste ARQUIVOS_R2_BUCKET="$BUCKET_ARQUIVOS" ARQUIVOS_R2_REGIAO=us-east-1)
VARS_COPIA=(COPIA_S3_ENDPOINT="$B2_ENDPOINT" COPIA_S3_ACCESS_KEY_ID=teste
  COPIA_S3_SECRET_ACCESS_KEY=teste COPIA_S3_BUCKET="$BUCKET_COPIA" COPIA_S3_REGIAO=us-east-1)
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
for chave in "diarios/leia-me.txt" "outra-pasta/2020-01-01.dump.age"; do
  s3 baixar "$chave" "$temp/x" || reprovar "a retenção apagou $chave, fora do padrão"
done
ok "retenção não toca em chave fora do padrão"

s3 baixar "$objeto" "$temp/baixado"
[[ "$(head -c 21 "$temp/baixado")" == "age-encryption.org/v1" ]] || reprovar "o objeto não está cifrado"
! grep -qa PGDMP "$temp/baixado" || reprovar "o objeto tem cabeçalho de dump em claro"
ok "o objeto no bucket está cifrado com age (sem PGDMP em claro)"

# --- 4b. Cópia dos arquivos (ADR-0011): sem configuração, avisa e não falha ----------------
resumo="$temp/resumo.md"
: >"$resumo"
GITHUB_STEP_SUMMARY="$resumo" GITHUB_ACTIONS=true "$pasta/copiar-arquivos.sh" >"$temp/saida.txt" 2>&1 || {
  cat "$temp/saida.txt" >&2
  reprovar "sem configuração, a cópia dos arquivos não pode falhar o backup"
}
grep -q "::warning::.*cópia dos arquivos não configurada" "$temp/saida.txt" ||
  reprovar "sem configuração, a cópia deveria emitir um aviso do GitHub"
grep -q "COPIA_S3_BUCKET" "$temp/saida.txt" || reprovar "o aviso deveria citar as variáveis que faltam"
grep -q "cópia dos arquivos não configurada" "$resumo" || reprovar "o aviso deveria ir para o resumo do job"
ok "cópia dos arquivos sem configuração: avisa (log e resumo) e sai com 0"

# Configuração pela metade: o mesmo aviso, com os nomes, e nunca um valor.
env ARQUIVOS_R2_ENDPOINT="$R2_ENDPOINT" ARQUIVOS_R2_ACCESS_KEY_ID=id-que-nao-aparece \
  ARQUIVOS_R2_SECRET_ACCESS_KEY=segredo-que-nao-aparece ARQUIVOS_R2_BUCKET="$BUCKET_ARQUIVOS" \
  COPIA_S3_SECRET_ACCESS_KEY=outro-segredo-que-nao-aparece \
  "$pasta/copiar-arquivos.sh" >"$temp/saida.txt" 2>&1 || reprovar "configuração pela metade não pode falhar o backup"
grep -q "COPIA_S3_ENDPOINT" "$temp/saida.txt" || reprovar "o aviso deveria citar COPIA_S3_ENDPOINT"
grep -q "que-nao-aparece" "$temp/saida.txt" && reprovar "a saída mostrou o valor de uma variável"
ok "configuração pela metade: avisa com os nomes, sem mostrar valor"

# Bucket fora do ar ou inexistente: erro curto, sem traceback, sem endereço e sem nome de bucket.
sem_rastro() { # descrição texto-que-não-pode-aparecer comando...
  local descricao="$1" proibido="$2"
  shift 2
  if "$@" >"$temp/saida.txt" 2>&1; then
    reprovar "$descricao: deveria falhar e passou"
  fi
  if grep -qE "Traceback|$proibido" "$temp/saida.txt"; then
    cat "$temp/saida.txt" >&2
    reprovar "$descricao: a saída mostrou traceback ou '$proibido'"
  fi
  grep -q "ERRO" "$temp/saida.txt" || reprovar "$descricao: sem a linha de ERRO"
  ok "$descricao"
}
porta_fechada="$(porta_livre)"
sem_rastro "bucket de arquivos fora do ar: erro curto, sem o endereço" "127.0.0.1:$porta_fechada" \
  env "${VARS_ARQUIVOS[@]}" "${VARS_COPIA[@]}" ARQUIVOS_R2_ENDPOINT="http://127.0.0.1:$porta_fechada" \
  "$pasta/copiar-arquivos.sh"
sem_rastro "cópia com bucket inexistente: erro curto, sem o nome do bucket" "bucket-que-nao-existe" \
  env "${VARS_ARQUIVOS[@]}" "${VARS_COPIA[@]}" COPIA_S3_BUCKET=bucket-que-nao-existe \
  "$pasta/copiar-arquivos.sh"

# Os arquivos publicados: um de cada tipo (o PDF passa de 8 MB: envio em partes), mais o que
# a cópia tem de ignorar (o envio ainda não conferido e uma chave fora do padrão da API).
nova_chave() { head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n'; }
mkdir "$temp/originais"
TIPOS=(application/pdf image/jpeg image/png image/webp)
CHAVES=()
{ printf '%%PDF-1.7\n'; head -c 9000000 /dev/urandom; } >"$temp/originais/0"
{ printf '\xff\xd8\xff\xe0'; head -c 3000 /dev/urandom; } >"$temp/originais/1"
{ printf '\x89PNG\r\n\x1a\n'; head -c 2000 /dev/urandom; } >"$temp/originais/2"
{ printf 'RIFF\x10\x00\x00\x00WEBPVP8 '; head -c 1000 /dev/urandom; } >"$temp/originais/3"
for i in 0 1 2 3; do
  CHAVES+=("$(nova_chave)")
  arq gravar "$temp/originais/$i" "arquivos/${CHAVES[$i]}" "${TIPOS[$i]}"
done
arq gravar "$temp/originais/0" "envios/$(nova_chave)" application/pdf
arq gravar "$temp/originais/0" "arquivos/leia-me.txt" text/plain

# No banco: os quatro confirmados (como a API faz: insere pendente e confirma) e um pendente.
valores=""
for i in 0 1 2 3; do
  valores+="${valores:+,}('${CHAVES[$i]}', 'teste-$i', '${TIPOS[$i]}', 'documento', $(stat -c %s "$temp/originais/$i"), (select min(id) from unidade))"
done
admin --dbname="$URL_ORIGEM_ADMIN" >/dev/null <<SQL
insert into arquivo (chave, nome_original, tipo, finalidade, tamanho_bytes, enviado_por)
values $valores,
       ('$(nova_chave)', 'pendente', 'application/pdf', 'documento', 10, (select min(id) from unidade));
update arquivo set confirmado_em = now() where nome_original like 'teste-%';
SQL

# Dia que não é 1: só diário.
BACKUP_DATA=2026-10-02 "$pasta/fazer-backup.sh" >/dev/null
s3 listar mensais | grep -q "2026-10-02" && reprovar "dia 2 não deveria virar mensal"
[[ "$(contar diarios)" == 30 ]] || reprovar "a retenção deveria manter 30 diários"
ok "dia 2 gera só o diário, e a retenção segue em 30"

# --- 4c. Cópia dos arquivos configurada -------------------------------------------------------
copiar() { env "${VARS_ARQUIVOS[@]}" "${VARS_COPIA[@]}" "$pasta/copiar-arquivos.sh"; }
: >"$resumo"
GITHUB_STEP_SUMMARY="$resumo" copiar >"$temp/saida.txt" 2>&1 || {
  cat "$temp/saida.txt" >&2
  reprovar "a cópia dos arquivos falhou"
}
grep -q "copiados agora: 4 · já na cópia: 0 · ignorados (fora do padrão): 1" "$temp/saida.txt" || {
  cat "$temp/saida.txt" >&2
  reprovar "a cópia deveria contar 4 copiados, 0 já estavam e 1 ignorado"
}
grep -q "copiados agora: 4" "$resumo" || reprovar "a cópia deveria escrever no resumo do job"
b2 listar arquivos/ | awk '{print $1}' | sort >"$temp/na-copia.txt"
printf 'arquivos/%s.age\n' "${CHAVES[@]}" | sort >"$temp/esperado.txt"
diff -u "$temp/esperado.txt" "$temp/na-copia.txt" >&2 ||
  reprovar "a cópia deveria ter exatamente os 4 publicados (sem envios/ nem a chave fora do padrão)"
ok "cópia: os 4 publicados foram para arquivos/<chave>.age; envios/ e chave fora do padrão, não"
for i in 0 1 2 3; do
  b2 ler "arquivos/${CHAVES[$i]}.age" "$temp/copia.age"
  [[ "$(head -c 21 "$temp/copia.age")" == "age-encryption.org/v1" ]] || reprovar "a cópia $i não está cifrada"
  age --decrypt --identity "$temp/chave-teste.age" --output "$temp/decifrado" "$temp/copia.age"
  cmp -s "$temp/decifrado" "$temp/originais/$i" || reprovar "a cópia $i não decifra para o original"
done
rm -f "$temp/decifrado" "$temp/copia.age"
ok "cópia: cada objeto é age e decifra para os mesmos bytes do original"

b2 listar arquivos/ >"$temp/antes.txt"
copiar >"$temp/saida.txt" 2>&1 || reprovar "a segunda rodada da cópia falhou"
grep -q "copiados agora: 0 · já na cópia: 4" "$temp/saida.txt" ||
  reprovar "a segunda rodada não deveria copiar nada"
grep -q "baixando" "$temp/saida.txt" && reprovar "a segunda rodada baixou um arquivo já copiado"
b2 listar arquivos/ >"$temp/depois.txt"
cmp -s "$temp/antes.txt" "$temp/depois.txt" || reprovar "a segunda rodada mexeu na cópia"
ok "cópia é incremental: a segunda rodada não baixa nem reenvia nada"

if grep -nE 'delete_object|delete_objects|copy_object|DeleteObject|put_bucket' "$pasta/arquivos.py" >&2; then
  reprovar "arquivos.py não pode apagar, copiar por cima nem mexer na configuração de bucket"
fi
ok "arquivos.py não tem nenhuma chamada que apague ou sobrescreva"

# Um arquivo que não se cifra (destinatário inválido): falha, avisa a chave, e não envia nada.
CHAVE_NOVA="$(nova_chave)"
arq gravar "$temp/originais/2" "arquivos/$CHAVE_NOVA" image/png
echo "age1invalido" >"$temp/destinatario-invalido.age"
esperar_falha "arquivo que não se cifra faz a cópia falhar, com a chave" "$CHAVE_NOVA" \
  env BACKUP_DESTINATARIOS="$temp/destinatario-invalido.age" "${VARS_ARQUIVOS[@]}" "${VARS_COPIA[@]}" \
  "$pasta/copiar-arquivos.sh"
b2 listar arquivos/ | grep -q "$CHAVE_NOVA" && reprovar "um arquivo que falhou chegou à cópia"
copiar >"$temp/saida.txt" 2>&1 || reprovar "a cópia não se recuperou na rodada seguinte"
grep -q "copiados agora: 1 · já na cópia: 4" "$temp/saida.txt" || reprovar "a rodada seguinte deveria copiar o que faltou"
ok "falha num arquivo não suja a cópia, e a rodada seguinte completa"

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

# --- 5b. Conferência da cópia dos arquivos no banco restaurado ------------------------------
conferir() {
  env "${VARS_COPIA[@]}" BACKUP_AGE_KEY_FILE="${CHAVE_CONFERIR:-$temp/chave-teste.age}" \
    "$pasta/conferir-arquivos.sh" --destino "$URL_DESTINO_ADMIN"
}
: >"$resumo"
GITHUB_STEP_SUMMARY="$resumo" conferir >"$temp/saida.txt" 2>&1 || {
  cat "$temp/saida.txt" >&2
  reprovar "a conferência da cópia dos arquivos falhou com a cópia em dia"
}
grep -q "4 arquivo(s) confirmado(s), todos com cópia do tamanho certo; cabeçalho conferido em 4" "$temp/saida.txt" ||
  reprovar "a conferência deveria achar os 4 confirmados (e ignorar o pendente)"
grep -qE "decifrado ao acaso: [0-9a-f]{32}" "$temp/saida.txt" ||
  reprovar "a conferência deveria decifrar um arquivo ao acaso"
grep -q "todos com cópia" "$resumo" || reprovar "a conferência deveria escrever no resumo do job"
ok "conferência: os 4 confirmados têm cópia, e um ao acaso decifra com a assinatura certa"

# Troca da chave do age (README): BACKUP_AGE_KEY com a antiga e a nova, uma por linha.
cat "$temp/chave-errada.age" "$temp/chave-teste.age" >"$temp/duas-chaves.age"
CHAVE_CONFERIR="$temp/duas-chaves.age" conferir >"$temp/saida.txt" 2>&1 || {
  cat "$temp/saida.txt" >&2
  reprovar "a conferência deveria passar com as duas chaves privadas no mesmo arquivo"
}
ok "conferência com duas chaves privadas (troca de chave) passa"

# Um arquivo confirmado no banco que não está na cópia reprova (e diz qual).
CHAVE_SEM_COPIA="$(nova_chave)"
admin --dbname="$URL_DESTINO_ADMIN" >/dev/null <<SQL
insert into arquivo (chave, nome_original, tipo, finalidade, tamanho_bytes, enviado_por)
values ('$CHAVE_SEM_COPIA', 'sem-copia', 'application/pdf', 'documento', 10, (select min(id) from unidade));
update arquivo set confirmado_em = now() where chave = '$CHAVE_SEM_COPIA';
SQL
esperar_falha "arquivo confirmado sem cópia reprova a conferência" "$CHAVE_SEM_COPIA" conferir
# Arquivo publicado não se apaga (gatilho); aqui é um banco descartável de teste.
admin --dbname="$URL_DESTINO_ADMIN" >/dev/null <<SQL
set session_replication_role = replica;
delete from arquivo where chave = '$CHAVE_SEM_COPIA';
SQL

CHAVE_CONFERIR="$temp/chave-errada.age" esperar_falha "chave privada errada não decifra a cópia" \
  "não consegui decifrar" conferir
esperar_falha "arquivos confirmados sem as variáveis da cópia reprovam" "COPIA_S3_ENDPOINT" \
  env BACKUP_AGE_KEY_FILE="$temp/chave-teste.age" \
  "$pasta/conferir-arquivos.sh" --destino "$URL_DESTINO_ADMIN"

# Cópias estragadas que o sorteio quase nunca pegaria: toda cópia tem o tamanho exato do age
# e o cabeçalho conferidos. Usa a do WEBP (1016 bytes) e devolve a boa no fim de cada caso.
alvo="arquivos/${CHAVES[3]}.age"
b2 ler "$alvo" "$temp/boa.age"
estragar() { # descrição texto-esperado arquivo-estragado
  b2 gravar "$3" "$alvo"
  esperar_falha "$1" "$2" conferir
  b2 gravar "$temp/boa.age" "$alvo"
}
head -c 5000 /dev/urandom >"$temp/estragada"
estragar "cópia trocada por lixo maior que o original reprova" "${CHAVES[3]}" "$temp/estragada"
head -c "$(($(stat -c %s "$temp/boa.age") - 10))" "$temp/boa.age" >"$temp/estragada"
estragar "cópia truncada (ainda maior que o original) reprova" "${CHAVES[3]}" "$temp/estragada"
{ printf 'X%.0s' $(seq 1 21); tail -c +22 "$temp/boa.age"; } >"$temp/estragada"
estragar "cópia do tamanho certo com cabeçalho errado reprova" "cabeçalho" "$temp/estragada"
conferir >/dev/null 2>&1 || reprovar "a conferência deveria voltar a passar com a cópia boa"
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

# O backup de 01/10 é de antes do primeiro arquivo (a situação de hoje em produção).
: >"$resumo"
GITHUB_STEP_SUMMARY="$resumo" GITHUB_ACTIONS=true \
  "$pasta/conferir-arquivos.sh" --destino "$URL_DESTINO_ADMIN" >"$temp/saida.txt" 2>&1 || {
  cat "$temp/saida.txt" >&2
  reprovar "banco sem arquivo confirmado deveria passar a conferência"
}
grep -q "::warning::.*nenhum arquivo confirmado" "$temp/saida.txt" ||
  reprovar "banco sem arquivo confirmado deveria passar com aviso"
grep -q "nenhum arquivo confirmado" "$resumo" || reprovar "o aviso deveria ir para o resumo do job"
ok "conferência: banco sem arquivo confirmado passa com aviso (mesmo sem as variáveis)"

# Uma cópia que decifra, mas não é o que o banco diz (assinatura de PDF ausente), reprova.
CHAVE_LIXO="$(nova_chave)"
printf 'isto não é um PDF\n' | age --encrypt --recipients-file "$temp/destinatario-teste.age" \
  >"$temp/lixo.age"
b2 gravar "$temp/lixo.age" "arquivos/$CHAVE_LIXO.age"
admin --dbname="$URL_DESTINO_ADMIN" >/dev/null <<SQL
insert into arquivo (chave, nome_original, tipo, finalidade, tamanho_bytes, enviado_por)
values ('$CHAVE_LIXO', 'lixo', 'application/pdf', 'documento', 20, (select min(id) from unidade));
update arquivo set confirmado_em = now() where chave = '$CHAVE_LIXO';
SQL
esperar_falha "cópia sem a assinatura do tipo registrado reprova" "assinatura" conferir

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

# --- 7. Desastre: os arquivos voltam da cópia para um bucket novo ---------------------------
# Na cópia agora: os 4 publicados, o que falhou e foi copiado na rodada seguinte, e a cópia sem
# assinatura conhecida do teste da conferência.
BUCKET_NOVO=portal-capibaribe-arquivos-novo
s3t "$R2_ENDPOINT" "$BUCKET_NOVO" criar
s3t "$R2_ENDPOINT" "$BUCKET_NOVO-2" criar
novo() { s3t "$R2_ENDPOINT" "$BUCKET_NOVO" "$@"; }
restaurar_arquivos() { # bucket de destino
  env "${VARS_COPIA[@]}" DESTINO_S3_ENDPOINT="$R2_ENDPOINT" DESTINO_S3_ACCESS_KEY_ID=teste \
    DESTINO_S3_SECRET_ACCESS_KEY=teste DESTINO_S3_BUCKET="$1" DESTINO_S3_REGIAO=us-east-1 \
    BACKUP_AGE_KEY="$(cat "${CHAVE_RESTAURAR:-$temp/chave-teste.age}")" \
    "$pasta/restaurar-arquivos.sh"
}
# A versão mais nova de uma cópia estragada (não decifra) e outra cópia escondida (o "hide" do
# B2, que no S3 é um marcador de remoção): as duas voltam das versões anteriores.
head -c 3000 /dev/urandom >"$temp/estragada"
b2 gravar "$temp/estragada" "arquivos/${CHAVES[1]}.age"
b2 apagar "arquivos/${CHAVES[2]}.age"
b2 listar arquivos/ | grep -q "${CHAVES[2]}" && reprovar "a cópia escondida ainda aparece na listagem"
restaurar_arquivos "$BUCKET_NOVO" >"$temp/saida.txt" 2>&1 || {
  cat "$temp/saida.txt" >&2
  reprovar "a restauração dos arquivos falhou"
}
grep -q "de versão anterior: 1 · estavam escondidos: 1" "$temp/saida.txt" || {
  cat "$temp/saida.txt" >&2
  reprovar "a restauração deveria recuperar 1 de versão anterior e 1 escondido"
}
grep -q "restaurados agora: 6 · já no destino: 0 · sem assinatura conhecida: 1" "$temp/saida.txt" || {
  cat "$temp/saida.txt" >&2
  reprovar "a restauração dos arquivos deveria contar 6 restaurados, 1 sem assinatura conhecida"
}
novo listar arquivos/ | awk '{print $1}' | sort >"$temp/no-novo.txt"
printf 'arquivos/%s\n' "${CHAVES[@]}" "$CHAVE_NOVA" "$CHAVE_LIXO" | sort >"$temp/esperado.txt"
diff -u "$temp/esperado.txt" "$temp/no-novo.txt" >&2 ||
  reprovar "o bucket novo deveria ter arquivos/<chave> de cada cópia, sem .age"
for i in 0 1 2 3; do
  novo ler "arquivos/${CHAVES[$i]}" "$temp/restaurado"
  cmp -s "$temp/restaurado" "$temp/originais/$i" || reprovar "o arquivo $i não voltou igual ao original"
  [[ "$(novo tipo "arquivos/${CHAVES[$i]}")" == "${TIPOS[$i]}" ]] ||
    reprovar "o arquivo $i voltou sem o Content-Type ${TIPOS[$i]}"
done
[[ "$(novo tipo "arquivos/$CHAVE_LIXO")" == "application/octet-stream" ]] ||
  reprovar "conteúdo sem assinatura conhecida deveria voltar como application/octet-stream"
ok "restauração dos arquivos: bucket novo com os mesmos bytes e o tipo pela assinatura"

restaurar_arquivos "$BUCKET_NOVO" >"$temp/saida.txt" 2>&1 || reprovar "a segunda rodada da restauração falhou"
grep -q "restaurados agora: 0 · já no destino: 6" "$temp/saida.txt" ||
  reprovar "a segunda rodada não deveria refazer o que já está no destino"
ok "restauração dos arquivos pode rodar de novo: pula o que já está no destino"

CHAVE_RESTAURAR="$temp/chave-errada.age" esperar_falha "restauração com a chave errada falha" \
  "não consegui decifrar" restaurar_arquivos "$BUCKET_NOVO-2"
[[ -z "$(s3t "$R2_ENDPOINT" "$BUCKET_NOVO-2" listar arquivos/)" ]] ||
  reprovar "a restauração com a chave errada gravou alguma coisa"
esperar_falha "restauração dos arquivos recusa o bucket de backups" "backup" \
  restaurar_arquivos portal-capibaribe-backups

# O destino nunca é a própria cópia: gravaria os arquivos em claro no B2 (achado da revisão),
# nem com o endpoint escrito de outro jeito, nem um bucket que já tem cópias (.age).
b2 listar "" >"$temp/antes.txt"
esperar_falha "restauração dos arquivos recusa a própria cópia como destino" "a própria cópia" \
  env "${VARS_COPIA[@]}" DESTINO_S3_ENDPOINT="${B2_ENDPOINT/http:/HTTP:}/" DESTINO_S3_ACCESS_KEY_ID=teste \
  DESTINO_S3_SECRET_ACCESS_KEY=teste DESTINO_S3_BUCKET="$BUCKET_COPIA" DESTINO_S3_REGIAO=us-east-1 \
  BACKUP_AGE_KEY_FILE="$temp/chave-teste.age" "$pasta/restaurar-arquivos.sh"
b2 listar "" >"$temp/depois.txt"
cmp -s "$temp/antes.txt" "$temp/depois.txt" || reprovar "a restauração recusada mexeu na cópia"
s3t "$R2_ENDPOINT" "$BUCKET_NOVO-3" criar
s3t "$R2_ENDPOINT" "$BUCKET_NOVO-3" gravar "$temp/lixo.age" "arquivos/$CHAVE_LIXO.age"
esperar_falha "restauração dos arquivos recusa destino que já tem cópias .age" ".age" \
  restaurar_arquivos "$BUCKET_NOVO-3"
[[ "$(s3t "$R2_ENDPOINT" "$BUCKET_NOVO-3" listar arquivos/ | wc -l)" == 1 ]] ||
  reprovar "a restauração recusada gravou no destino"

# --- 8. Plano B da ADR-0011: a cópia na pasta arquivos/ do bucket de backups ----------------
# Escolha do Erick (12/10/2026): sem Backblaze, os COPIA_S3_* recebem os mesmos valores dos R2_*
# do backup do banco. Origem e cópia na mesma conta (mesmo endpoint, buckets diferentes), e a
# cópia no mesmo bucket dos dumps: nada pode se misturar com diarios/ e mensais/.
VARS_COPIA_BACKUPS=(COPIA_S3_ENDPOINT="$R2_ENDPOINT" COPIA_S3_ACCESS_KEY_ID=teste
  COPIA_S3_SECRET_ACCESS_KEY=teste COPIA_S3_BUCKET="$R2_BUCKET" COPIA_S3_REGIAO=us-east-1)
bkp() { s3t "$R2_ENDPOINT" "$R2_BUCKET" "$@"; }
{ bkp listar diarios/; bkp listar mensais/; bkp listar outra-pasta/; } >"$temp/dumps-antes.txt"
env "${VARS_ARQUIVOS[@]}" "${VARS_COPIA_BACKUPS[@]}" "$pasta/copiar-arquivos.sh" >"$temp/saida.txt" 2>&1 || {
  cat "$temp/saida.txt" >&2
  reprovar "a cópia no bucket de backups falhou"
}
grep -q "copiados agora: 5 · já na cópia: 0 · ignorados (fora do padrão): 1" "$temp/saida.txt" || {
  cat "$temp/saida.txt" >&2
  reprovar "a cópia no bucket de backups deveria contar 5 copiados e 1 ignorado"
}
bkp listar arquivos/ | awk '{print $1}' | sort >"$temp/na-copia.txt"
printf 'arquivos/%s.age\n' "${CHAVES[@]}" "$CHAVE_NOVA" | sort >"$temp/esperado.txt"
diff -u "$temp/esperado.txt" "$temp/na-copia.txt" >&2 ||
  reprovar "o bucket de backups deveria ter só as 5 cópias em arquivos/"
{ bkp listar diarios/; bkp listar mensais/; bkp listar outra-pasta/; } >"$temp/dumps-depois.txt"
cmp -s "$temp/dumps-antes.txt" "$temp/dumps-depois.txt" || reprovar "a cópia mexeu nos dumps"
ok "plano B: a cópia vai para arquivos/ do bucket de backups, sem tocar nos dumps"

# A retenção dos dumps (que tem permissão de apagar) nunca chega em arquivos/.
s3 reter --diarios 1 --mensais 1 >/dev/null 2>&1 || reprovar "a retenção falhou"
bkp listar arquivos/ | awk '{print $1}' | sort >"$temp/na-copia.txt"
diff -u "$temp/esperado.txt" "$temp/na-copia.txt" >&2 || reprovar "a retenção apagou uma cópia de arquivo"
ok "plano B: a retenção dos dumps não apaga as cópias dos arquivos"

s3t "$R2_ENDPOINT" "$BUCKET_NOVO-4" criar
env "${VARS_COPIA_BACKUPS[@]}" DESTINO_S3_ENDPOINT="$R2_ENDPOINT" DESTINO_S3_ACCESS_KEY_ID=teste \
  DESTINO_S3_SECRET_ACCESS_KEY=teste DESTINO_S3_BUCKET="$BUCKET_NOVO-4" DESTINO_S3_REGIAO=us-east-1 \
  BACKUP_AGE_KEY="$(cat "$temp/chave-teste.age")" "$pasta/restaurar-arquivos.sh" >"$temp/saida.txt" 2>&1 || {
  cat "$temp/saida.txt" >&2
  reprovar "a restauração a partir do bucket de backups falhou"
}
grep -q "restaurados agora: 5 · já no destino: 0" "$temp/saida.txt" || {
  cat "$temp/saida.txt" >&2
  reprovar "a restauração a partir do bucket de backups deveria restaurar as 5"
}
for i in 0 1 2 3; do
  s3t "$R2_ENDPOINT" "$BUCKET_NOVO-4" ler "arquivos/${CHAVES[$i]}" "$temp/restaurado"
  cmp -s "$temp/restaurado" "$temp/originais/$i" || reprovar "plano B: o arquivo $i não voltou igual"
done
ok "plano B: os arquivos voltam da cópia no bucket de backups para um bucket novo"

# --- Limpeza ---------------------------------------------------------------------------------
admin -c "drop database if exists $DESTINO with (force)" -c "drop database if exists $ORIGEM with (force)"
log "TUDO PASSOU ($passou verificações)"
