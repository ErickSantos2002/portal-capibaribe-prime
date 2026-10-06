# Plano · M2 · Épico A · Push e PWA

Spec: `docs/superpowers/specs/m2-push.md`. Branch `m2/push`. Banco de teste
`PORTAL_TESTE_BANCO=portal_teste_m2_push`. Cada passo: teste que falha → código → verde →
commit pequeno.

## Tarefas

1. **Docs**: spec, plano e `duvidas-m2-push.md`.
2. **API · rotas** (`test_push_rotas.py`):
   1. `GET /api/notificacoes` com e sem VAPID, com e sem inscrição nesta sessão.
   2. `PUT`: 503 sem VAPID; guarda na sessão da requisição; troca o endpoint da sessão; move o
      endpoint de outra sessão; 409 `limite_de_aparelhos` no 11º.
   3. `DELETE`: apaga só a desta sessão; idempotente.
   4. Apagar a seção do épico A em `test_m2_em_construcao.py` e tirar `/api/notificacoes` de
      `EM_CONSTRUCAO` em `test_cache.py`.
3. **API · envio** (`test_push_envio.py`, `pywebpush.webpush` trocado por um falso):
   1. `ligado()` segue a configuração.
   2. Corpo `PushAviso`, TTL, `Urgency`, `Topic`, `timeout`, `aud` de cada endpoint.
   3. 201 entregue; 404/410 apagam a inscrição e contam `removidas` e `falhas`; 500 e erro de
      rede contam `falhas`.
   4. `tempo_esgotado` vira `pulados`; `salvar` a cada lote; sem commit; log sem endpoint.
   5. De ponta a ponta: publicar com VAPID ligado e o `webpush` falso → `concluido` com as
      contagens em `/api/avisos/{id}/envios`.
4. **Front · PWA**: `manifest.webmanifest`, `sw.js` (teste no `self` falso), `index.html`,
   `web/testes/pwa.test.ts`.
5. **Front · lógica**: `aparelho.ts`, `inscricao.ts`, `ganchos.ts` (testes primeiro).
6. **Front · telas**: `useNotificacoes`, `ReceberAvisos` + rota, `SecaoNotificacoes`, CSS próprio;
   ajustar o teste de encaixes (`m2contrato.test.ts`, só as linhas do épico A).
7. **Conferência**: API local + `vite preview` com banco próprio; Playwright em 390 px e no
   computador; prints.
8. **Fechamento**: `uv run pytest`, `ruff`, `npm test`, `tsc`, `eslint`; relatório com o texto
   sugerido das novidades.
