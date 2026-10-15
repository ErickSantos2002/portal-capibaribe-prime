# M4 · Épico B · Votar e resultado · Plano

> Execução: o próprio agente do épico, em sequência, com TDD
> (`superpowers:test-driven-development`).

**Spec:** `docs/superpowers/specs/m4-votar.md` · **Contrato:** `docs/superpowers/specs/m4-contrato.md`

## Restrições

- Só os arquivos do épico B (contrato, seção 5). Comum que precisar mudar: registrar em
  `duvidas-m4-votar.md` e contornar.
- Banco de teste próprio: container `portal-pg-m4-votar` (porta 55462),
  `PORTAL_TESTE_BANCO=portal_teste_m4_votar`; removido no fim.
- Sem push, merge, Vercel, Neon ou R2. `web/package.json` e `novidades.ts` intactos.

## Tarefas

### 1. Resultado e lista (API)
- [x] `test_enquetes_resultado.py` vermelho: quem vê (404 igual), lista na ordem, `ja_votou`,
  resultado com votos e participação, "só no fim" nulo para todos (inclusive gestão) e visível
  depois do prazo, `pode_votar`/`pode_editar`, votantes sem o voto.
- [x] `app/servicos/enquetes.py` (`listar`, `abrir`, `votantes`) e as rotas; verde.

### 2. Votar e trocar (API)
- [x] `test_enquetes_voto.py` vermelho: votar, trocar (vale o último), escolha única com duas
  (422), múltipla, opção de outra enquete (409 `enquete_mudou`), encerrada (409), gestão fora do
  destino (403), comum fora do destino (404), erro do banco vira 409; **duas requisições em
  paralelo da mesma unidade = um voto só, sem erro** (conferido por mutação).
- [x] `votar` no serviço e na rota; apagar a seção "épico B" de `test_m4_em_construcao.py`; verde.

### 3. Front
- [x] Testes de tela vermelhos (`votar.test.tsx`, `formatos.test.ts`): menu, lista com selo,
  votar e trocar, confirmação no lugar, "só no fim", terminada, gestão (votantes, editar), aviso
  com o botão.
- [x] Telas, CSS, encaixes; ajustar a parte do épico B do `m4contrato.test.ts` (dúvida 1);
  verde; eslint + tsc.

### 4. Conferência e fechamento
- [x] Prints (Playwright próprio, celular e computador, claro e escuro).
- [x] Suíte inteira (pytest, vitest, cabeçalhos, eslint, tsc, pre-commit); commit; container
  derrubado.
