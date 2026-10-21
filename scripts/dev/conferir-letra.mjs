// Conferência da "letra que cresce" (M5, spec docs/superpowers/specs/m5-letra.md): abre as telas
// do Portal num Chrome headless PRÓPRIO (playwright-core, devDependency de web/; nunca o MCP,
// porque vários agentes rodam ao mesmo tempo), em cada largura e em cada tamanho de fonte padrão
// do navegador (16 px = 100 %, 24 px = 150 %, 32 px = 200 %, como a opção "Tamanho da fonte" do
// Chrome e do Firefox), tira um print da página inteira e mede sozinho:
//   - rolagem lateral da página (scrollWidth > clientWidth);
//   - elemento que passa da borda direita da tela;
//   - texto cortado (overflow escondido com conteúdo maior que a caixa);
//   - alvo de toque com menos de 44 px de altura ou largura (link no meio da frase não conta,
//     como na WCAG 2.5.8);
//   - ícone encolhido: SVG (ou o pontinho redondo desenhado em CSS) mais estreito ou mais baixo
//     que o desenho pede, o que acontece quando ele é item de flex e o texto ao lado quebra;
//   - palavra de até 12 letras quebrada no meio (as letras dela em duas linhas);
//   - se a letra cresceu: o tamanho mediano e o menor do texto visível;
//   - a barra do celular com a bola do Menu (spec 2026-10-18-navegacao-bola-design.md): a altura
//     total (do topo da bola ao fim da barra, sem a safe-area) acima de 104 px, rótulo dela que
//     não cabe, e o fim do conteúdo escondido atrás da barra (rolando a página até o fim).
//
// Precisa do Portal no ar com dados (scripts/dev/ambiente-conferencia.sh) e do Chrome do sistema
// (/usr/bin/google-chrome-stable, ou CHROME=<caminho>). Uso, da raiz do repositório:
//   node scripts/dev/conferir-letra.mjs --base http://localhost:5170 --tarefa base --semear
//   node scripts/dev/conferir-letra.mjs --base http://localhost:5171 --tarefa g1 --grupo G1
//   node scripts/dev/conferir-letra.mjs ... --telas entrar,mural --larguras 360 --fontes 32
// Opções: --grupo comum|G1|G2|G3|indicacoes|classificados (só as telas do grupo; repetível com vírgula), --telas <nomes>,
// --larguras 360,1280[,1366x768], --fontes 16,24,32, --temas claro[,escuro], --saida <pasta>,
// --semear (cria, uma vez, os avisos, a enquete, os documentos, os anexos e as indicações fictícias
// que as telas usam; os arquivos vão para o bucket de mentira da api-conferencia.py), --listar.
// Rolagem dentro de um elemento (a faixa de categorias das indicações): o que passa da borda dentro
// de um ancestral com overflow-x auto/scroll que cabe na tela sai de "fora da tela" e vai para
// "rola dentro" (informativo, não conta). A rolagem da página continua sendo problema.
// Saída: <saida>/<tela>-<largura>-<fonte>[-escuro].png, resultado.json e resumo.txt
// (padrão: /tmp/portal-letra-<tarefa>/). Sai com código 1 se houver algum problema.
import { createRequire } from 'node:module'
import { deflateSync } from 'node:zlib'
import { cpSync, existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { homedir, tmpdir } from 'node:os'
import { join } from 'node:path'

const exigir = createRequire(new URL('../../web/package.json', import.meta.url))
const { chromium } = exigir('playwright-core')

// ---------- opções ----------
const args = process.argv.slice(2)
const opcao = (nome, padrao) => {
  const i = args.indexOf(`--${nome}`)
  return i >= 0 && args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : padrao
}
const lista = (texto) => texto.split(',').map((s) => s.trim()).filter(Boolean)
const BASE = opcao('base', 'http://localhost:5170').replace(/\/$/, '')
const TAREFA = opcao('tarefa', 'local')
const SAIDA = opcao('saida', `/tmp/portal-letra-${TAREFA}`)
// Cada largura pode levar a altura (`1366x768`); sem ela, 780 no celular e 900 no computador.
const LARGURAS = lista(opcao('larguras', '360,1280'))
const janelaDe = (rotulo) => {
  const [l, a] = rotulo.split('x').map(Number)
  return { width: l, height: a || (l < 900 ? 780 : 900) }
}
const FONTES = lista(opcao('fontes', '16,24,32')).map(Number)
const TEMAS = lista(opcao('temas', 'claro'))
const SENHA = 'mudar123'
// Dados fictícios de semente fixa (api/app/servicos/dados_ficticios.py): 1002 é o admin,
// 1003 é da Comissão, 1101 é um morador comum já ativado.
// `novo`: uma unidade ainda não ativada (a semente acha a primeira), que entra com a senha
// inicial e cai na troca obrigatória do primeiro acesso.
const QUEM = { admin: '1002', comissao: '1003', morador: '1101', novo: null }
// O R2 fictício dos links assinados (scripts/dev/api-conferencia.py): o Chrome pede o arquivo
// nesse endereço (a CSP de produção libera *.r2.cloudflarestorage.com) e a rota abaixo busca o
// conteúdo no bucket de mentira da API.
const R2_FICTICIO = 'https://conferencia.r2.cloudflarestorage.com/portal-arquivos/'
const NO_BUCKET = (url) => `${BASE}/api/_conferencia/bucket/${url.slice(R2_FICTICIO.length).split('?')[0]}`
// iPhone com o Safari, para o passo a passo de "Receber os avisos" (o aparelho é lido do agente).
const AGENTE_IPHONE =
  'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1'

// ---------- as telas ----------
// grupo: quem converte o CSS dela (plano docs/superpowers/plans/m5-letra.md). `quem`: anonimo,
// morador, admin ou novo. `{aviso}`, `{fixado}`, `{enquete}`, `{anexos}`, `{documento}` e
// `{aviso_documento}` viram os ids da semente. `iphone`: a página se apresenta como Safari do iPhone.
const TELAS = [
  { nome: 'entrar', grupo: 'G3', quem: 'anonimo', caminho: '/entrar' },
  { nome: 'privacidade', grupo: 'G3', quem: 'anonimo', caminho: '/privacidade' },
  { nome: 'minha-unidade', grupo: 'G3', quem: 'morador', caminho: '/minha-unidade' },
  { nome: 'primeiro-acesso', grupo: 'G3', quem: 'novo', caminho: '/primeiro-acesso' },
  { nome: 'esqueci-a-senha', grupo: 'G3', quem: 'anonimo', caminho: '/esqueci-a-senha' },
  { nome: 'mural', grupo: 'G1', quem: 'morador', caminho: '/avisos' },
  { nome: 'aviso', grupo: 'G1', quem: 'morador', caminho: '/avisos/{aviso}' },
  { nome: 'aviso-fixado', grupo: 'G1', quem: 'morador', caminho: '/avisos/{fixado}' },
  { nome: 'aviso-anexos', grupo: 'G1', quem: 'morador', caminho: '/avisos/{anexos}' },
  {
    nome: 'foto-grande',
    grupo: 'G1',
    quem: 'morador',
    caminho: '/avisos/{anexos}',
    depois: async (p) => {
      await p.getByRole('button', { name: /Ver a foto 1 de/ }).click()
      await p.getByRole('dialog').locator('img').waitFor()
      await p.waitForTimeout(300)
    },
  },
  { nome: 'novo-aviso', grupo: 'G1', quem: 'admin', caminho: '/avisos/novo' },
  { nome: 'quem-leu', grupo: 'G1', quem: 'admin', caminho: '/avisos/{aviso}/leitura' },
  { nome: 'documentos', grupo: 'G2', quem: 'morador', caminho: '/documentos' },
  { nome: 'documentos-publicos', grupo: 'G2', quem: 'anonimo', caminho: '/documentos/publicos' },
  { nome: 'documento', grupo: 'G2', quem: 'morador', caminho: '/documentos/{documento}' },
  { nome: 'documento-gestao', grupo: 'G2', quem: 'admin', caminho: '/documentos/{documento}' },
  { nome: 'aviso-documento', grupo: 'G2', quem: 'morador', caminho: '/avisos/{aviso_documento}' },
  { nome: 'novo-documento', grupo: 'G2', quem: 'admin', caminho: '/documentos/novo' },
  { nome: 'receber-avisos', grupo: 'G2', quem: 'morador', caminho: '/receber-avisos' },
  { nome: 'receber-avisos-iphone', grupo: 'G2', quem: 'morador', caminho: '/receber-avisos', iphone: true },
  {
    nome: 'o-que-mudou',
    grupo: 'G2',
    quem: 'morador',
    caminho: '/minha-unidade',
    depois: async (p) => {
      await p.getByRole('button', { name: /Versão \d/ }).first().click()
      await p.waitForTimeout(300)
    },
  },
  { nome: 'enquetes', grupo: 'G3', quem: 'morador', caminho: '/enquetes' },
  { nome: 'enquete', grupo: 'G3', quem: 'morador', caminho: '/enquetes/{enquete}' },
  { nome: 'nova-enquete', grupo: 'G3', quem: 'admin', caminho: '/enquetes/nova' },
  { nome: 'votantes', grupo: 'G3', quem: 'admin', caminho: '/enquetes/{enquete}/votantes' },
  { nome: 'painel', grupo: 'G3', quem: 'admin', caminho: '/unidades' },
  // Navegação com a bola: a folha do Menu aberta, para o morador e para a gestão.
  {
    nome: 'menu-aberto',
    grupo: 'comum',
    quem: 'morador',
    caminho: '/avisos',
    depois: async (p) => {
      // No computador não há bola nem folha: fica o print da tela, sem abrir nada.
      const bola = p.getByRole('button', { name: 'Menu' })
      if (!(await bola.isVisible())) return
      await bola.click()
      await p.getByRole('dialog').waitFor()
      // O mouse sai de cima da folha: a linha que passou por baixo dele na animação ficava realçada.
      await p.mouse.move(0, 0)
      await p.waitForTimeout(400)
    },
  },
  {
    nome: 'menu-aberto-gestao',
    grupo: 'comum',
    quem: 'admin',
    caminho: '/unidades',
    depois: async (p) => {
      // No computador não há bola nem folha: fica o print da tela, sem abrir nada.
      const bola = p.getByRole('button', { name: 'Menu' })
      if (!(await bola.isVisible())) return
      await bola.click()
      await p.getByRole('dialog').waitFor()
      // O mouse sai de cima da folha: a linha que passou por baixo dele na animação ficava realçada.
      await p.mouse.move(0, 0)
      await p.waitForTimeout(400)
    },
  },
  { nome: 'ficha-unidade', grupo: 'G3', quem: 'admin', caminho: '/unidades/1101' },
  { nome: 'historico', grupo: 'G3', quem: 'admin', caminho: '/historico' },
  // Indicações de serviços (spec de 18/10/2026). `{indicacao}`: o primeiro prestador da semente,
  // com nome longo, um "não recomendo" e um aviso da Comissão.
  { nome: 'indicacoes', grupo: 'indicacoes', quem: 'morador', caminho: '/indicacoes' },
  { nome: 'indicacao', grupo: 'indicacoes', quem: 'morador', caminho: '/indicacoes/{indicacao}' },
  // O formulário da opinião aberto (o 1101 ainda não opinou no primeiro prestador).
  { nome: 'indicacao-opinar', grupo: 'indicacoes', quem: 'morador', caminho: '/indicacoes/{indicacao}?opinar=1' },
  { nome: 'nova-indicacao', grupo: 'indicacoes', quem: 'morador', caminho: '/indicacoes/nova' },
  { nome: 'indicacao-gestao', grupo: 'indicacoes', quem: 'admin', caminho: '/indicacoes/{indicacao}' },
  { nome: 'categorias-servico', grupo: 'indicacoes', quem: 'admin', caminho: '/indicacoes/categorias' },
  // Classificados entre vizinhos (spec de 20/10/2026). `{classificado}`: o primeiro anúncio da
  // semente (do admin), com título longo, 3 fotos e um aviso da Comissão.
  { nome: 'classificados', grupo: 'classificados', quem: 'morador', caminho: '/classificados' },
  { nome: 'classificado', grupo: 'classificados', quem: 'morador', caminho: '/classificados/{classificado}' },
  // O visor de fotos aberto (revisão de UX, 1 e 2: o visor comum dos anexos).
  {
    nome: 'classificado-visor',
    grupo: 'classificados',
    quem: 'morador',
    caminho: '/classificados/{classificado}',
    depois: async (pagina) => {
      await pagina.click('.cla-foto-grande')
      await pagina.waitForSelector('.anexo-visualizador img')
      await pagina.waitForTimeout(300)
    },
  },
  { nome: 'novo-classificado', grupo: 'classificados', quem: 'morador', caminho: '/classificados/novo' },
  // O dono: "Meus anúncios" (com um encerrado) e o próprio anúncio, com as ações.
  { nome: 'meus-classificados', grupo: 'classificados', quem: 'admin', caminho: '/classificados/meus' },
  { nome: 'classificado-dono', grupo: 'classificados', quem: 'admin', caminho: '/classificados/{classificado}' },
  { nome: 'classificado-editar', grupo: 'classificados', quem: 'admin', caminho: '/classificados/{classificado}/editar' },
  // A gestão vendo o anúncio de outra unidade (o da Comissão), com o aviso do admin.
  { nome: 'classificado-gestao', grupo: 'classificados', quem: 'admin', caminho: '/classificados/{classificado_comissao}' },
  { nome: 'categorias-classificado', grupo: 'classificados', quem: 'admin', caminho: '/classificados/categorias' },
]

if (args.includes('--listar')) {
  for (const t of TELAS) console.log(`${t.grupo.padEnd(6)} ${t.nome.padEnd(20)} ${t.caminho} (${t.quem})`)
  process.exit(0)
}

const grupos = lista(opcao('grupo', ''))
const nomes = lista(opcao('telas', ''))
const escolhidas = TELAS.filter(
  (t) => (!grupos.length || grupos.includes(t.grupo)) && (!nomes.length || nomes.includes(t.nome)),
)
if (!escolhidas.length) {
  console.error('nenhuma tela escolhida (veja --listar)')
  process.exit(2)
}
mkdirSync(SAIDA, { recursive: true })

// ---------- navegador ----------
// Um Chrome por tamanho de fonte, com um perfil temporário cujas Preferences têm o "Tamanho da
// fonte" escolhido (webkit.webprefs.default_font_size: o mesmo que a pessoa muda nas
// configurações). O Page.setFontSizes do CDP foi descartado: o print da página inteira o desfaz.
async function abrirChrome(fonte) {
  const perfil = mkdtempSync(join(tmpdir(), `portal-letra-${fonte}-`))
  mkdirSync(join(perfil, 'Default'))
  const prefs = { webkit: { webprefs: { default_font_size: fonte, default_fixed_font_size: Math.round((fonte * 13) / 16) } } }
  writeFileSync(join(perfil, 'Default', 'Preferences'), JSON.stringify(prefs))
  // Hifenização (revisões do M5, U7): o Chrome do Linux baixa os dicionários de hífen como
  // componente, e o perfil temporário nasce sem eles (o hyphens: auto não fazia nada). Copia os
  // do Chrome do sistema, se houver, e deixa o carregador de componentes ligado.
  const hifen = join(homedir(), '.config/google-chrome/hyphen-data')
  if (existsSync(hifen)) cpSync(hifen, join(perfil, 'hyphen-data'), { recursive: true })
  const c = await chromium.launchPersistentContext(perfil, {
    ignoreDefaultArgs: ['--disable-component-update'],
    executablePath: process.env.CHROME ?? '/usr/bin/google-chrome-stable',
    headless: true,
    args: ['--lang=pt-BR'],
    locale: 'pt-BR',
    timezoneId: 'America/Recife',
    viewport: { width: 1280, height: 900 },
  })
  c.perfil = perfil
  // O "R2" dos links assinados: o conteúdo vem do bucket de mentira da API, nunca da internet.
  // A foto do aviso chega por `…/abrir`, que redireciona para o link assinado; o Playwright não
  // intercepta o pedido redirecionado, então a rota segue o redirecionamento aqui mesmo. Qualquer
  // outro pedido ao R2 fictício é buscado no bucket; nunca sai para a rede.
  await c.route(/\/api\/(avisos|documentos)\/\d+\/.*\/abrir(\?|$)/, async (rota) => {
    const ida = await rota.fetch({ maxRedirects: 0 })
    const destino = ida.headers().location
    if (ida.status() !== 302 || !destino?.startsWith(R2_FICTICIO)) return rota.fulfill({ response: ida })
    await rota.fulfill({ response: await rota.fetch({ url: NO_BUCKET(destino), method: 'GET' }) })
  })
  await c.route(`${R2_FICTICIO}**`, async (rota) => {
    await rota.fulfill({ response: await rota.fetch({ url: NO_BUCKET(rota.request().url()) }) })
  })
  return c
}

async function fecharChrome(c) {
  await c.close()
  rmSync(c.perfil, { recursive: true, force: true })
}

// Sai da sessão: sem isso, cada rodada deixa um "aparelho conectado" a mais na conta.
async function sair(c) {
  await c.request.post(`${BASE}/api/acesso/sair`, { headers: { 'X-Portal': '1' } }).catch(() => {})
  await c.clearCookies()
}

async function entrar(c, login) {
  const r = await c.request.post(`${BASE}/api/acesso/entrar`, {
    headers: { 'X-Portal': '1' },
    data: { login, senha: SENHA },
  })
  if (!r.ok()) throw new Error(`entrar como ${login}: ${r.status()} ${await r.text()}`)
}

// ---------- semente ----------
const TITULO_FIXADO = 'Reunião da Comissão de Representantes com a construtora sobre o andamento das obras'
const TITULO_AVISO = 'Vistoria das áreas comuns: horários por bloco e o que levar'
const PERGUNTA = 'Qual horário fica melhor para a próxima assembleia geral extraordinária dos condôminos?'
const TITULO_ANEXOS = 'Fotos da concretagem do Bloco 3 e o relatório da fiscalização'
const TITULO_DOC = 'Relatório mensal de acompanhamento da obra pela Comissão de Representantes'
const TITULO_DOC_PUBLICO = 'Memorial descritivo do empreendimento e especificações das áreas comuns'
const CLASSIFICADO_LONGO = 'Sobra de porcelanato 60x60 acetinado cinza claro, 12 caixas fechadas e argamassa'

// Uma "foto" PNG de verdade (faixas de cor), sem arquivo no repositório.
function fotoPng(largura, altura, cores) {
  const crc = (buf) => {
    let c = ~0
    for (const b of buf) {
      c ^= b
      for (let k = 0; k < 8; k++) c = (c >>> 1) ^ (0xedb88320 & -(c & 1))
    }
    return ~c >>> 0
  }
  const pedaco = (tipo, dados) => {
    const t = Buffer.from(tipo)
    const tam = Buffer.alloc(4)
    tam.writeUInt32BE(dados.length)
    const soma = Buffer.alloc(4)
    soma.writeUInt32BE(crc(Buffer.concat([t, dados])))
    return Buffer.concat([tam, t, dados, soma])
  }
  const cabeca = Buffer.alloc(13)
  cabeca.writeUInt32BE(largura, 0)
  cabeca.writeUInt32BE(altura, 4)
  cabeca[8] = 8 // 8 bits por canal
  cabeca[9] = 2 // RGB
  const linhas = Buffer.alloc((largura * 3 + 1) * altura)
  for (let y = 0; y < altura; y++) {
    const [r, g, b] = cores[Math.floor((y / altura) * cores.length)]
    for (let x = 0; x < largura; x++) linhas.set([r, g, b], y * (largura * 3 + 1) + 1 + x * 3)
  }
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    pedaco('IHDR', cabeca),
    pedaco('IDAT', deflateSync(linhas)),
    pedaco('IEND', Buffer.alloc(0)),
  ])
}
// Indicações (idempotentes pelo telefone: o 409 devolve o id do que já existe).
const INDICACOES = [
  {
    categoria: 'Móveis planejados',
    nome: 'Marcenaria e Móveis Planejados Irmãos Albuquerque de Paulista',
    telefone: '81999990101',
    instagram: '@marcenaria.exemplo',
    recomenda: true,
    comentario: 'Fizeram a cozinha e os armários dos quartos. Pontuais e caprichosos, entregaram no prazo combinado.',
  },
  {
    categoria: 'Eletricista',
    nome: 'Fios & Cia Instalações',
    telefone: '8133330102',
    recomenda: true,
    comentario: ('Instalou o quadro de distribuição e os pontos de tomada da sala e da varanda. ' +
      'Explicou tudo com calma, deixou o serviço limpo e voltou para conferir a ligação do chuveiro. ').repeat(4).slice(0, 500),
  },
  { categoria: 'Diarista', nome: 'Limpeza Pós-Obra Exemplo', telefone: '81999990103', recomenda: false, comentario: null },
]

