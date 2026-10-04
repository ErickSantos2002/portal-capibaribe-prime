# 01 · Documento de Visão — Portal Capibaribe Prime

| | |
|---|---|
| **Status** | Rascunho v0.3 |
| **Autor** | Erick Santos Dantas |
| **Criado em** | 24/09/2026 |
| **Atualizado em** | 02/10/2026: fatos do condomínio conferidos nos documentos; acesso por conta de unidade |
| **Próximo documento** | `02-requisitos.md` |

---

## 1. Resumo

O **Portal Capibaribe Prime** é um sistema web, instalável no celular (PWA), que concentra a
vida do condomínio **Capibaribe Prime Residence** num lugar só: avisos, reservas, chamados,
encomendas, visitantes, documentos, prestação de contas e o controle de pagamentos da taxa
condominial. É usado por moradores, síndico, conselho e funcionários.

O condomínio está **em construção**. O prazo contratual de obra termina em **24/01/2028**,
prorrogável uma vez por até 6 meses, e a construtora tem mais 60 dias para entregar as chaves.
A intenção é que o sistema exista **antes** da entrega, para ser usado desde a primeira
assembleia, e já na fase de obra, pela Comissão de Representantes (seção 4).

## 2. O condomínio

Fatos tirados de documentos oficiais e do material de venda. Os documentos ficam com o autor,
**fora do repositório**: o contrato tem dado pessoal, e o material de venda é da construtora.

| Fato | Fonte |
|---|---|
| **Capibaribe Prime Residence**: 5 torres, **320 unidades**, térreo + 7 andares, 8 apartamentos por andar (64 por torre), elevador | E-book da construtora |
| Endereço: Av. Ministro Mário Andreazza, s/n, Várzea, Recife/PE | Matrícula 13.674, 7º RI do Recife |
| Faz parte do **Reserva do Capibaribe**, um bairro planejado com vários condomínios. A 1ª etapa tem 3 empreendimentos e 14 blocos, cada empreendimento com o **próprio lazer** | E-book |
| O **Módulo I** (subcondomínio Capibaribe Prime, blocos 01, 02 e 03) tem **192 unidades** e é financiado pela Caixa no Minha Casa, Minha Vida | Contrato Caixa, letra D1 |
| Apartamentos de 2 quartos (43,29 m²) ou 2 quartos com suíte (46,45 m²), todos com varanda | E-book, matrícula |
| Vagas **rotativas, sem número**, por ordem de chegada, uma por unidade | Matrícula, e-book |
| A **convenção de condomínio já está registrada** (RA nº 939, Livro 3, 7º RI), retificada em nov/2024 | Matrícula, AV-03 e AV-07 |
| **Gás coletivo sem medição individual** | Memorial descritivo |
| Garantia pós-entrega da construtora: seguro de **60 meses** a partir do Habite-se | Contrato, item 23.10 |

**Áreas comuns.** O memorial descritivo, que é o documento técnico registrado, lista: guarita e
zeladoria, salão de festas e salas multiuso com copa, **2 churrasqueiras**, piscina com deck e
ducha, minicampo, bicicletário, redário/mirante, depósito de lixo e estacionamento. O e-book
promete ainda brinquedoteca, coworking, espaço fitness, pet place, playground e pista de cooper,
mas avisa que as imagens são ilustrativas. **Só a entrega vai dizer o que existe de fato**, por
isso a lista de áreas não pode ficar fixa no sistema.

**Evidência de interesse:** a escolha do nome foi feita por enquete no grupo de WhatsApp dos
futuros moradores, com **45 votos** (Portal Capibaribe Prime: 35 · Capibaribe Connect: 9 ·
Prime Hub: 1 · Meu Capibaribe: 0). Os moradores já participam antes de existir uma linha de
código. E a própria enquete é um exemplo do problema: aconteceu num canal sem registro, que
vai se perder no histórico do grupo.

## 3. O problema

Sem um sistema, a informação do condomínio se espalha e se perde. Num condomínio de 320
unidades, isso aparece em quatro frentes, e todas pesam:

1. **Tudo espalhado.** O que importa fica dividido entre WhatsApp, papel, planilha e boca a
   boca. Nada tem registro, nada é rastreável e ninguém sabe onde achar as coisas.
