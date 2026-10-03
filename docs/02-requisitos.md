# 02 · Requisitos — Portal Capibaribe Prime

| | |
|---|---|
| **Status** | v0.1 |
| **Autor** | Erick Santos Dantas |
| **Criado em** | 02/10/2026 |
| **Base** | `01-visao.md` v0.2 |
| **Próximo documento** | `03-historias.md` |

---

## 1. Como ler este documento

Cada requisito tem um código e uma **entrega** (quando entra):

| Entrega | Nome | Quando | Para quê |
|---|---|---|---|
| **E1** | Fase de obra | 2026–2027 | Comunicação oficial entre compradores, Comissão de Representantes e (depois) gestão. Útil antes da entrega das chaves. |
| **E2** | Mudança e dia a dia | Perto da entrega (2028) | Reservas, chamados, encomendas, visitantes e garantia da construtora |
| **E3** | Gestão | Após a 1ª assembleia | Financeiro, assembleias, manutenção, funcionários |

> **Decisão (02/10/2026):** a E1 é a comunicação da fase de obra. Motivo: é a única parte que
> tem uso real antes de 2028, tira o grupo de WhatsApp do centro e dá visibilidade ao projeto
> antes da eleição de síndico.

Códigos: **RF** = requisito funcional (o que o sistema faz) · **RNF** = não funcional (como ele
se comporta) · **RN** = regra de negócio (regra do condomínio que o sistema respeita).

Cada entrega precisa funcionar **sozinha**. Se o projeto parar depois da E1, a E1 continua útil.

## 2. Perfis e permissões

Os perfis da visão, mais um técnico. Uma pessoa pode ter mais de um perfil (um proprietário
pode ser da Comissão, por exemplo).

| Perfil | Entra em | Resumo |
|---|---|---|
| **Administrador do sistema** | E1 | Mantém o Portal funcionando: aprova cadastros, gerencia perfis. Na E1 é o Erick. |
| **Comissão de Representantes** | E1 | Publica avisos e documentos da obra, cria enquetes. Deixa de existir após a entrega. |
| **Proprietário** | E1 | Vê tudo o que é público aos compradores, vota em enquetes pela sua unidade. |
| **Inquilino / morador** | E2 | Uso do dia a dia. Não vota. |
| **Síndico e conselho** | E2 | Herdam os poderes da Comissão e ganham os de gestão. |
| **Funcionários** | E2 | Portaria e zeladoria: encomendas, visitantes, chamados atribuídos. |

| Ação | Admin | Comissão / Síndico | Proprietário | Inquilino | Funcionário |
|---|:-:|:-:|:-:|:-:|:-:|
| Aprovar cadastro e vínculo com unidade | ✅ | ✅ | — | — | — |
| Publicar aviso oficial | ✅ | ✅ | — | — | — |
| Criar enquete | ✅ | ✅ | — | — | — |
| Votar em enquete | — | pela sua unidade | ✅ | — | — |
| Publicar documento | ✅ | ✅ | — | — | — |
| Ver documento (RF-31) | todos | todos | público + compradores | público + compradores | público |
| Ver dados de contato de outros moradores | ✅ | ✅ | — | — | — |

## 3. Requisitos funcionais

### 3.1 Unidades e cadastro — E1

| Código | Requisito |
|---|---|
| RF-01 | O sistema traz as **320 unidades** já cadastradas: 5 blocos × 8 pavimentos (térreo + 7) × 8 posições, numeradas `<andar><posição>` (ex.: 502 = 5º andar, posição 02). |
| RF-02 | O administrador pode **editar** blocos, unidades e a que módulo cada bloco pertence, porque a convenção ainda pode mudar o que é "o condomínio" (visão, seção 12). |
| RF-03 | Uma pessoa cria conta informando nome, e-mail e celular, e **pede vínculo** com uma unidade, dizendo se é proprietária. |
| RF-04 | O vínculo só vale depois de **aprovado** pelo administrador ou pela Comissão. Até lá a pessoa vê só os avisos públicos. |
| RF-05 | Uma unidade pode ter mais de um proprietário (ex.: casal que comprou junto). |
| RF-06 | A pessoa pode editar os próprios dados e **excluir a própria conta** (RNF de LGPD). |
| RF-07 | O administrador vê a lista de unidades com e sem cadastro, para saber a adesão. |

### 3.2 Avisos — E1