const PDF = Buffer.from('%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n')

async function semente(semear) {
  const c = await abrirChrome(16)
  await entrar(c, QUEM.admin)
  const api = (metodo, caminho, data) =>
    c.request.fetch(`${BASE}/api${caminho}`, { method: metodo, headers: { 'X-Portal': '1' }, data })
  const avisos = async () => (await (await api('GET', '/avisos')).json()).itens
  const enquetes = async () => (await (await api('GET', '/enquetes')).json()).itens
  const documentos = async () => (await (await api('GET', '/documentos')).json()).itens
  const exigirOk = async (r, oque) => {
    if (!r.ok()) throw new Error(`semear ${oque}: ${r.status()} ${await r.text()}`)
    return r.json().catch(() => null)
  }
  // O caminho de um arquivo: pedir o envio, mandar ao "R2" (o bucket de mentira) e confirmar.
  const enviar = async (nome, tipo, conteudo, finalidade) => {
    const pedido = await exigirOk(
      await api('POST', '/arquivos', { nome, tipo, finalidade, tamanho_bytes: conteudo.length }),
      `envio de ${nome}`,
    )
    if (!pedido.url.startsWith(R2_FICTICIO)) {
      throw new Error('a API não está com o bucket de mentira (suba com scripts/dev/ambiente-conferencia.sh)')
    }
    await exigirOk(
      await c.request.put(NO_BUCKET(pedido.url), { headers: { 'Content-Type': tipo }, data: conteudo }),
      `mandar ${nome} ao bucket`,
    )
    await exigirOk(await api('POST', `/arquivos/${pedido.arquivo_id}/confirmar`), `confirmar ${nome}`)
    return pedido.arquivo_id
  }
  if (semear) {
    const ja = (await avisos()).map((a) => a.titulo)
    if (!ja.includes(TITULO_FIXADO)) {
      const r = await api('POST', '/avisos', {
        titulo: TITULO_FIXADO,
        texto:
          'Na **quinta-feira**, a Comissão se reúne com a construtora para tratar do cronograma.\n\n' +
          '## O que vai ser tratado\n- Andamento das fundações do Bloco 3\n- Prazo de entrega das áreas comuns\n- Dúvidas enviadas pelos moradores\n\n' +
          '> Mande a sua pergunta até quarta-feira, pelo e-mail da Comissão: comissao-exemplo@example.com',
        categoria: 'reuniao',
        evento: { quando: new Date(Date.now() + 5 * 864e5).toISOString(), onde: 'Salão de vendas do empreendimento' },
        para_todos: true,
        fixado: true,
      })
      if (!r.ok()) throw new Error(`semear aviso fixado: ${r.status()} ${await r.text()}`)
    }
    if (!ja.includes(TITULO_AVISO)) {
      const r = await api('POST', '/avisos', {
        titulo: TITULO_AVISO,
        texto:
          'A vistoria das áreas comuns acontece por bloco, das 8h às 17h. Leve um documento com foto.\n\n' +
          'Um endereço longo para conferir a quebra de linha: https://portal-capibaribe-prime.example.com/documentos/vistoria-das-areas-comuns-2026',
        categoria: 'obra',
        para_todos: true,
      })
      if (!r.ok()) throw new Error(`semear aviso: ${r.status()} ${await r.text()}`)
    }
    if (!(await enquetes()).some((e) => e.pergunta === PERGUNTA)) {
      const r = await api('POST', '/enquetes', {
        pergunta: PERGUNTA,
        opcoes: ['Sábado de manhã, às 9h', 'Terça à noite, às 19h30', 'Quinta à noite, às 19h30'],
        encerra_em: new Date(Date.now() + 7 * 864e5).toISOString(),
        para_todos: true,
      })
      if (!r.ok()) throw new Error(`semear enquete: ${r.status()} ${await r.text()}`)
    }
    if (!ja.includes(TITULO_ANEXOS)) {
      const anexos = [
        await enviar('concretagem-laje-bloco-3.png', 'image/png', fotoPng(800, 600, [[96, 125, 139], [176, 190, 197], [121, 85, 72]]), 'aviso'),
        await enviar('vista-da-fachada.png', 'image/png', fotoPng(600, 800, [[129, 199, 132], [255, 213, 79], [69, 90, 100]]), 'aviso'),
        await enviar('Relatório de fiscalização da concretagem - setembro.pdf', 'application/pdf', PDF, 'aviso'),
      ]
      await exigirOk(
        await api('POST', '/avisos', {
          titulo: TITULO_ANEXOS,
          texto: 'As fotos foram tiradas na visita da Comissão. O relatório completo está no PDF.',
          categoria: 'obra',
          para_todos: true,
          anexos,
        }),
        'aviso com anexos',
      )
    }
    const docs = (await documentos()).map((d) => d.titulo)
    if (!docs.includes(TITULO_DOC)) {
      const primeiro = await enviar('relatorio-agosto.pdf', 'application/pdf', PDF, 'documento')
      const doc = await exigirOk(
        await api('POST', '/documentos', {
          titulo: TITULO_DOC,
          categoria: 'obra',
          data_documento: new Date(Date.now() - 20 * 864e5).toISOString().slice(0, 10),
          acesso: 'compradores',
          arquivo_id: primeiro,
        }),
        'documento',
      )
      // Uma versão nova, com o aviso automático ("Ver o documento") para as unidades.
      const segundo = await enviar('Relatório mensal de acompanhamento - setembro.pdf', 'application/pdf', PDF, 'documento')
      await exigirOk(
        await api('POST', `/documentos/${doc.id}/versoes`, {
          arquivo_id: segundo,
          avisar_unidades: true,
          nota_do_aviso: 'Corrigido o cronograma das fundações do Bloco 3.',
        }),
        'versão do documento',
      )
    }
    if (!docs.includes(TITULO_DOC_PUBLICO)) {
      await exigirOk(
        await api('POST', '/documentos', {
          titulo: TITULO_DOC_PUBLICO,
          categoria: 'contrato',
          data_documento: new Date(Date.now() - 200 * 864e5).toISOString().slice(0, 10),
          acesso: 'publico',
          arquivo_id: await enviar('memorial-descritivo.pdf', 'application/pdf', PDF, 'documento'),
        }),
        'documento público',
      )
    }
    // Indicações: três prestadores do admin; a Comissão dá um "não recomendo" e avisa a gestão
    // no primeiro.
    const categorias = (await (await api('GET', '/indicacoes/categorias')).json()).itens
    for (const i of INDICACOES) {
      const r = await api('POST', '/indicacoes', {
        categoria_id: categorias.find((c) => c.nome === i.categoria).id,
        nome: i.nome,
        telefone: i.telefone,
        instagram: i.instagram ?? null,
        recomenda: i.recomenda,
        comentario: i.comentario,
      })
      if (!r.ok() && r.status() !== 409) throw new Error(`semear indicação: ${r.status()} ${await r.text()}`)
    }
    // Um voto (do admin) para o resultado ter barra.
    const id = (await enquetes()).find((e) => e.pergunta === PERGUNTA).id
    const aberta = await (await api('GET', `/enquetes/${id}`)).json()
    if (!aberta.ja_votou) await api('PUT', `/enquetes/${id}/voto`, { opcoes: [aberta.opcoes[0].id] })
  }
  const indicacoes = (await (await api('GET', '/indicacoes')).json()).itens
  const indicacao = indicacoes.find((i) => i.nome === INDICACOES[0].nome)?.id
  if (semear && indicacao) {
    await c.request.post(`${BASE}/api/acesso/sair`, { headers: { 'X-Portal': '1' } })
    await entrar(c, QUEM.comissao)
    const aberto = await (await api('GET', `/indicacoes/${indicacao}`)).json()
    if (!aberto.minha_opiniao) {
      await exigirOk(
        await api('PUT', `/indicacoes/${indicacao}/opiniao`, {
          recomenda: false,
          comentario: 'Atrasou duas semanas a entrega dos armários.',
        }),
        'opinião da Comissão',
      )
    }
    if (!aberto.ja_avisei) {
      await exigirOk(
        await api('POST', `/indicacoes/${indicacao}/aviso`, { motivo: 'O número do WhatsApp não atende.' }),
        'aviso da Comissão',
      )
    }
    await c.request.post(`${BASE}/api/acesso/sair`, { headers: { 'X-Portal': '1' } })
    await entrar(c, QUEM.admin)
  }
  // Classificados (idempotentes pelo título, em "Meus anúncios" de quem anuncia).
  const fotoDoClassificado = async (cores) => {
    const png = fotoPng(800, 600, cores)
    const pedido = await exigirOk(
      await api('POST', '/classificados/fotos', { tipo: 'image/png', tamanho_bytes: png.length }),
      'foto de classificado',
    )
    await exigirOk(
      await c.request.put(NO_BUCKET(pedido.url), { headers: { 'Content-Type': 'image/png' }, data: png }),
      'mandar a foto ao bucket',
    )
    await exigirOk(await api('POST', `/classificados/fotos/${pedido.foto_id}/confirmar`), 'confirmar a foto')
    return pedido.foto_id
  }
  const meusClassificados = async () => (await (await api('GET', '/classificados/meus')).json()).itens
  const categoriaDoClassificado = async (nome) =>
    (await (await api('GET', '/classificados/categorias')).json()).itens.find((x) => x.nome === nome).id
  const anunciar = async (dados, fotos = []) => {
    if ((await meusClassificados()).some((a) => a.titulo === dados.titulo)) return
    const ids = []
    for (const cores of fotos) ids.push(await fotoDoClassificado(cores))
    await exigirOk(
      await api('POST', '/classificados', {
        ...dados,
        categoria_id: await categoriaDoClassificado(dados.categoria_id),
        fotos: ids,
      }),
      `anúncio ${dados.titulo}`,
    )
  }
  if (semear) {
    await anunciar(
      {
        tipo: 'venda',
        categoria_id: 'Material de obra e acabamento',
        titulo: CLASSIFICADO_LONGO,
        descricao:
          'Sobraram 12 caixas fechadas do porcelanato do apartamento, mais 3 sacos de argamassa e o rejunte da mesma cor.\nRetirar no Bloco 1, de noite ou no fim de semana. ' +
          'Dá para levar só uma parte, se preferir. '.repeat(10),
        preco_centavos: 125050,
        contato: '81999990201',
      },
      [
        [[176, 190, 197], [207, 216, 220], [144, 164, 174]],
        [[121, 85, 72], [161, 136, 127], [93, 64, 55]],
        [[255, 213, 79], [255, 224, 130], [255, 193, 7]],
      ],
    )
    await anunciar({
      tipo: 'venda',
      categoria_id: 'Eletrodomésticos',
      titulo: 'Geladeira frost free 400 litros',
      descricao: null,
      preco_centavos: null,
      contato: '8133330202',
    })
    await anunciar({
      tipo: 'troca',
      categoria_id: 'Infantil',
      titulo: 'Berço de madeira com colchão',
      descricao: 'Troco por um cercadinho.',
      preco_centavos: null,
      contato: '81999990201',
    })
    const berco = (await meusClassificados()).find((a) => a.titulo === 'Berço de madeira com colchão')
    if (berco && berco.situacao !== 'encerrado') {
      await exigirOk(await api('POST', `/classificados/${berco.id}/encerrar`, { motivo: 'troquei' }), 'encerrar')
    }
  }
  const classificado = (await meusClassificados()).find((a) => a.titulo === CLASSIFICADO_LONGO)?.id
  if (semear && classificado) {
    await c.request.post(`${BASE}/api/acesso/sair`, { headers: { 'X-Portal': '1' } })
    await entrar(c, QUEM.comissao)
    await anunciar(
      {
        tipo: 'doacao',
        categoria_id: 'Móveis',
        titulo: 'Cadeira de escritório',
        descricao: 'Funciona, só o encosto está gasto.',
        preco_centavos: null,
        contato: '81999990203',
      },
      [[[69, 90, 100], [96, 125, 139], [38, 50, 56]]],
    )
    const aberto = await (await api('GET', `/classificados/${classificado}`)).json()
    if (!aberto.ja_avisei) {
      await exigirOk(
        await api('POST', `/classificados/${classificado}/aviso`, { motivo: 'O preço parece errado.' }),
        'aviso da Comissão',
      )
    }
    await c.request.post(`${BASE}/api/acesso/sair`, { headers: { 'X-Portal': '1' } })
    await entrar(c, QUEM.admin)
  }
  const classificadoDaComissao = (await (await api('GET', '/classificados')).json()).itens.find(
    (a) => a.titulo === 'Cadeira de escritório',
  )?.id
  if (semear && classificadoDaComissao) {
    const aberto = await (await api('GET', `/classificados/${classificadoDaComissao}`)).json()
    if (!aberto.ja_avisei) {
      await exigirOk(
        await api('POST', `/classificados/${classificadoDaComissao}/aviso`, { motivo: 'A foto não é do produto.' }),
        'aviso do admin',
      )
    }
  }
  const ids = {
    classificado,
    classificado_comissao: classificadoDaComissao,
    indicacao,
    fixado: (await avisos()).find((a) => a.titulo === TITULO_FIXADO)?.id,
    aviso: (await avisos()).find((a) => a.titulo === TITULO_AVISO)?.id,
    enquete: (await enquetes()).find((e) => e.pergunta === PERGUNTA)?.id,
    anexos: (await avisos()).find((a) => a.titulo === TITULO_ANEXOS)?.id,
    documento: (await documentos()).find((d) => d.titulo === TITULO_DOC)?.id,
    aviso_documento: (await avisos()).find((a) => a.titulo.includes(TITULO_DOC.slice(0, 40)))?.id,
  }
  // A primeira unidade ainda não ativada (entra com a senha inicial e cai na troca obrigatória).
  const painel = await (await api('GET', '/admin/unidades')).json()
  QUEM.novo = painel.unidades.find((u) => !u.ativada)?.unidade.login ?? null
  await c.request.post(`${BASE}/api/acesso/sair`, { headers: { 'X-Portal': '1' } })
  await fecharChrome(c)
  return ids
}