2. **Falta de transparência.** O morador não enxerga para onde vai o dinheiro nem o que a
   gestão está fazendo, e isso gera desconfiança.
3. **Comunicação caótica.** Aviso importante se perde no grupo lotado, e reclamação vira
   discussão pública em vez de chamado.
4. **Trabalho manual do síndico.** Reserva, pagamento e documento são controlados na mão, e
   isso consome horas.

Um prédio **novo** tem uma dor a mais: nos primeiros anos aparecem os defeitos de construção, e
cobrar a construtora dentro da garantia exige registro organizado, com data, foto e
acompanhamento.

## 4. Objetivos

| # | Objetivo | Tipo |
|---|---|---|
| O1 | Ser **o** canal oficial do condomínio: o que não está no Portal, não é oficial | Uso |
| O2 | Dar transparência financeira ao morador (o que entra, o que sai, quem deve) | Uso |
| O3 | Tirar o trabalho repetitivo do síndico (reservas, controle de pagamento, encomendas) | Uso |
| O4 | Servir de **projeto de portfólio completo**, com planejamento, documentação, segurança e sistema em produção com usuários reais | Pessoal |

**Não é objetivo** virar produto comercial nem ser vendido a outros condomínios.

## 5. Usuários (perfis)

| Perfil | Quem é | O que faz no sistema |
|---|---|---|
| **Proprietário** | Dono da unidade, more ou não nela | Tudo o que o morador faz, mais: responde pela taxa e tem direito a voto em assembleia |
| **Inquilino / morador** | Quem vive na unidade sem ser dono (inclui familiares) | Uso do dia a dia: reservas, chamados, encomendas, visitantes, avisos |
| **Síndico e conselho** | Gestão eleita em assembleia | Pagamentos, prestação de contas, documentos oficiais, avisos, aprovações |
| **Funcionários** | Portaria, zeladoria, limpeza | Encomendas, visitantes, chamados atribuídos, tarefas do dia |
| **Comissão** *(só na fase de obra)* | Hoje, os **5 administradores do grupo de WhatsApp** dos compradores. A Lei 4.591/64 exige uma Comissão de Representantes durante a obra; se esse grupo é ela formalmente, não importa para o sistema | Avisos, enquetes e documentos da obra |

> **Decisão (revista em 02/10/2026):** o acesso é por **uma conta por unidade**, compartilhada
> pela família ou por quem mora lá. Quem está com a conta vota pela unidade, com o consentimento
> implícito do proprietário. Proprietário e inquilino continuam sendo papéis diferentes na lei
> (quem responde pela taxa), mas o sistema não os separa por enquanto. Detalhes e riscos em
> `02-requisitos.md`, seção 2.

## 6. Escopo — o que o sistema faz

As funções abaixo entram **em algum momento**. A ordem fica no roadmap.

**Comunicação**
- Mural de avisos oficiais
- Enquetes (consulta sem valor legal)
- Assembleias: pauta, convocação, presença e ata
- Notificações no celular

**Dia a dia**
- Reservas de áreas comuns (salão de festas, churrasqueiras e o que mais for entregue). A
  lista de áreas é um cadastro editável pelo síndico, não fica fixa no código.
- Chamados / ocorrências, com foto e acompanhamento
- Encomendas: a portaria registra e o morador é avisado
- Visitantes e prestadores pré-autorizados

**Administrativo e financeiro**
- Cadastro completo: unidades (torre, andar, posição), moradores, veículos, pets
- Controle de pagamentos da taxa condominial (quem pagou, inadimplência)
- Prestação de contas: receitas, despesas, balancete
- Documentos: convenção, regimento, atas, contratos, com permissão de acesso

**Operação**
- Manutenção preventiva com alerta de vencimento. Itens conhecidos pelo memorial: elevadores
  das 5 torres, 2 estações de bombas, reservatórios, central de gás, portões, interfone e
  impermeabilização.
- **Garantia da construtora:** registro dos defeitos de construção encontrados, com envio e
  acompanhamento junto à construtora, dentro dos 60 meses de garantia
- Tarefas e escala dos funcionários
- Achados e perdidos

## 7. Fora do escopo

