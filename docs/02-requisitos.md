# 02 · Requisitos — Portal Capibaribe Prime

| | |
|---|---|
| **Status** | v0.2 — conta por unidade (decisão de 02/10/2026) |
| **Autor** | Erick Santos Dantas |
| **Criado em** | 02/10/2026 |
| **Base** | `01-visao.md` v0.2 |
| **Próximo documento** | `03-historias.md` |

---

## 1. Como ler este documento

Cada requisito tem um código e uma **entrega** (quando entra):

| Entrega | Nome | Quando | Para quê |
|---|---|---|---|
| **E1** | Fase de obra | 2026–2027 | Comunicação oficial entre compradores, Comissão e (depois) gestão. Útil antes da entrega das chaves. |
| **E2** | Mudança e dia a dia | Perto da entrega (2028) | Reservas, chamados, encomendas, visitantes e garantia da construtora |
| **E3** | Gestão | Após a 1ª assembleia | Financeiro, assembleias, manutenção, funcionários |

> **Decisão (02/10/2026):** a E1 é a comunicação da fase de obra. Motivo: é a única parte que
> tem uso real antes de 2028, tira o grupo de WhatsApp do centro e dá visibilidade ao projeto
> antes da eleição de síndico.

Códigos: **RF** = requisito funcional (o que o sistema faz) · **RNF** = não funcional (como ele
se comporta) · **RN** = regra de negócio (regra do condomínio que o sistema respeita).

Cada entrega precisa funcionar **sozinha**. Se o projeto parar depois da E1, a E1 continua útil.

## 2. Perfis e permissões

> **Decisão (02/10/2026): uma conta por unidade.** A família inteira usa a mesma conta. O login
> segue um padrão que se explica numa frase no grupo, e a senha inicial é igual para todas as
> unidades, com troca obrigatória no primeiro acesso. **Motivo:** dispensa aprovar e conferir
> centenas de pessoas uma a uma. **Risco aceito:** quem souber o padrão pode ativar a conta de
> outra unidade antes do dono; isso é tratado com detecção e reset rápido (RF-04 a RF-07), não
> com burocracia na entrada. Pode ser revisto se os moradores pedirem.

Há dois tipos de conta:

- **Conta da unidade** (compartilhada pela família ou por quem mora lá): é quem vota e recebe avisos.
- **Conta pessoal de gestão** (Administrador, Comissão, depois síndico/conselho): individual,
  separada da conta da unidade. Assim o poder de publicar fica com a pessoa, não com a família.

| Perfil | Entra em | Resumo |
|---|---|---|
| **Administrador do sistema** | E1 | Mantém o Portal funcionando: reseta contas de unidade, gerencia perfis. Na E1 é o Erick. |
| **Comissão** | E1 | Os 5 administradores do grupo de WhatsApp dos compradores. Publicam avisos e documentos da obra e criam enquetes. Deixa de existir após a entrega. |
| **Unidade** | E1 | Conta compartilhada da unidade. Vê o que é dos compradores, vota em enquetes. Quem estiver com a conta vota pela unidade, com o consentimento implícito do proprietário (RN-02). |
| **Síndico e conselho** | E2 | Herdam os poderes da Comissão e ganham os de gestão. |
| **Funcionários** | E2 | Portaria e zeladoria: encomendas, visitantes, chamados atribuídos. |

| Ação | Admin | Comissão / Síndico | Unidade | Funcionário |
|---|:-:|:-:|:-:|:-:|
| Resetar conta de unidade | ✅ | — | — | — |
| Publicar aviso oficial | ✅ | ✅ | — | — |
| Criar enquete | ✅ | ✅ | — | — |
| Votar em enquete | — | — (vota pela conta da unidade) | ✅ | — |
| Publicar documento | ✅ | ✅ | — | — |
| Ver documento (RF-31) | todos | todos | público + compradores | público |
| Ver dados de contato das unidades | ✅ | ✅ | — | — |

## 3. Requisitos funcionais

### 3.1 Unidades e cadastro — E1

