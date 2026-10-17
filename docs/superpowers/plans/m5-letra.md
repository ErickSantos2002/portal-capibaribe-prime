# M5 · Letra que cresce · Plano

> Execução: a base (tarefas 1 a 5) por um agente, com TDD (`superpowers:test-driven-development`);
> depois os grupos G1, G2 e G3 **em paralelo**, um agente por grupo, cada um na sua branch a partir
> de `m5/letra-base`. O coordenador junta tudo, cuida da versão e das novidades e faz a tarefa 6.

**Spec (a regra):** `docs/superpowers/specs/m5-letra.md` · **Dúvidas:** `docs/superpowers/duvidas-m5-letra.md`

## Restrições (todos)

- Só os arquivos do seu grupo (tabela abaixo). Precisou mudar o comum (`estilo.css`, `marca.css`,
  `casca/`)? Registre em `duvidas-m5-letra.md` e contorne no CSS do seu épico.
- Nada de versão (`web/package.json`) nem `web/src/sobre/novidades.ts`: o coordenador faz no fim.
- A letra de fábrica não muda: os prints a 16 px depois da conversão têm de ser iguais aos de
  antes (`comparar-prints.mjs`). Mudou? É regressão, a menos que esteja escrito nas dúvidas por quê.
- Container, portas e pasta de prints próprios (tabela abaixo); derrubar o container no fim.
- Sem push, merge, Vercel, Neon ou R2. Commits em português, pre-commit sem `--no-verify`.

## Base (feita: branch `m5/letra-base`)

- [x] **1. Pesquisa** (Chrome Android e a meta `text-scale`, Safari e o `-apple-system-body`, PWA,
  computador), com fato × a testar: spec, seção 2.
- [x] **2. Regra, tabela e exceções:** spec, seções 3 e 4.
- [x] **3. Guarda** `web/testes/letra.test.ts` (vermelha antes da conversão, com 2 CSS × dezenas
  de achados; prova a própria regra com CSS de exemplo; conferida por mutação: um `padding: 12px
  14px` de volta no `marca.css` reprova).
- [x] **4. Base convertida:** `estilo.css` e `marca/marca.css` (com `px-para-rem.mjs` e à mão),
  meta `text-scale` no `index.html`, `-apple-system-body` no iPhone, `Icone` em rem (`emRem`,
  teste `casca/icone.test.tsx`), teto da spec 3.5 no comum.
- [x] **5. Ferramenta de conferência** (`ambiente-conferencia.sh`, `conferir-letra.mjs`,
  `comparar-prints.mjs`) e rodada antes/depois: spec, seção 6.

## Grupos (em paralelo)

| Grupo | Arquivos | Telas no script (`--grupo`) | Container / API / web |
|---|---|---|---|
| **G1** | `avisos/avisos.css`, `avisos/anexos.css`, `avisos/IconesAnexo.tsx` | mural, aviso, aviso-fixado, novo-aviso, quem-leu | `m5-letra-g1` · 55471 · 8171 · 5171 |
| **G2** | `documentos/documentos.css`, `sobre/sobre.css`, `notificacoes/notificacoes.css`, `documentos/pecas.tsx` (`IconeDoc`) | documentos, documentos-publicos, novo-documento, receber-avisos, o-que-mudou | `m5-letra-g2` · 55472 · 8172 · 5172 |
| **G3** | `enquetes/gestao/gestao.css`, `enquetes/votar/enquetes.css`, `acesso/acesso.css`, `recuperacao/recuperacao.css`, `administracao/administracao.css`, e o teste `web/testes/estilo-m4.test.ts` (ponto 21) | entrar, privacidade, minha-unidade, esqueci-a-senha, enquetes, enquete, nova-enquete, votantes, painel, ficha-unidade, historico | `m5-letra-g3` · 55473 · 8173 · 5173 |

O que a rodada da base já achou para cada grupo (spec, seção 6): **G1** as categorias do novo
aviso e o `input` de anexo (rolagem a 24 e 32 px), a grade de "Quem leu" (alvos de 38 px e não
cresce), o ícone do "Fixado" que não cresce; **G2** a lista de documentos (letra 26 a 32 px) e a
janela "O que mudou" (18); **G3** "Dia/Hora do término" lado a lado (rolagem a 32 px), o celular
como link na ficha (alvo de 21 px de altura).

### Passo a passo de cada grupo (troque `g1`, `G1` e as portas pelas do seu)

Da raiz da cópia de trabalho, numa branch nova a partir de `m5/letra-base`:

```sh
git switch -c m5/letra-g1 m5/letra-base
npm ci --prefix web
scripts/dev/ambiente-conferencia.sh subir m5-letra-g1 55471 8171 5171

# 1. Antes de mexer: os prints de referência (só as telas do grupo). A 1ª rodada cria os
#    avisos e a enquete fictícios (--semear) e lê os avisos uma vez; rode duas vezes e use a 2ª
#    como "antes" (na 1ª, o "Novo" dos avisos ainda aparece).
node scripts/dev/conferir-letra.mjs --base http://localhost:5171 --tarefa g1-antes --grupo G1 --semear
node scripts/dev/conferir-letra.mjs --base http://localhost:5171 --tarefa g1-antes --grupo G1

# 2. Converter: primeira passada mecânica, depois à mão (exceções com /* px: motivo */, teto)
node scripts/dev/px-para-rem.mjs web/src/avisos/avisos.css web/src/avisos/anexos.css
#    e tire as linhas dos SEUS arquivos de PENDENTES em web/testes/letra.test.ts (deixe os
#    comentários "// G1", "// G2", "// G3": separam as mudanças dos três grupos no merge)
cd web && node --test testes/letra.test.ts && cd ..

# 3. Rever no navegador (o build do preview tem de ser refeito a cada mudança de CSS)
cd web && npx vite build --logLevel warn && cd ..
node scripts/dev/conferir-letra.mjs --base http://localhost:5171 --tarefa g1-depois --grupo G1
node scripts/dev/comparar-prints.mjs /tmp/portal-letra-g1-antes /tmp/portal-letra-g1-depois
#    O resumo fica em /tmp/portal-letra-g1-depois/resumo.txt; os prints na mesma pasta.
#    Uma tela só, ou só a letra grande: --telas novo-aviso --larguras 360 --fontes 32

# 4. Fechar
cd web && npm test && npm run lint && npx tsc -b && cd ..
git add -A && git commit        # mensagem em português, com a linha Co-Authored-By
scripts/dev/ambiente-conferencia.sh descer m5-letra-g1
```

Pronto quando: `letra.test.ts` cobre os seus arquivos (fora de `PENDENTES`) e passa; as telas do
seu grupo saem **sem rolagem, sem nada fora da tela e sem cortado** a 16, 24 e 32 px, em 360 e
1280; a letra mediana bate o esperado (18 → 27 → 36); `comparar-prints.mjs` diz que os prints a
16 px estão iguais (diferença só no horário do "aparelho conectado" de Minha unidade, que é dado,
não CSS); os alvos < 44 que já existiam antes com a letra de fábrica estão nas dúvidas, e nenhum
novo. Registre no fim de `duvidas-m5-letra.md` (seção do seu grupo) o que decidiu, e a rodada
antes/depois (as duas tabelas do resumo).

### Dicas que valem para os três (vieram da base)

- `overflow-wrap: anywhere` só no componente que precisa (texto como item de flex/grid); no
  `body` ele já é `break-word`. Item de grid com palavra comprida: `minmax(0, 1fr)`.
- Coisas lado a lado que não cabem com letra grande: `flex-wrap: wrap` + `flex: 1 1 <n>rem`
  (a base em rem decide quando desce de linha), ou `repeat(auto-fit, minmax(min(100%, <n>rem), 1fr))`.
  Escolha o `<n>` de modo que, com a letra de fábrica, tudo continue na mesma linha (o
  `comparar-prints` prova).
- Rádio/caixa escondidos: o `.oculto` do comum (com `clip-path`), não um `width: 1px` solto, que
  com letra grande empurra a página (é o caso do `input` de anexo).
- Ícone próprio do épico: `width={emRem(tamanho)}`, com `import { emRem } from '../casca/emRem'`.
- Media query: `56.25em` (900 px). `@container` também em rem/em.
- Seletor mais forte dentro de `@media` vence a regra do computador: confira os prints de 1280.

## 6. Fechamento do M5 (coordenador)

- [ ] Juntar `m5/letra-base` e os três grupos; `PENDENTES` vazio; suíte inteira.
- [ ] Rodada completa do `conferir-letra.mjs` (todas as telas, também `--temas escuro`).
- [ ] Versão e novidade em `novidades.ts` (na voz do morador: "o tamanho de letra do celular
  agora vale no Portal").
- [ ] **Aparelho real** (só dá para conferir assim; spec 2): Android com Chrome ≥ 146 e o
  "Tamanho da fonte" no máximo, no navegador e com o Portal instalado; iPhone com Tamanho do
  Texto grande e com "Tamanhos maiores de acessibilidade", no Safari e instalado. Em cada um:
  mural, aviso aberto, entrar, votar. O que olhar: a letra cresce, nada rola para o lado, as abas
  de baixo se leem. Resultado nas dúvidas.