| Item | Por quê |
|---|---|
| **Pagar a taxa pelo sistema** (boleto, PIX, cartão) | Envolve banco, dinheiro de terceiros e responsabilidade legal. O sistema **registra** o pagamento, não o processa. |
| **Acesso de administradora** | Não há administradora definida. Se houver, a decisão é revista. |
| **Votação com valor legal** em assembleia | Tem exigências jurídicas próprias. A decidir depois; enquetes cobrem a consulta informal. |
| **Classificados** entre moradores | Avaliado e descartado. |
| **Controle de vagas por unidade** | As vagas são rotativas e sem número, então não há o que controlar. |
| **Uso comercial / multi-condomínio** | Não é objetivo (ver seção 4). |

## 8. Restrições

- **Custo zero.** Nenhuma infraestrutura paga. A hospedagem prevista é a Vercel, e banco e
  arquivos em serviços com plano gratuito. Os limites dos planos serão conferidos na
  documentação oficial ao escrever o documento de arquitetura, considerando **320 unidades**.
- **Sem infraestrutura da Health & Safety.** Projeto pessoal, com contas pessoais.
- **Web + celular com um código só**, via PWA (instalável, com notificação).
- **LGPD.** O sistema guarda dado pessoal de terceiros (nome, contato, placa, documentos).
  Cada dado sensível é justificado antes de entrar. Dados reais **nunca** vão para o
  repositório; desenvolvimento e testes usam dados fictícios.
- **Usuário leigo.** Morador de qualquer idade precisa usar sem treinamento.

## 9. Premissas

- O Erick vai se candidatar a síndico ou ao conselho, o que dá acesso para implantar o sistema.
- Antes disso, a **Comissão de Representantes** da obra é uma porta de entrada: é um órgão que
  já deve existir e que precisa se comunicar com centenas de compradores.
- Os futuros moradores já estão reunidos num grupo de WhatsApp, que serve de canal de validação.
- Se o condomínio não adotar o sistema, ele ainda cumpre o objetivo O4 (portfólio).

## 10. Riscos

| Risco | Impacto | Mitigação |
|---|---|---|
| Escopo grande demais e o projeto parar no meio | Alto | Entregar em módulos que funcionam sozinhos, cada fase útil por si |
| Gestão eleita ou administradora não adotar | Médio | Candidatura do Erick; sistema pronto e demonstrável antes da 1ª assembleia |
| Limites do plano gratuito estourarem | Médio | Conferir limites no desenho da arquitetura; guardar arquivos pesados fora do banco |
| Vazamento de dado pessoal | Alto | LGPD desde o desenho, permissões por perfil, dados fictícios no desenvolvimento |
| Moradores não aderirem e continuarem no WhatsApp | Médio | Envolver desde já (enquetes, testes); regra de que o oficial está no Portal |
| O que for entregue diferir do material de venda (áreas, módulos, prazos) | Médio | Áreas e unidades como cadastro editável; nada sobre o prédio fixo no código |

## 11. Critérios de sucesso

*Base: 320 unidades (seção 12). As metas em números estão em `07-roadmap.md`, seção 6.*

- X% das unidades com pelo menos um morador cadastrado nos primeiros 3 meses
- Todas as reservas de áreas comuns feitas pelo sistema
- Prestação de contas mensal publicada no Portal
- Custo de infraestrutura: R$ 0

## 12. Questões em aberto

- [x] ~~Quantas unidades tem o condomínio?~~ 320 no Capibaribe Prime, 192 no Módulo I (seção 2).
- [x] ~~O que a convenção cobre?~~ A certidão não foi obtida (02/10/2026). **Decisão:** o sistema
      atende o Capibaribe Prime inteiro, **320 unidades em 5 blocos**, porque o lazer é do
      empreendimento todo. Blocos e unidades são editáveis (RF-02) se a convenção disser outra coisa.
- [ ] Quais áreas comuns serão entregues de fato (memorial × e-book)?
- [x] ~~A Comissão existe?~~ Sim: os 5 administradores do grupo de WhatsApp (seção 5).
- [ ] Haverá administradora? (sem a convenção, só se sabe após a entrega)
- [ ] Votação com valor legal: entra ou não?

---

### Sequência de documentos

1. **Visão** ← este
2. Requisitos (funcionais e não funcionais)
3. Histórias de usuário / casos de uso
4. Modelo de dados
5. Arquitetura + ADRs (registros de decisão)
6. Protótipo de telas
7. Roadmap
