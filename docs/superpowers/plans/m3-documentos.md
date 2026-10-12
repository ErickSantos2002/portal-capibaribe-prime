# M3 · Épico A · Documentos · Plano de implementação

> **Para agentes:** executar tarefa por tarefa, com TDD (`superpowers:test-driven-development`).
> Passos em checkbox (`- [ ]`).

**Objetivo:** documentos de ponta a ponta (H-17, H-18, H-19, RF-33).

**Spec:** `docs/superpowers/specs/m3-documentos.md` · **Contrato:** `m3-contrato.md` (5.2, 7, 10).

## Restrições globais

- `uv run --frozen` em `api/`; Postgres próprio (`portal-pg-m3-documentos`, porta 55481),
  `PORTAL_TESTE_BANCO=portal_teste_m3_documentos`.
- Só os arquivos do épico A (contrato, seção 10). Nenhuma migração. `web/package.json` e
  `novidades.ts` ficam como estão. Nenhum teste fala com o R2 (fixture `armazenamento`).
- Antes de cada commit: pytest, ruff (check e format), vitest, eslint, tsc, testes node e
  `pre-commit run --all-files`. Commits pequenos na branch `m3/documentos`, com `Co-Authored-By`.

## Foco da revisão

- Conta comum pedindo documento `gestao` (lista, abrir, link direto de qualquer versão): 404.
- Sem sessão / sessão do primeiro acesso: só `publico`, nunca arquivado.
- Arquivo de outra unidade, pendente, de aviso, ou já usado: nunca entra no documento.
- "Avisar" com falha no meio: nem documento nem aviso ficam gravados.
- Abrir o PDF no celular sem cair no bloqueio de janela.

## Tarefas

- [x] **1. Spec, plano e dúvidas** (este arquivo, o spec e `duvidas-m3-documentos.md`).
- [ ] **2. Leitura (API):** `servicos/documentos.py` (`listar`, `publicos`, `abrir`,
  `link`); rotas; testes de quem vê o quê, ordem, versões anteriores, arquivados, link com e
  sem bucket, 404 iguais (`test_documentos_leitura.py`); apagar o épico A de
  `test_m3_em_construcao.py` e de `EM_CONSTRUCAO` (`test_cache.py`).
- [ ] **3. Gestão (API):** `publicar` (com e sem aviso; arquivo de outra unidade, pendente, de
  aviso, já usado; aviso automático e `agendar` só quando avisou; tudo ou nada), `nova_versao`
  (sequência, arquivado, histórico), `arquivar` (idempotente)
  (`test_documentos_gestao.py`).
- [ ] **4. Front, leitura:** `menu.ts`, `rotas.tsx`, `carregar.ts`, `formatos.ts`
  (assuntos, níveis, tamanho, busca), `Lista.tsx`, `DocumentoAberto.tsx`, `abrir.ts` (aba
  antes do pedido), `Publicos.tsx`, `LinkDocumentosPublicos.tsx`, `DocumentoDoAviso.tsx`,
  `documentos.css`; testes (`documentos.test.tsx`, `formatos.test.ts`); trocar o bloco "ainda
  não mostram nada" do `m3contrato.test.ts`.
- [ ] **5. Front, gestão:** `NovoDocumento.tsx`, `NovaVersao.tsx`, arquivar no documento
  aberto; testes (envio + publicar, reaproveitar o arquivo enviado, erros por campo, sem
  "avisar" para a gestão).
- [ ] **6. Conferência visual:** banco `portal_dev_m3_documentos`, S3 falso (`moto_server`),
  uvicorn na 8181, Vite na 5191; Playwright a 390 px e 1280 px como morador e como gestão;
  prints em `docs/superpowers/prints/m3-documentos/`.
- [ ] **7. Fechamento:** suíte inteira, dúvidas, relatório.