| Código | Requisito |
|---|---|
| RF-10 | Comissão e administrador publicam avisos com título, texto, anexos (imagem ou PDF) e destino: todos, um bloco ou um módulo. |
| RF-11 | Ao publicar, quem tem vínculo aprovado no destino recebe **notificação** no celular e por e-mail. |
| RF-12 | Um aviso pode ser **fixado** no topo do mural. |
| RF-13 | O mural mostra os avisos do mais novo para o mais antigo, com busca por texto. |
| RF-14 | Aviso publicado **não é apagado**: pode ser corrigido (fica o histórico da edição) ou arquivado. O oficial precisa ser rastreável (objetivo O1). |
| RF-15 | Quem publica vê quantas pessoas leram o aviso. |

### 3.3 Enquetes — E1

| Código | Requisito |
|---|---|
| RF-20 | Comissão e administrador criam enquetes com pergunta, opções (escolha única ou múltipla), prazo e destino. |
| RF-21 | **Um voto por unidade** (RN-01), dado por qualquer proprietário vinculado a ela. |
| RF-22 | O voto pode ser trocado até o prazo terminar. |
| RF-23 | Quem cria escolhe se o resultado aparece durante a votação ou só no fim. |
| RF-24 | O resultado mostra votos por opção, unidades que votaram e participação (% das unidades). |
| RF-25 | Enquete encerrada fica guardada com o resultado, sem poder ser alterada. |

### 3.4 Documentos — E1

| Código | Requisito |
|---|---|
| RF-30 | Comissão e administrador publicam documentos (PDF ou imagem) com título, categoria e data. Categorias iniciais: convenção, regimento, atas, contratos, obra, outros. |
| RF-31 | Cada documento tem um nível de acesso: **público** (qualquer visitante), **compradores** (vínculo aprovado) ou **gestão** (Comissão / síndico / conselho). |
| RF-32 | Uma nova versão de documento não apaga a anterior: o histórico de versões fica disponível. |
| RF-33 | Publicar documento gera aviso automático (RF-11) se quem publica marcar essa opção. |

### 3.5 Reservas — E2

| Código | Requisito |
|---|---|
| RF-40 | O síndico cadastra as **áreas reserváveis** com nome, capacidade, horários permitidos e regras. A lista não fica fixa no código (visão, seção 2). |
| RF-41 | O morador vê a agenda de cada área e reserva um horário livre. |
| RF-42 | O sistema impede reserva em conflito e aplica as regras da área (antecedência mínima e máxima, limite por unidade). |
| RF-43 | A reserva pode exigir aprovação do síndico, conforme a área. |
| RF-44 | O morador cancela a própria reserva dentro do prazo da regra. |

### 3.6 Chamados e garantia da construtora — E2

| Código | Requisito |
|---|---|
| RF-50 | O morador abre um chamado com descrição, local (unidade ou área comum) e fotos. |
| RF-51 | O chamado tem estados: aberto → em andamento → resolvido / recusado, e quem abriu acompanha cada mudança. |
| RF-52 | O síndico atribui chamados a funcionários. |
| RF-53 | Um chamado pode ser marcado como **garantia da construtora**: entra na lista de pendências com a construtora, com a data em que foi comunicado e o prazo de resposta. |
| RF-54 | O sistema avisa quando a garantia de 60 meses estiver perto de acabar. |

### 3.7 Encomendas e visitantes — E2

| Código | Requisito |
|---|---|
| RF-60 | A portaria registra uma encomenda para uma unidade, e os moradores dela são notificados. |
| RF-61 | A retirada é confirmada pela portaria, com nome de quem retirou. |
| RF-62 | O morador pré-autoriza visitantes e prestadores com nome e período. |
| RF-63 | A portaria consulta as autorizações do dia e registra entrada. |

### 3.8 Financeiro — E3

| Código | Requisito |
|---|---|
| RF-70 | O síndico registra a taxa de cada mês por unidade e marca o pagamento. **O sistema não processa pagamento** (visão, seção 7). |
| RF-71 | O sistema mostra inadimplência por unidade e no total. |
| RF-72 | O síndico registra receitas e despesas com categoria e comprovante. |
| RF-73 | O balancete mensal é publicado no Portal para os proprietários. |
| RF-74 | Cada proprietário vê a situação da própria unidade. A lista de quem deve só é vista pela gestão (RN-04). |

### 3.9 Assembleias — E3

| Código | Requisito |
|---|---|
| RF-80 | A gestão cria a assembleia com pauta, data e local, e o sistema envia a convocação. |
| RF-81 | Lista de presença por unidade. |
| RF-82 | A ata é publicada como documento (RF-30). |

### 3.10 Operação — E3