// ---------- medidas (rodam dentro da página) ----------
function medir() {
  const visivel = (el) => {
    const r = el.getBoundingClientRect()
    const s = getComputedStyle(el)
    return r.width > 1 && r.height > 1 && s.visibility !== 'hidden' && s.display !== 'none' && Number(s.opacity) > 0
  }
  const descrever = (el) => {
    const id = el.id ? `#${el.id}` : ''
    const classe = typeof el.className === 'string' && el.className ? `.${el.className.trim().split(/\s+/).join('.')}` : ''
    const texto = (el.innerText || el.getAttribute('aria-label') || el.value || '').trim().replace(/\s+/g, ' ').slice(0, 40)
    return `${el.tagName.toLowerCase()}${id}${classe}${texto ? ` "${texto}"` : ''}`
  }
  const raiz = document.documentElement
  const largura = raiz.clientWidth
  // Janela aberta por cima (o "O que mudou", a foto grande): mede só ela, que é o que se vê; a
  // página atrás está coberta.
  const janela = document.querySelector('dialog:modal, [role=dialog]')
  const base = janela ?? document.body
  const todos = [...base.querySelectorAll('*')].filter(visivel)

  // Rola dentro: o elemento passa da borda, mas dentro de um ancestral com rolagem lateral
  // própria (overflow-x auto/scroll) que cabe na tela. A pessoa rola a faixa, não a página.
  const rolaDentro = (el) => {
    for (let pai = el.parentElement; pai && pai !== document.body; pai = pai.parentElement) {
      const ox = getComputedStyle(pai).overflowX
      if (ox === 'auto' || ox === 'scroll') return pai.getBoundingClientRect().right <= largura + 1
    }
    return false
  }
  const vazadosDaTela = todos
    .filter((el) => el.getBoundingClientRect().right > largura + 1)
    // Só o mais externo de cada galho: o filho de quem já vazou repete a mesma notícia.
    .filter((el, _, vazados) => !vazados.some((outro) => outro !== el && outro.contains(el)))
  const fora = (el) => `${descrever(el)} (direita ${Math.round(el.getBoundingClientRect().right)} > ${largura})`
  const foraDaTela = vazadosDaTela.filter((el) => !rolaDentro(el)).map(fora)
  const rolamDentro = vazadosDaTela.filter(rolaDentro).map(fora)

  // Quem empurra a página quando nada visível passa da borda (ex.: um rádio invisível largo):
  // os elementos mais internos cujo conteúdo é mais largo que eles.
  const largos = raiz.scrollWidth > raiz.clientWidth
    ? [...document.querySelectorAll('body *')].filter(
        (el) => el.scrollWidth > el.clientWidth + 1 && el.clientWidth > 0 && getComputedStyle(el).clipPath === 'none',
      )
    : []
  const transbordam = largos
    .filter((el) => !largos.some((outro) => outro !== el && el.contains(outro)))
    .map((el) => `${descrever(el)} (conteúdo ${el.scrollWidth} em ${el.clientWidth})`)

  // Só o que transborda pelo texto: a foto recortada na moldura (object-fit) não é texto cortado.
  const soImagemPassa = (el) => {
    if (!el.querySelector('img')) return false
    if ([...el.childNodes].some((n) => n.nodeType === Node.TEXT_NODE && n.textContent.trim())) return false
    const caixa = el.getBoundingClientRect()
    return ![...el.querySelectorAll('*')]
      .filter((f) => f.tagName !== 'IMG' && !f.closest('svg') && visivel(f))
      .some((f) => {
        const r = f.getBoundingClientRect()
        return r.bottom > caixa.bottom + 1 || r.right > caixa.right + 1 || r.left < caixa.left - 1 || r.top < caixa.top - 1
      })
  }
  const passaDaCaixa = todos.filter((el) => {
    const s = getComputedStyle(el)
    if (s.clipPath !== 'none') return false // .oculto: escondido de propósito
    const esconde = (v) => v === 'hidden' || v === 'clip'
    const lado = esconde(s.overflowX) && el.scrollWidth > el.clientWidth + 1
    const alto = esconde(s.overflowY) && el.scrollHeight > el.clientHeight + 1
    return (lado || alto || (s.textOverflow === 'ellipsis' && el.scrollWidth > el.clientWidth + 1)) && el.innerText?.trim() && !soImagemPassa(el)
  })
  const caixaDe = (el) => `${descrever(el)} (${el.scrollWidth}x${el.scrollHeight} em ${el.clientWidth}x${el.clientHeight})`
  // Resumido de propósito (line-clamp com reticências, como o título do documento no topo, U17,
  // que aparece inteiro logo abaixo): listado à parte, não conta como problema.
  const resumidoDeProposito = (el) => getComputedStyle(el).webkitLineClamp !== 'none'
  // Texto que vaza da caixa do controle (botão, link-botão, rótulo de opção, campo): não some
  // nem rola a página, mas passa por cima da borda. Só o mais externo de cada galho.
  const controles = todos.filter((el) => el.matches('button, a[href], label, summary, input, select, textarea'))
  const vazam = controles.filter((el) => {
    const s = getComputedStyle(el)
    if (s.display.startsWith('inline') && !s.display.includes('flex') && !s.display.includes('block')) return false
    if (s.overflowX !== 'visible' || s.clipPath !== 'none') return false
    const caixa = el.getBoundingClientRect()
    return [...el.querySelectorAll('*')].concat([el]).some((f) => {
      if (f !== el && !visivel(f)) return false
      const texto = [...f.childNodes].filter((n) => n.nodeType === Node.TEXT_NODE && n.textContent.trim())
      return texto.some((n) => {
        const faixa = document.createRange()
        faixa.selectNodeContents(n)
        return [...faixa.getClientRects()].some((r) => r.width > 0 && (r.right > caixa.right + 1 || r.left < caixa.left - 1))
      })
    })
  })
  const cortados = passaDaCaixa
    .filter((el) => !resumidoDeProposito(el))
    .map(caixaDe)
    .concat(vazam.map((el) => `${descrever(el)} (o texto passa da borda)`))
  const resumidos = passaDaCaixa.filter(resumidoDeProposito).map(caixaDe)

  // Palavra curta (até 12 letras) quebrada no meio: as letras dela caem em duas linhas. Quebra
  // em hífen não conta (o hífen separa as duas palavras). Palavra mais comprida que isso pode
  // não caber na linha com letra grande (spec 3.5, overflow-wrap).
  const quebradas = []
  // Quebra com hífen da hifenização (hyphens: auto, U7): é a quebra certa, na sílaba; listada à
  // parte, não conta.
  const hifenizadas = []
  const busca = document.createTreeWalker(base, NodeFilter.SHOW_TEXT)
  while (busca.nextNode()) {
    const no = busca.currentNode
    const pai = no.parentElement
    if (!no.textContent.trim() || !pai || !visivel(pai) || pai.closest('.oculto, svg')) continue
    for (const bloco of no.textContent.matchAll(/\S+/g)) {
      // Endereço e e-mail são uma "palavra" só, comprida: quebram onde der (spec 3.5).
      if (/[@/]|\p{L}\.\p{L}/u.test(bloco[0])) continue
      for (const m of bloco[0].matchAll(/[\p{L}\p{N}]+/gu)) {
        if (m[0].length < 2 || m[0].length > 12) continue
        const inicio = bloco.index + m.index
        const faixa = document.createRange()
        faixa.setStart(no, inicio)
        faixa.setEnd(no, inicio + m[0].length)
        const caixas = [...faixa.getClientRects()].filter((r) => r.width > 0)
        if (caixas.length > 1 && Math.abs(caixas[0].top - caixas[caixas.length - 1].top) > 2) {
          const lista = getComputedStyle(pai).hyphens === 'auto' && m[0].length >= 5 ? hifenizadas : quebradas
          lista.push(`"${m[0]}" em ${descrever(pai)}`)
        }
      }
    }
  }

  const interativos = todos.filter((el) =>
    el.matches('a[href], button, input:not([type=hidden]), select, textarea, summary, [role=button], [tabindex="0"]'),
  )
  const emLinha = (el) => {
    if (el.tagName !== 'A') return false
    const pai = el.parentElement
    if (!pai || getComputedStyle(el).display !== 'inline') return false
    return [...pai.childNodes].some((n) => n !== el && n.nodeType === Node.TEXT_NODE && n.textContent.trim())
  }
  const pequenos = []
  for (const el of interativos) {
    let alvo = el
    // Rádio e caixa de seleção valem pelo rótulo que os envolve (é ele que recebe o toque).
    if (el.matches('input[type=radio], input[type=checkbox]')) alvo = el.closest('label') ?? el
    const r = alvo.getBoundingClientRect()
    if ((r.width < 44 || r.height < 44) && !emLinha(el)) {
      pequenos.push(`${descrever(el)} (${Math.round(r.width)}x${Math.round(r.height)})`)
    }
  }

  // Letra: tamanho de cada folha de texto visível.
  const tamanhos = []
  const passeio = document.createTreeWalker(base, NodeFilter.SHOW_TEXT)
  while (passeio.nextNode()) {
    const no = passeio.currentNode
    const pai = no.parentElement
    if (!no.textContent.trim() || !pai || !visivel(pai) || pai.closest('.oculto')) continue
    tamanhos.push(parseFloat(getComputedStyle(pai).fontSize))
  }
  tamanhos.sort((a, b) => a - b)

  // Ícone encolhido: o SVG (todos do Portal são quadrados, viewBox 0 0 24 24) com largura e
  // altura fora da proporção do desenho; e o pontinho redondo em CSS (::before com
  // border-radius 50 %, como o do selo "Novo") que deixou de ser redondo.
  const encolhidos = []
  for (const el of todos) {
    if (el.tagName.toLowerCase() === 'svg') {
      const caixa = el.viewBox?.baseVal
      const r = el.getBoundingClientRect()
      // O SVG esticado de propósito (o arco da barra, preserveAspectRatio="none") não é ícone.
      const esticado = el.getAttribute('preserveAspectRatio') === 'none'
      if (!esticado && caixa && caixa.width && caixa.height && Math.abs(r.width - (r.height * caixa.width) / caixa.height) > 1) {
        encolhidos.push(`${descrever(el.parentElement ?? el)} > svg (${r.width.toFixed(1)}x${r.height.toFixed(1)})`)
      }
    }
    const antes = getComputedStyle(el, '::before')
    if (antes.content !== 'none' && antes.display !== 'none' && antes.borderRadius === '50%') {
      const l = parseFloat(antes.width)
      const a = parseFloat(antes.height)
      if (l && a && Math.abs(l - a) > 1) encolhidos.push(`${descrever(el)}::before (${l.toFixed(1)}x${a.toFixed(1)})`)
    }
  }
  // A barra do celular com a bola do Menu. Com a folha aberta, a barra está atrás do véu.
  const barra = janela ? null : document.querySelector('.nav-barra')
  let alturaDaBarra = 0
  const naBarra = []
  if (barra && visivel(barra)) {
    const caixa = barra.getBoundingClientRect()
    const bola = barra.querySelector('.nav-bola-circulo')?.getBoundingClientRect()
    const topo = Math.min(caixa.top, bola?.top ?? caixa.top)
    const safeArea = parseFloat(getComputedStyle(barra).paddingBottom) || 0
    alturaDaBarra = Math.round((caixa.bottom - safeArea - topo) * 10) / 10
    // O teto de 104 px é do celular (spec, seção 3: 320 a 412 px). No layout de celular numa tela
    // larga (notebook a 150 % ou 200 %), o teto pela largura (vw) não segura nada e a barra
    // acompanha a letra, como o resto da página (docs/superpowers/duvidas-nav-bola.md).
    if (largura < 600 && alturaDaBarra > 104) naBarra.push(`barra com ${alturaDaBarra} px de altura (> 104)`)
    for (const el of barra.querySelectorAll('a, .nav-bola, .nav-rotulo, .nav-bola-rotulo')) {
      if (visivel(el) && el.scrollWidth > el.clientWidth + 1) {
        naBarra.push(`rótulo que não cabe: ${descrever(el)} (${el.scrollWidth} em ${el.clientWidth})`)
      }
    }
    // Rótulos de abas vizinhas que se encostam (menos de 2 px entre as palavras).
    const rotulos = [...barra.querySelectorAll('.nav-rotulo, .nav-bola-rotulo')]
      .filter(visivel)
      .map((el) => {
        // Só o texto que se vê: o nome inteiro escondido para o leitor de tela ("Documentos"
        // na tela estreita, recortado por clip-path) não conta.
        const r = []
        const andar = document.createTreeWalker(el, NodeFilter.SHOW_TEXT)
        for (let no = andar.nextNode(); no; no = andar.nextNode()) {
          let pai = no.parentElement
          let escondido = false
          for (; pai && pai !== el.parentElement; pai = pai.parentElement) {
            const st = getComputedStyle(pai)
            if (st.clipPath !== 'none' || st.display === 'none') escondido = true
          }
          if (escondido) continue
          const faixa = document.createRange()
          faixa.selectNodeContents(no)
          r.push(...[...faixa.getClientRects()].filter((q) => q.width > 0))
        }
        return { el, esquerda: Math.min(...r.map((q) => q.left)), direita: Math.max(...r.map((q) => q.right)) }
      })
      .sort((a, b) => a.esquerda - b.esquerda)
    for (let i = 1; i < rotulos.length; i++) {
      if (rotulos[i].esquerda - rotulos[i - 1].direita < 2) {
        naBarra.push(`rótulos encostados: ${descrever(rotulos[i - 1].el)} e ${descrever(rotulos[i].el)}`)
      }
    }
    // O fim do conteúdo nunca fica atrás da barra (nem da saliência da bola): rola até o fim,
    // mede e volta para o alto (o print é da página inteira).
    const principal = document.querySelector('main')
    const ultimo = principal && [...principal.querySelectorAll('*')].filter(visivel).at(-1)
    if (ultimo) {
      window.scrollTo(0, raiz.scrollHeight)
      const fimDoConteudo = ultimo.getBoundingClientRect().bottom
      const topoDaBarra = Math.min(barra.getBoundingClientRect().top, barra.querySelector('.nav-bola-circulo')?.getBoundingClientRect().top ?? Infinity)
      if (fimDoConteudo > topoDaBarra + 1) {
        naBarra.push(`fim do conteúdo atrás da barra: ${descrever(ultimo)} (${Math.round(fimDoConteudo)} > ${Math.round(topoDaBarra)})`)
      }
      window.scrollTo(0, 0)
    }
  }
  return {
    alturaDaBarra,
    naBarra,
    raiz: parseFloat(getComputedStyle(raiz).fontSize),
    corpo: parseFloat(getComputedStyle(document.body).fontSize),
    letraMediana: tamanhos[Math.floor(tamanhos.length / 2)] ?? 0,
    letraMenor: tamanhos[0] ?? 0,
    rolagemLateral: raiz.scrollWidth > raiz.clientWidth,
    larguraDaPagina: raiz.scrollWidth,
    foraDaTela,
    rolamDentro,
    transbordam,
    cortados,
    pequenos,
    encolhidos,
    quebradas,
    hifenizadas,
    resumidos,
    janela: Boolean(janela),
  }
}

