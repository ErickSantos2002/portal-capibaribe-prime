# Plano · M3 · Épico B · Anexos nos avisos

Spec: `docs/superpowers/specs/m3-anexos.md`. Branch `m3/anexos`. Banco de teste
`PORTAL_TESTE_BANCO=portal_teste_m3_anexos` (Postgres próprio na porta 55482). Cada passo: teste
que falha → código → verde → suíte inteira + `pre-commit run --all-files` → commit pequeno.

## Tarefas

1. **Docs**: spec, plano e `duvidas-m3-anexos.md`.
2. **API · publicar com anexos** (`test_anexos_publicar.py`):
   1. 1 e 5 anexos: gravados na ordem, `anexos` no aviso aberto, `quantidade_anexos` no mural.
   2. 6 anexos, repetido, de outra unidade, pendente, de documento, inexistente, já usado em
      outro aviso: 422 com campo `anexos`, nada gravado.
   3. Corrida: `arquivo_em_uso` do banco vira a mesma 422.
   4. `gravar_publicacao` sem anexos continua igual (épico A).
3. **API · corrigir com anexos** (`test_anexos_corrigir.py`): omitido e nulo repetem; `[]` tira;
   lista troca; só a ordem é mudança; tudo igual é `sem_mudanca`; outro membro da gestão repete
   os anexos de quem publicou; a versão antiga mantém os dela.
4. **API · link** (`test_anexos_link.py`): visível, versão antiga, `baixar`, outro bloco (404),
   arquivo de outro aviso (404), sem bucket (503 depois das conferências). Apagar a seção
   "épico B" de `test_m3_em_construcao.py` e tirar a rota de `EM_CONSTRUCAO` em `test_cache.py`.
5. **Front · lógica** (`anexos.test.ts`): tamanho em texto, foto ou PDF, "N anexos", a fila e a
   situação para publicar.
6. **Front · aviso aberto e mural** (`anexos-telas.test.tsx`): fotos com link, visualizador,
   PDF abrindo em outra aba, erro do link, versão antiga, clipe no mural.
7. **Front · formulário**: escolher, enviar um de cada vez, erro e "Tentar de novo", tirar,
   limite de 5, bloqueio ao publicar, prévia, correção com a lista.
8. **Conferência**: Postgres + `moto_server` + API (8182) + Vite (5192); Playwright em 390 px e
   1280 px, gestão e morador; prints em `docs/superpowers/prints/m3-anexos/`.
9. **Fechamento**: suíte inteira, relatório.
