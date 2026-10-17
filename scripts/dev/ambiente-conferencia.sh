#!/usr/bin/env bash
# Sobe (ou derruba) um Portal local completo para conferência visual: Postgres num container
# próprio, banco com carga inicial e dados fictícios (admin 1002, Comissão 1003, senha mudar123),
# a API (uvicorn) e o front já construído (vite preview). Cada cópia de trabalho usa o seu nome e
# as suas portas, então vários agentes sobem o seu ao mesmo tempo sem se cruzar.
#
# Uso (da raiz do repositório):
#   scripts/dev/ambiente-conferencia.sh subir  <nome> <porta-pg> <porta-api> <porta-web>
#   scripts/dev/ambiente-conferencia.sh descer <nome>
# Ex.: scripts/dev/ambiente-conferencia.sh subir m5-letra 55470 8170 5170
#      → container portal-pg-<nome>, Portal em http://127.0.0.1:<porta-web>
#
# Só dados fictícios (RNF-16): nada de produção, Neon, R2 ou e-mail. Os arquivos (M3) vão para
# um bucket de mentira, em memória (scripts/dev/api-conferencia.py), então dá para semear
# documentos e anexos (conferir-letra.mjs --semear); e o push fica ligado com um par VAPID
# gerado na hora (nenhuma notificação sai: ninguém se inscreve), para a faixa "Falta um passo"
# e o "Receber os avisos" aparecerem como para o morador.
# Os logs da API e do preview ficam em /tmp/portal-<nome>-{api,web}.log.
set -euo pipefail

raiz="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
acao="${1:-}"
nome="${2:-}"
[[ -n "$acao" && -n "$nome" ]] || {
  echo "uso: $0 subir <nome> <porta-pg> <porta-api> <porta-web> | descer <nome>" >&2
  exit 2
}
container="portal-pg-$nome"
pids="/tmp/portal-$nome.pids"

# Mata um processo e todos os descendentes dele. O pid gravado é o do `uv run`/`npx`, que
# abrem filhos (o python da API, o node do vite): matar só o pai deixava os filhos órfãos,
# segurando a porta, e o próximo `subir` falhava ou conversava com o preview velho. Cada um
# sobe na própria sessão (setsid), então o grupo inteiro cai junto; a descida pela árvore
# (pgrep -P) pega quem tenha saído do grupo.
matar_arvore() {
  local pid="$1" filho
  for filho in $(pgrep -P "$pid" 2>/dev/null); do matar_arvore "$filho"; done
  kill "$pid" 2>/dev/null || true
}

descer() {
  if [[ -f "$pids" ]]; then
    while read -r pid; do
      [[ -n "$pid" ]] || continue
      kill -- "-$pid" 2>/dev/null || true
      matar_arvore "$pid"
    done <"$pids"
    rm -f "$pids"
  fi
  docker rm -f "$container" >/dev/null 2>&1 || true
  echo "derrubado: $container (e a API e o preview, se estavam no ar)"
}

if [[ "$acao" == descer ]]; then
  descer
  exit 0
fi
[[ "$acao" == subir && $# -eq 5 ]] || {
  echo "uso: $0 subir <nome> <porta-pg> <porta-api> <porta-web>" >&2
  exit 2
}
porta_pg="$3"
porta_api="$4"
porta_web="$5"

# Subir duas vezes não deixa nada do ambiente anterior no ar; e, se algo falhar no meio, o que
# já subiu cai junto (nada de processo órfão segurando a porta).
descer >/dev/null
trap 'echo "falhou na linha $LINENO; derrubando o que subiu" >&2; descer >&2' ERR
docker run -d --name "$container" -e POSTGRES_PASSWORD=teste \
  -p "127.0.0.1:$porta_pg:5432" postgres:17 >/dev/null
echo -n "esperando o Postgres"
until docker exec "$container" pg_isready -U postgres -q 2>/dev/null; do
  echo -n .
  sleep 1
done
# O pg_isready responde antes do fim da inicialização do container; mais uma conferida real.
until docker exec "$container" psql -U postgres -tAc 'select 1' >/dev/null 2>&1; do sleep 1; done
echo " pronto"

# Os mesmos papéis que os testes da API criam (api/testes/conftest.py).
docker exec "$container" psql -q -U postgres \
  -c "create role dono login password 'dono-teste'" \
  -c "create role app login password 'app-teste'" \
  -c "create database portal_dev owner dono"

banco="127.0.0.1:$porta_pg/portal_dev"
export DATABASE_URL="postgresql://app:app-teste@$banco"
export DATABASE_URL_DONO="postgresql://dono:dono-teste@$banco"
export PORTAL_AMBIENTE=local
export PORTAL_URL_BASE="http://127.0.0.1:$porta_web"

cd "$raiz/api"
uv run --frozen alembic upgrade head >/dev/null
uv run --frozen python -m app.comandos.carga_inicial
uv run --frozen python -m app.comandos.dados_ficticios
# Par VAPID só deste ambiente, nunca gravado: some quando o processo da API acaba.
PORTAL_VAPID_PRIVADA="$(uv run --frozen python -m app.comandos.gerar_chaves_vapid |
  sed -n 's/^PORTAL_VAPID_PRIVADA=//p')"
export PORTAL_VAPID_PRIVADA
export PORTAL_VAPID_CONTATO="mailto:conferencia@example.com"

: >"$pids"
PYTHONPATH="$raiz/api" setsid nohup uv run --frozen python "$raiz/scripts/dev/api-conferencia.py" --port "$porta_api" \
  >"/tmp/portal-$nome-api.log" 2>&1 &
echo $! >>"$pids"

cd "$raiz/web"
npx vite build --logLevel warn
PORTAL_API_URL="http://127.0.0.1:$porta_api" setsid nohup npx vite preview --host 127.0.0.1 \
  --port "$porta_web" --strictPort >"/tmp/portal-$nome-web.log" 2>&1 &
echo $! >>"$pids"

echo -n "esperando a API e o preview"
for _ in $(seq 60); do
  if curl -fs "http://127.0.0.1:$porta_web/api/saude" >/dev/null 2>&1; then
    echo " pronto"
    echo "Portal em http://localhost:$porta_web (admin 1002, Comissão 1003, senha mudar123)"
    exit 0
  fi
  echo -n .
  sleep 1
done
echo " não respondeu; veja /tmp/portal-$nome-api.log e /tmp/portal-$nome-web.log" >&2
descer >&2
exit 1