// ---------- rodada ----------
const ids = await semente(args.includes('--semear'))
const resultados = []
for (const fonte of FONTES) {
  const chrome = await abrirChrome(fonte)
  for (const tema of TEMAS) {
    await chrome.clearCookies()
    await chrome.addInitScript((t) => {
      try {
        localStorage.setItem('portal-tema', t)
      } catch {}
    }, tema)
    for (const largura of LARGURAS) {
      // Entra uma vez por quem: o cookie da sessão é do Chrome inteiro.
      let quemEstaDentro = 'anonimo'
      for (const tela of escolhidas) {
        const caminho = tela.caminho.replace(/\{(\w+)\}/g, (_, k) => ids[k] ?? `sem-${k}`)
        if (caminho.includes('sem-')) {
          console.log(`pulada: ${tela.nome} (sem dado; rode com --semear)`)
          continue
        }
        if (tela.quem !== 'anonimo' && !QUEM[tela.quem]) {
          console.log(`pulada: ${tela.nome} (sem unidade "${tela.quem}")`)
          continue
        }
        if (tela.quem !== quemEstaDentro) {
          await sair(chrome)
          if (tela.quem !== 'anonimo') await entrar(chrome, QUEM[tela.quem])
          quemEstaDentro = tela.quem
        }
        const pagina = await chrome.newPage()
        if (tela.iphone) {
          await pagina.addInitScript((agente) => {
            Object.defineProperty(navigator, 'userAgent', { get: () => agente })
            Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 5 })
          }, AGENTE_IPHONE)
        }
        await pagina.setViewportSize(janelaDe(largura))
        const errosJs = []
        pagina.on('pageerror', (e) => errosJs.push(e.message))
        await pagina.goto(`${BASE}${caminho}`, { waitUntil: 'networkidle' })
        await pagina.waitForTimeout(200)
        if (tela.depois) await tela.depois(pagina)
        const m = await pagina.evaluate(medir)
        if (Math.round(m.raiz) !== fonte) {
          errosJs.push(`a fonte do navegador não pegou: html com ${m.raiz}px, pedido ${fonte}px`)
        }
        const arquivo = `${tela.nome}-${largura}-${fonte}${tema === 'claro' ? '' : `-${tema}`}.png`
        // Com janela aberta, o print é da tela (a janela é fixa; a página inteira atrás só a
        // espalharia pelo meio do print).
        await pagina.screenshot({ path: join(SAIDA, arquivo), fullPage: !m.janela })
        await pagina.close()
        const r = { tela: tela.nome, grupo: tela.grupo, largura, fonte, tema, arquivo, errosJs, ...m }
        resultados.push(r)
        const problemas =
          Number(m.rolagemLateral) +
          m.foraDaTela.length +
          m.cortados.length +
          m.pequenos.length +
          m.encolhidos.length +
          m.quebradas.length +
          m.naBarra.length +
          errosJs.length
        console.log(
          `${problemas ? 'PROBLEMA' : 'ok      '} ${tela.nome.padEnd(20)} ${String(largura).padStart(4)} px  fonte ${fonte}` +
            `  letra ${m.letraMediana}/${m.letraMenor}  rolagem ${m.rolagemLateral ? 'SIM' : 'não'}` +
            `  fora ${m.foraDaTela.length}  cortado ${m.cortados.length}  alvo<44 ${m.pequenos.length}  encolhido ${m.encolhidos.length}  quebrada ${m.quebradas.length}` +
            (m.alturaDaBarra ? `  barra ${m.alturaDaBarra}px${m.naBarra.length ? ` (${m.naBarra.length} problema)` : ''}` : ''),
        )
      }
      await sair(chrome)
    }
  }
  await fecharChrome(chrome)
}

