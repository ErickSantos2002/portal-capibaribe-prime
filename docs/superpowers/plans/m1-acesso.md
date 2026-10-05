# M1 · Épico A · Acesso · Plano de implementação

> Executar tarefa por tarefa com TDD (`superpowers:test-driven-development`): teste vermelho,
> código mínimo, verde, commit. Spec: `docs/superpowers/specs/m1-acesso.md`.

**Restrições:** só os arquivos do épico A (contrato, seção 7); Python via `uv run`; banco de
teste `PORTAL_TESTE_BANCO=portal_m1_acesso`; sem `style=` no JSX; sem push, merge, Vercel ou Neon.

## Tarefas

- [ ] **1. Entrar e bloqueio (API)** — `testes/test_acesso_entrar.py`: senha certa abre sessão e
  devolve `Eu`; login inexistente, desativado e senha errada dão a mesma resposta; unidade não
  ativada entra com `precisa_trocar_senha`; 5 erros → 6ª recusada mesmo com a senha certa, com
  minutos e histórico; bloqueio vencido volta a aceitar; senha certa zera as tentativas; sessão
  dura 180 dias; sem `X-Portal` → 403. Depois: `servicos/acesso.py` + rota.
- [ ] **2. Primeiro acesso (API)** — `testes/test_acesso_primeiro.py`: cada mensagem de recusa;
  conclui → ativada com data, histórico, cookie novo, sessão antiga morta; repetir → 409; sem
  sessão → 401; e-mail opcional.
- [ ] **3. Minha unidade (API)** — `testes/test_minha_unidade.py`: ver, editar, trocar senha,
  desconectar aparelho (próprio e de outra unidade), apagar dados (com e sem papel), sessão
  restrita recusada.
- [ ] **4. Telas de acesso (front)** — `web/src/acesso/*.test.tsx` primeiro: entrar (bloco +
  apartamento → login, erro, bloqueio, colar 1203), primeiro acesso (aviso, validação, sucesso),
  privacidade, minha unidade (ficha, editar, senha, aparelhos, apagar com confirmação).
- [ ] **5. Navegador** — API (8101) + vite com proxy próprio (5101) e build com os cabeçalhos de
  produção; 390 px e 1366 px, claro e escuro; console sem CSP; prints no scratchpad
  (fora do repositório).
- [ ] **6. Fechamento** — pytest inteiro, pyright, ruff, lint, typecheck, test, build; dúvidas
  registradas.
