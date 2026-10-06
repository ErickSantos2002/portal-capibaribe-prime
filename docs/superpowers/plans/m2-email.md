# M2 · Épico B · E-mail e "esqueci a senha" · Plano de implementação

> **Para agentes:** executar tarefa por tarefa, com TDD (`superpowers:test-driven-development`).
> Passos em checkbox (`- [ ]`).

**Objetivo:** cópia do aviso por e-mail e "esqueci a senha" completo (H-04, H-13 e-mail).

**Spec:** `docs/superpowers/specs/m2-email.md` · **Contrato:** `m2-contrato.md` (4.3, 5, 9).

## Restrições globais

- `uv run --frozen`; banco de teste `PORTAL_TESTE_BANCO=portal_teste_m2_email`.
- Só os arquivos do épico B (contrato, seção 9). Nenhuma migração. `web/package.json` e
  `novidades.ts` ficam como estão.
- Nenhum e-mail de verdade: SMTP falso nos testes; na conferência visual, a API sobe com um
  servidor SMTP local que só guarda as mensagens em arquivo.
- Commits pequenos na branch `m2/email`, em português, com `Co-Authored-By`.

## Tarefas

- [x] **1. Spec e plano** (este arquivo e o spec).
- [ ] **2. Markdown restrito → HTML** (`email.html_do_texto`): teste de paridade com os exemplos
  do `formatacao.test.ts` e de escape (`test_email_formatacao.py`); depois o código.
- [ ] **3. Mensagens** (`mensagem_do_aviso`, `mensagem_de_recuperacao`): cabeçalhos, um
  destinatário, assunto numa linha, texto + HTML, link do aviso e do token, rodapé
  (`test_email_mensagens.py`).
- [ ] **4. Conexão e `ENVIADOR`**: SMTP falso; 465 com SSL, outra porta com STARTTLS; uma
  conexão por lote; reserva antes; `pulados`; tempo; recusa segue; queda levanta; `salvar` a
  cada 25; integrado com `notificacoes.processar` (`test_email_envio.py`).
- [ ] **5. `processar_pedido`**: cada motivo, histórico 1×/hora, token só em hash, e-mail
  depois do commit, nada levanta, log sem dado (`test_recuperacao_pedido.py`).
- [ ] **6. `conferir` e `redefinir`** (serviço e rotas): vencido, usado, senha já trocada,
  inexistente, unidade resetada; redefinir entra, derruba os outros aparelhos e os outros links,
  histórico, bloqueio esquecido; apagar a seção do épico B de `test_m2_em_construcao.py`
  (`test_recuperacao_link.py`). Fluxo completo e respostas iguais com e sem e-mail
  (`test_recuperacao_fluxo.py`).
- [ ] **7. Front**: `LinkEsqueci` → link; `EsqueciASenha.tsx`; `RedefinirSenha.tsx`;
  `rotas.tsx`; `recuperacao.css`; testes `recuperacao.test.tsx`; ajustar o teste de encaixe
  (`m2contrato.test.ts`) e o de entrar (`Entrar.test.tsx`), registrado nas dúvidas.
- [ ] **8. Conferência visual**: banco `portal_dev_m2_email`, uvicorn com SMTP local de
  mentira, `vite preview`, Playwright a 390 px e desktop; prints em
  `docs/superpowers/prints/m2-email/`; HTML de exemplo dos dois e-mails e print deles.
- [ ] **9. Fechamento**: `uv run pytest`, `npm test`, ruff, tsc, eslint; dúvidas; relatório.