// ---------- relatório ----------
writeFileSync(join(SAIDA, 'resultado.json'), JSON.stringify(resultados, null, 2))
const linhas = []
linhas.push(`Conferência da letra (${TAREFA}) · ${resultados.length} prints em ${SAIDA}`)
linhas.push('')
linhas.push('fonte  largura  letra mediana (esperado)  com rolagem  com algo fora  com cortado  com alvo<44  com ícone encolhido  com palavra quebrada')
for (const fonte of FONTES) {
  for (const largura of LARGURAS) {
    const rs = resultados.filter((r) => r.fonte === fonte && r.largura === largura)
    if (!rs.length) continue
    const mediana = rs.map((r) => r.letraMediana).sort((a, b) => a - b)[Math.floor(rs.length / 2)]
    linhas.push(
      `${String(fonte).padStart(5)}  ${String(largura).padStart(7)}  ${String(mediana).padStart(13)} (${((18 * fonte) / 16).toFixed(1)})` +
        `  ${String(rs.filter((r) => r.rolagemLateral).length).padStart(11)}` +
        `  ${String(rs.filter((r) => r.foraDaTela.length).length).padStart(13)}` +
        `  ${String(rs.filter((r) => r.cortados.length).length).padStart(11)}` +
        `  ${String(rs.filter((r) => r.pequenos.length).length).padStart(11)}` +
        `  ${String(rs.filter((r) => r.encolhidos.length).length).padStart(19)}` +
        `  ${String(rs.filter((r) => r.quebradas.length).length).padStart(20)}`,
    )
  }
}
linhas.push('')
for (const r of resultados) {
  // Até 6 de cada tipo (uma grade de 40 apartamentos repetiria a mesma notícia 40 vezes).
  const ate6 = (rotulo, xs) => [
    ...xs.slice(0, 6).map((x) => `${rotulo}: ${x}`),
    ...(xs.length > 6 ? [`${rotulo}: … e mais ${xs.length - 6}`] : []),
  ]
  const itens = [
    ...(r.rolagemLateral ? [`rolagem lateral (página com ${r.larguraDaPagina} px)`] : []),
    ...ate6('fora da tela', r.foraDaTela),
    ...ate6('quem empurra', r.transbordam),
    ...ate6('cortado', r.cortados),
    ...ate6('alvo < 44', r.pequenos),
    ...ate6('ícone encolhido', r.encolhidos),
    ...ate6('palavra quebrada', r.quebradas),
    ...ate6('barra', r.naBarra ?? []),
    ...ate6('rola dentro (não conta)', r.rolamDentro ?? []),
    ...ate6('resumido de propósito (não conta)', r.resumidos),
    ...ate6('hifenizada (não conta)', r.hifenizadas ?? []),
    ...ate6('erro JS', r.errosJs),
  ]
  if (!itens.length) continue
  linhas.push(`## ${r.tela} · ${r.largura} px · fonte ${r.fonte}${r.tema === 'claro' ? '' : ` · ${r.tema}`} (${r.arquivo})`)
  for (const i of itens) linhas.push(`- ${i}`)
}
writeFileSync(join(SAIDA, 'resumo.txt'), linhas.join('\n') + '\n')
console.log(`\n${linhas.slice(0, 3 + FONTES.length * LARGURAS.length).join('\n')}\n\nDetalhes: ${join(SAIDA, 'resumo.txt')}`)
const algum = resultados.some(
  (r) =>
    r.rolagemLateral ||
    r.foraDaTela.length ||
    r.cortados.length ||
    r.pequenos.length ||
    r.encolhidos.length ||
    r.quebradas.length ||
    r.naBarra.length ||
    r.errosJs.length,
)
process.exit(algum ? 1 : 0)
