# Plano · M1 · Correções da revisão independente

| | |
|---|---|
| **Marco** | M1 · Acesso e mural |
| **Branch** | `m1/revisao` |
| **Base** | achados dos dois revisores (código e UX), decisões do coordenador |
| **Dúvidas** | `docs/superpowers/duvidas-m1.md`, seção "Revisão do marco" |

Regra: **cada item ganha primeiro um teste de regressão que falha na `main`**; depois a
correção; commit pequeno por item (ou par de itens que mexem no mesmo lugar).

## Banco · migração 0003 (uma só, mesmo padrão da 0002)

1. `entrada_tentativa` (C2): `login`, `ip_hash` (HMAC, nunca o IP cru), `falhas_em`
   (datas das falhas dos últimos 15 min), `bloqueada_ate`, `expira_em`; PK (`login`,
   `ip_hash`); o `app` lê, insere, altera e apaga (a linha expira). Sai de `unidade`:
   `tentativas_falhas` e `bloqueada_ate` (o bloqueio deixa de ser da unidade inteira).
2. Trigger de `aviso_versao` (C4) trava a linha do aviso (`for share`) e recusa versão nova em
   aviso arquivado (restrição `aviso_versao_arquivado`).
3. `aviso_leitura.versao_lida` (U1): a maior versão que a unidade abriu; preenchida pelas
   datas na migração; `lido_em` continua a da primeira leitura (trigger); o `app` só altera
   `versao_lida`, e ela só cresce.

## API

| Item | Teste primeiro | Correção |
|---|---|---|
| C6 | toda resposta de `/api` tem `Cache-Control: no-store` | middleware ASGI único |
| C3 | NUL e controle viram 422 em todo texto livre | validador comum `sem_controle` |
| C2 | bloqueio por (login, IP); outro IP entra; erro velho não conta; certo zera | serviço novo `tentativas.py` |
| C1 | apagar dados sem senha / com senha errada recusa e conta tentativa | `ApagarDados.senha` |
| C4 | arquivar × corrigir ao mesmo tempo; versão em arquivado recusada no banco | 0003 |
| C5 | impasse real (40P01) ao retirar papel vira 409 | tradução nas rotas de papel e reset |
| U1 | leitura de versão antiga → `corrigido_desde_a_leitura` | `versao_lida` |
| U3 | 401 traz `tentativas_restantes` a partir do 3º erro | mensagem e extra |
| U5 | `Leitura` separa quem não entrou de quem entrou e não leu | `nao_entraram`, `entraram_sem_ler` |
| U7 | senha nova igual à atual: 422 | validador do `TrocarSenha` |

## Front

U1 a U11 nas telas (Vitest primeiro), mais C1 (campo de senha e o aviso em destaque).
Depois, script Playwright próprio (320, 390, 1366; claro e escuro; CSP; rolagem horizontal;
axe nas seis telas), banco `portal_m1_revisao`, portas 8120/5120.

## Fim

pytest, pyright, ruff, lint, typecheck, `npm test`, build, migração do zero
(upgrade/downgrade/upgrade). Sem merge, sem push, sem Vercel/Neon.
