# M4 · Épico A · Criar e gerir enquetes · Plano

> Executar em sequência, com TDD (`superpowers:test-driven-development`): teste vermelho, código,
> verde, commit.

**Spec:** `docs/superpowers/specs/m4-gestao.md` · **Contrato:** `m4-contrato.md`

**Restrições:** só os arquivos do épico A (contrato, seção 5); banco de teste próprio
(`portal-pg-m4-gestao`, porta 55461, `PORTAL_TESTE_BANCO=portal_teste_m4_gestao`); sem push,
merge, Vercel, Neon ou R2; `web/package.json` e `novidades.ts` intactos.

### Tarefa 1 · Criar pela API
**Arquivos:** `api/testes/test_enquetes_gestao.py`, `api/app/servicos/enquetes_gestao.py`,
`api/app/rotas/enquetes_gestao.py`, `api/testes/test_m4_em_construcao.py` (apagar a seção A).
- [x] Testes: 201 com `id` e `aviso_id`; enquete, opções na ordem e blocos gravados; aviso com
  título, texto, categoria e destino; notificação agendada e pedido de envio gravado; histórico
  `enquete_criada`; pergunta comprida cortada no título; bloco inexistente 422 sem gravar nada;
  admin também cria; o aviso aberto aponta para a enquete.
- [x] Implementar; verde; commit.

### Tarefa 2 · Editar pela API
- [x] Testes: troca tudo (pergunta, opções, tipo, término, resultado) e corrige o aviso (versão
  2, sem notificar); opções iguais mantêm os ids; só o término muda; nada mudou → 409
  `sem_mudanca`; com voto → 409 `enquete_com_voto`; encerrada → 409 `enquete_encerrada`;
  inexistente → 404; aviso arquivado → edita sem corrigir o aviso; mudança só de segundos no
  término não corrige o aviso; histórico `enquete_editada`; erro no meio desfaz tudo.
- [x] Implementar; verde; commit.

### Tarefa 3 · Front
**Arquivos:** `web/src/enquetes/gestao/**`.
- [x] Testes (vitest, API de mentira): formulário publica com o corpo certo e vai para a
  enquete; conferências na tela; adicionar e tirar opção (limite 10); 422 da API marca o campo;
  prévia do aviso igual à da API; destino em botões e o alcance; editar carrega e salva;
  editar sem `pode_editar` explica; 409 ao salvar explica; comum não vê o formulário.
- [x] Implementar com o visual do Portal; conferência visual no celular e no computador;
  commit.

### Tarefa 4 · Fechamento
- [x] `duvidas-m4-gestao.md`; suíte inteira (pytest, vitest, eslint, tsc, pre-commit); commit;
  derrubar o container.

---

## Estado (14/10/2026, épico concluído)

Tarefas 1 a 4 feitas na branch `m4/gestao` (sem push, sem merge). API: 1713 testes verdes.
Front: 573 testes; falha só `m4contrato.test.ts` → "rotas vazias e sem item no menu", que confere
que as rotas do épico A não existem (arquivo comum; conserto de uma linha no fechamento,
`duvidas-m4-gestao.md`, item 1). Prints da conferência visual (celular, computador, escuro)
ficaram fora do repositório.