| Código | Requisito |
|---|---|
| RF-90 | Cadastro de itens de manutenção preventiva com periodicidade e responsável. Itens iniciais tirados do memorial: elevadores, estações de bombas, reservatórios, central de gás, portões, interfone. |
| RF-91 | Alerta antes do vencimento de cada manutenção. Registro da manutenção feita, com comprovante. |
| RF-92 | Tarefas e escala dos funcionários. |
| RF-93 | Achados e perdidos: a portaria registra o item com foto, e o dono reivindica. |
| RF-94 | Cadastro de veículos e pets por unidade. |

## 4. Regras de negócio

| Código | Regra |
|---|---|
| RN-01 | **Enquete vale um voto por unidade**, não por pessoa. É como o condomínio decide, e evita que unidade com mais cadastros pese mais. |
| RN-02 | Só **proprietário** vota. Inquilino não vota (visão, seção 5). |
| RN-03 | Enquete é **consulta**, sem valor legal. O sistema mostra isso em toda enquete. |
| RN-04 | Dado de um morador (contato, situação financeira) só é visto pelo próprio morador e pela gestão. |
| RN-05 | O que é oficial (aviso, documento, resultado de enquete) não some: corrige-se ou arquiva-se, sempre com histórico. |
| RN-06 | A Comissão de Representantes perde os poderes de gestão quando o síndico eleito assume. Esses poderes passam ao síndico. |

## 5. Requisitos não funcionais

### Uso
| Código | Requisito |
|---|---|
| RNF-01 | Funciona no navegador do celular e do computador e pode ser **instalado** como aplicativo (PWA). |
| RNF-02 | **Usuário leigo:** as tarefas principais (ler aviso, votar, abrir documento) se fazem em no máximo 3 toques a partir da tela inicial, sem treinamento. |
| RNF-03 | Entrar no Portal **sem precisar decorar senha** (ex.: link de acesso por e-mail). A forma exata é decidida na arquitetura. |
| RNF-04 | Acessibilidade WCAG 2.1 nível AA: contraste, texto ampliável, navegação por teclado e leitor de tela. |
| RNF-05 | Interface em português do Brasil. |

### Segurança e LGPD
| Código | Requisito |
|---|---|
| RNF-10 | Coletar **só o dado necessário**. Na E1: nome, e-mail, celular e unidade. **Não** pedir CPF, RG, contrato ou renda. |
| RNF-11 | Cada dado pessoal tem uma finalidade escrita na política de privacidade, que fica visível no Portal antes do cadastro. |
| RNF-12 | O titular pode ver, corrigir e excluir os próprios dados (RF-06). |
| RNF-13 | Permissões verificadas **no servidor**, não só na tela. |
| RNF-14 | Toda ação de gestão (aprovar, publicar, editar, arquivar) fica registrada com quem fez e quando. |
| RNF-15 | Conexão sempre criptografada (HTTPS). |
| RNF-16 | Dados reais nunca no repositório. Desenvolvimento e testes com dados fictícios. |

### Operação
| Código | Requisito |
|---|---|
| RNF-20 | **Custo de infraestrutura R$ 0**, dimensionado para 320 unidades e até ~1.000 pessoas cadastradas. |
| RNF-21 | Backup automático do banco, com teste de restauração antes de ir para produção. |
| RNF-22 | Arquivos (PDFs, fotos) guardados fora do banco, com limite de tamanho por envio. |
| RNF-23 | Tela principal carrega em menos de 3 segundos num celular comum com 4G. |

## 6. O que a E1 entrega, em uma frase

> Um comprador do Capibaribe Prime entra no Portal pelo celular, se cadastra na sua unidade,
> é aprovado, e a partir daí recebe os avisos oficiais, vota nas enquetes pela sua unidade e
> encontra os documentos da obra, tudo num lugar que não se perde como o grupo de WhatsApp.

Requisitos da E1: RF-01 a RF-33, RN-01 a RN-06 e todos os RNF.

## 7. Rastreabilidade com os objetivos

| Objetivo (visão) | Atendido por |
|---|---|
| O1 · canal oficial | Avisos (3.2), documentos (3.4), RN-05 |
| O2 · transparência financeira | Financeiro (3.8) |
| O3 · menos trabalho do síndico | Reservas (3.5), chamados (3.6), encomendas (3.7), operação (3.10) |
| O4 · portfólio | Este processo inteiro: requisitos rastreáveis, LGPD desde o início, entregas em produção |

## 8. Questões em aberto

- [ ] Quem aprova cadastros na E1, se a Comissão de Representantes não existir ou não quiser usar o Portal? (padrão: o administrador)
- [ ] O destino "módulo" (RF-10) só faz sentido se a convenção separar o Módulo I dos blocos 04 e 05. Confirmar na certidão da convenção.