| Código | Requisito |
|---|---|
| RF-01 | O sistema traz as **320 unidades** já cadastradas: 5 blocos × 8 pavimentos (térreo + 7) × 8 posições, numeradas `<andar><posição>` (ex.: 502 = 5º andar, posição 02). |
| RF-02 | O administrador pode **editar** blocos e unidades. O sistema parte de 320 unidades sem ter visto a convenção (visão, seção 12), então precisa aceitar correção sem mexer em código. |
| RF-03 | Cada unidade já nasce com **uma conta**. Login = **bloco + apartamento**, sem separador: Bloco 1, apto 101 → `1101`; térreo: Bloco 1, apto 007 → `1007`. O campo aceita também `1-101` e `01101`. Senha inicial de todas: **`mudar123`**. |
| RF-04 | No **primeiro acesso**, a conta obriga a trocar a senha e pede o nome de um responsável e um celular. E-mail é **opcional**: quem informar pode recuperar a senha sozinho. |
| RF-05 | Depois de **5 tentativas erradas**, o login daquela unidade fica bloqueado por 15 minutos. |
| RF-06 | O administrador vê um **painel de ativação**: cada unidade com ativada / não ativada, data do primeiro acesso e responsável informado. Serve para medir a adesão e para perceber conta tomada. |
| RF-07 | O administrador pode **resetar a conta de uma unidade**: a senha volta para `mudar123`, os dados de contato são apagados e a conta volta a "não ativada". Os votos já dados pela unidade continuam valendo, mas o reset fica registrado (RNF-14). |
| RF-08 | A unidade pode editar os próprios dados e pedir a **exclusão dos dados de contato**. A conta em si não some, porque pertence à unidade, e volta a "não ativada" (LGPD). |
| RF-09 | O administrador e a Comissão têm **contas pessoais**, criadas pelo administrador, separadas das contas das unidades. |

### 3.2 Avisos — E1

| Código | Requisito |
|---|---|
| RF-10 | Comissão e administrador publicam avisos com título, texto, anexos (imagem ou PDF) e destino: todos ou blocos escolhidos. |
| RF-11 | Ao publicar, as unidades do destino recebem **notificação** em todo aparelho em que a conta estiver conectada, e por e-mail quando houver e-mail informado. |
| RF-12 | Um aviso pode ser **fixado** no topo do mural. |
| RF-13 | O mural mostra os avisos do mais novo para o mais antigo, com busca por texto. |
| RF-14 | Aviso publicado **não é apagado**: pode ser corrigido (fica o histórico da edição) ou arquivado. O oficial precisa ser rastreável (objetivo O1). |
| RF-15 | Quem publica vê quantas pessoas leram o aviso. |

### 3.3 Enquetes — E1

| Código | Requisito |
|---|---|
| RF-20 | Comissão e administrador criam enquetes com pergunta, opções (escolha única ou múltipla), prazo e destino. |
| RF-21 | **Um voto por unidade** (RN-01), dado pela conta da unidade. |
| RF-22 | O voto pode ser trocado até o prazo terminar. |
| RF-23 | Quem cria escolhe se o resultado aparece durante a votação ou só no fim. |
| RF-24 | O resultado mostra votos por opção, unidades que votaram e participação (% das unidades). |
| RF-25 | Enquete encerrada fica guardada com o resultado, sem poder ser alterada. |

### 3.4 Documentos — E1

| Código | Requisito |
|---|---|
| RF-30 | Comissão e administrador publicam documentos (PDF ou imagem) com título, categoria e data. Categorias iniciais: convenção, regimento, atas, contratos, obra, outros. |
| RF-31 | Cada documento tem um nível de acesso: **público** (qualquer visitante), **compradores** (conta de unidade ativada) ou **gestão** (Comissão / síndico / conselho). |
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
| RN-01 | **Enquete vale um voto por unidade**, não por pessoa. É como o condomínio decide. Com uma conta por unidade, isso sai naturalmente. |
| RN-02 | **Quem está com a conta da unidade vota por ela.** Se um inquilino ou parente tem a conta, considera-se que o proprietário consentiu. Vale para enquete, que é consulta (RN-03); voto com valor legal, se um dia existir, terá regra própria. |
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
| RNF-03 | Login explicável numa frase no grupo: "seu usuário é o bloco e o apartamento juntos, a senha inicial é mudar123". Senha guardada só como hash (nunca em texto), com mínimo de 8 caracteres na troca e diferente de `mudar123`. |
| RNF-04 | Acessibilidade WCAG 2.1 nível AA: contraste, texto ampliável, navegação por teclado e leitor de tela. |
| RNF-05 | Interface em português do Brasil. |

### Segurança e LGPD
| Código | Requisito |
|---|---|
| RNF-10 | Coletar **só o dado necessário**. Na E1: nome de um responsável, celular e, opcionalmente, e-mail, por unidade. **Não** pedir CPF, RG, contrato ou renda. |
| RNF-11 | Cada dado pessoal tem uma finalidade escrita na política de privacidade, que fica visível no Portal antes do cadastro. |
| RNF-12 | O titular pode ver, corrigir e excluir os próprios dados (RF-08). |
| RNF-13 | Permissões verificadas **no servidor**, não só na tela. |
| RNF-14 | Toda ação de gestão (resetar conta, publicar, editar, arquivar) fica registrada com quem fez e quando. |
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

> Um comprador do Capibaribe Prime entra no Portal pelo celular com o número do bloco e do
> apartamento, troca a senha, e a partir daí recebe os avisos oficiais, vota nas enquetes e
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

Nenhuma bloqueando a E1. A convenção não foi obtida; a decisão de seguir com 320 unidades está
na visão, seção 12.
