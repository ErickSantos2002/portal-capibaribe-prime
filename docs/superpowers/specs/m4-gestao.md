# Spec · M4 · Épico A · Criar e gerir enquetes

| | |
|---|---|
| **Marco** | M4 · Enquetes |
| **História** | H-20 (RF-20, RF-23, RN-03), com o aviso automático (H-13) |
| **Contrato** | `docs/superpowers/specs/m4-contrato.md` (seções 3.1, 3.2, 4 e 5) |
| **Plano** | `docs/superpowers/plans/m4-gestao.md` |
| **Dúvidas** | `docs/superpowers/duvidas-m4-gestao.md` |
| **Criado em** | 14/10/2026 |

Este spec só detalha o que o contrato deixou para o épico; o resto vale como está lá.

## 1. API

Serviço novo `app/servicos/enquetes_gestao.py`; a rota (`app/rotas/enquetes_gestao.py`) só
traduz HTTP e agenda a notificação depois do commit.

### 1.1 Criar (`POST /api/enquetes`, `Gestao`)

Numa transação só, nesta ordem:

1. `avisos.gravar_publicacao` com o aviso automático: categoria `geral`, não fixado, mesmo
   destino da enquete. Bloco que não existe para aqui (422 `bloco_inexistente`).
2. `enquete` com `aviso_id`; as opções na ordem do formulário (1 a n); os blocos do destino.
3. Histórico `enquete_criada` (entidade `enquete`): `pergunta`, `opcoes` (quantas),
   `multipla_escolha`, `mostrar_resultado`, `para_todos`, `blocos` (números).
4. Commit. Erro do banco → `enquetes_banco.traduzir` (4xx, nunca 500). Depois do commit, a rota
   chama `notificacoes.agendar(tarefas, aviso_id)`.

Resposta 201 `EnqueteGravada` (`id`, `aviso_id`).

### 1.2 O aviso automático

- **Título:** `Enquete nova: <pergunta>`, cortado em 120 letras com "…".
- **Texto** (o mesmo serve no mural e no e-mail; usa as marcas do aviso: lista e destaque):

  ```
  Uma enquete nova está aberta no Portal: “<pergunta>”.

  As opções são:

  - <opção 1>
  - <opção 2>

  Dá para votar até <dd/mm/aaaa>, às <H>h<MM> (horário de Recife). <escolha>
  Vale um voto por apartamento, e dá para trocar o voto até o fim. <resultado>

  > Enquete é consulta. Não tem valor legal de votação em assembleia.

  O botão “Ir para a enquete”, neste aviso, leva direto a ela.
  ```

  `<escolha>`: "Pode marcar mais de uma opção." (múltipla) ou "Marque uma opção." (única).
  `<resultado>`: "O resultado aparece durante a votação." ou "O resultado só aparece quando a
  enquete terminar."
- O front mostra a mesma prévia ("Como o aviso vai ficar no mural"); `formatos.ts` do épico
  repete o texto, e um teste de cada lado confere a mesma frase.

### 1.3 Editar (`PUT /api/enquetes/{id}`, `Gestao`)

1. Busca a enquete **com trava** (`for update`). Não existe: 404 `enquete_nao_encontrada`.
2. Já tem voto (`primeiro_voto_em`): 409 `enquete_com_voto`. Já terminou: 409
   `enquete_encerrada` (a trava espera um voto em andamento; quem chega depois vê a coluna).
3. Nada mudou (pergunta, opções na ordem, tipo de escolha, término como instante, quando
   mostrar): 409 `sem_mudanca` "Nada mudou na enquete."
4. `UPDATE` da enquete **sempre** (mesmo se só as opções mudaram): o banco carimba
   `editada_em` e confere de novo voto e prazo. Se as opções mudaram, apaga e insere de novo, na
   ordem; se não, ficam as mesmas (com os mesmos ids: a tela de quem está votando não quebra).
5. Corrige o aviso com `avisos.gravar_correcao` (título e texto novos; categoria, evento e
   anexos ficam), **sem notificar**. Se o título e o texto do aviso ficariam iguais (ex.: só o
   segundo do término mudou), não corrige. Se o aviso foi arquivado, não corrige (dúvida 4).
6. Histórico `enquete_editada` (os mesmos campos da criação), commit, 200 `EnqueteGravada`.

## 2. Front (`web/src/enquetes/gestao/`)

- `rotas.tsx`: `/enquetes/nova` e `/enquetes/:id/editar`, atrás de `ExigeUnidade` +
  `ExigeGestao`.
- `Formulario.tsx`: o formulário comum (criar e editar), como o protótipo:
  pergunta; opções (começa com 2 caixas, "Adicionar opção" até 10, "Tirar" a partir da 3ª);
  "Pode marcar mais de uma"; término em **dia** e **hora** separados (como o evento do aviso;
  hora padrão 20:00, horário de Recife); "Mostrar o resultado" em duas opções explicadas;
  destino em botões (só ao criar; ao editar, só o texto, porque não muda); o alerta "Depois do
  primeiro voto, a pergunta e as opções não podem mais mudar."; a prévia do aviso automático;
  "Publicar enquete" / "Salvar alterações".
- Conferência na tela antes de enviar, com as mesmas frases da API; os 422 da API marcam o campo
  certo. Sair com algo escrito pergunta antes (como "Novo aviso").
- Depois de publicar ou salvar: vai para `/enquetes/{id}` (tela do épico B) com o recado
  "Enquete publicada. O aviso saiu no mural." / "Enquete atualizada. O aviso foi corrigido."
- Editar carrega a enquete com `abrirEnquete` (rota do épico B). Sem `pode_editar`, mostra por
  quê (terminou, ou já tem voto) e o link para a enquete, sem formulário. 409 ao salvar
  (`enquete_com_voto`, `enquete_encerrada`) mostra a frase e o mesmo link.
- CSS próprio: `web/src/enquetes/gestao/gestao.css`, com os tokens do Portal.

## 3. Fora deste épico

Lista, enquete aberta, voto, resultado, "quais votaram", item do menu e botão do aviso (épico
B). Cancelar, prorrogar depois do voto, texto explicativo (backlog, contrato seção 6).
