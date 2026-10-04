#!/usr/bin/env bash
# Confere que toda action usada nos workflows existe no GitHub e está fixada por SHA.
# Uso: scripts/dev/conferir-actions.sh   (precisa do `gh` logado)
# Sai com 1 se alguma referência não resolver ou não for um SHA de 40 caracteres.
set -euo pipefail

raiz="$(cd "$(dirname "$0")/../.." && pwd)"
falhas=0

while read -r ref; do
  repo="${ref%@*}"
  versao="${ref#*@}"
  if [[ ! "$versao" =~ ^[0-9a-f]{40}$ ]]; then
    echo "FALHA  $ref: fixe por SHA (tag flutuante pode sumir ou mudar)"
    falhas=1
    continue
  fi
  if gh api "repos/$repo/commits/$versao" --jq .sha >/dev/null 2>&1; then
    echo "ok     $ref"
  else
    echo "FALHA  $ref: commit não existe em $repo"
    falhas=1
  fi
done < <(grep -hoE 'uses:[[:space:]]*[^[:space:]#]+' "$raiz"/.github/workflows/*.yml \
  | sed -E 's/uses:[[:space:]]*//' | sort -u)

exit "$falhas"
