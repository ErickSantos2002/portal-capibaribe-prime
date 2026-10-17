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
//   - se a letra cresceu: o tamanho mediano e o menor do texto visível.
//
// Precisa do Portal no ar com dados (scripts/dev/ambiente-conferencia.sh) e do Chrome do sistema
// (/usr/bin/google-chrome-stable, ou CHROME=<caminho>). Uso, da raiz do repositório:
//   node scripts/dev/conferir-letra.mjs --base http://localhost:5170 --tarefa base --semear
//   node scripts/dev/conferir-letra.mjs --base http://localhost:5171 --tarefa g1 --grupo G1
//   node scripts/dev/conferir-letra.mjs ... --telas entrar,mural --larguras 360 --fontes 32
// Opções: --grupo comum|G1|G2|G3 (só as telas do grupo; repetível com vírgula), --telas <nomes>,
// --larguras 360,1280, --fontes 16,24,32, --temas claro[,escuro], --saida <pasta>,
// --semear (cria, uma vez, os avisos e a enquete fictícios que as telas usam), --listar.
// Saída: <saida>/<tela>-<largura>-<fonte>[-escuro].png, resultado.json e resumo.txt
// (padrão: /tmp/portal-letra-<tarefa>/). Sai com código 1 se houver algum problema.
import { createRequire } from 'node:module'
import { mkdirSync, writeFileSync } from 'node:fs'
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
const LARGURAS = lista(opcao('larguras', '360,1280')).map(Number)
const FONTES = lista(opcao('fontes', '16,24,32')).map(Number)
const TEMAS = lista(opcao('temas', 'claro'))
const SENHA = 'mudar123'
// Dados fictícios de semente fixa (api/app/servicos/dados_ficticios.py): 1002 é o admin,
// 1003 é da Comissão, 1101 é um morador comum já ativado.
const QUEM = { admin: '1002', morador: '1101' }

// ---------- as telas ----------
// grupo: quem converte o CSS dela (plano docs/superpowers/plans/m5-letra.md). `quem`: anonimo,
// morador ou admin. `{aviso}`, `{fixado}` e `{enquete}` viram os ids da semente.
const TELAS = [
  { nome: 'entrar', grupo: 'G3', quem: 'anonimo', caminho: '/entrar' },
  { nome: 'privacidade', grupo: 'G3', quem: 'anonimo', caminho: '/privacidade' },
  { nome: 'minha-unidade', grupo: 'G3', quem: 'morador', caminho: '/minha-unidade' },
  { nome: 'esqueci-a-senha', grupo: 'G3', quem: 'anonimo', caminho: '/esqueci-a-senha' },
  { nome: 'mural', grupo: 'G1', quem: 'morador', caminho: '/avisos' },
  { nome: 'aviso', grupo: 'G1', quem: 'morador', caminho: '/avisos/{aviso}' },
  { nome: 'aviso-fixado', grupo: 'G1', quem: 'morador', caminho: '/avisos/{fixado}' },
  { nome: 'novo-aviso', grupo: 'G1', quem: 'admin', caminho: '/avisos/novo' },
  { nome: 'quem-leu', grupo: 'G1', quem: 'admin', caminho: '/avisos/{aviso}/leitura' },
  { nome: 'documentos', grupo: 'G2', quem: 'morador', caminho: '/documentos' },
  { nome: 'documentos-publicos', grupo: 'G2', quem: 'anonimo', caminho: '/documentos/publicos' },
  { nome: 'novo-documento', grupo: 'G2', quem: 'admin', caminho: '/documentos/novo' },
  { nome: 'receber-avisos', grupo: 'G2', quem: 'morador', caminho: '/receber-avisos' },
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
  { nome: 'ficha-unidade', grupo: 'G3', quem: 'admin', caminho: '/unidades/1101' },
  { nome: 'historico', grupo: 'G3', quem: 'admin', caminho: '/historico' },
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
const navegador = await chromium.launch({
  executablePath: process.env.CHROME ?? '/usr/bin/google-chrome-stable',
  headless: true,
  args: ['--lang=pt-BR'],
})

async function contexto(largura, tema) {
  const c = await navegador.newContext({
    viewport: { width: largura, height: largura < 900 ? 780 : 900 },
    locale: 'pt-BR',
    timezoneId: 'America/Recife',
    hasTouch: largura < 900,
    isMobile: false,
  })
  await c.addInitScript((t) => {
    try {
      localStorage.setItem('portal-tema', t)
    } catch {}
  }, tema)
  return c
}

/** O `font-size: medium` do navegador, como a opção "Tamanho da fonte" das configurações. */
async function usarFonte(pagina, px) {
  const cdp = await pagina.context().newCDPSession(pagina)
  await cdp.send('Page.setFontSizes', { fontSizes: { standard: px, fixed: Math.round((px * 13) / 16) } })
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

async function semente(semear) {
  const c = await contexto(1280, 'claro')
  await entrar(c, QUEM.admin)
  const api = (metodo, caminho, data) =>
    c.request.fetch(`${BASE}/api${caminho}`, { method: metodo, headers: { 'X-Portal': '1' }, data })
  const avisos = async () => (await (await api('GET', '/avisos')).json()).itens
  const enquetes = async () => (await (await api('GET', '/enquetes')).json()).itens
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
    // Um voto (do admin) para o resultado ter barra.
    const id = (await enquetes()).find((e) => e.pergunta === PERGUNTA).id
    const aberta = await (await api('GET', `/enquetes/${id}`)).json()
    if (!aberta.ja_votou) await api('PUT', `/enquetes/${id}/voto`, { opcoes: [aberta.opcoes[0].id] })
  }
  const ids = {
    fixado: (await avisos()).find((a) => a.titulo === TITULO_FIXADO)?.id,
    aviso: (await avisos()).find((a) => a.titulo === TITULO_AVISO)?.id,
    enquete: (await enquetes()).find((e) => e.pergunta === PERGUNTA)?.id,
  }
  await c.request.post(`${BASE}/api/acesso/sair`, { headers: { 'X-Portal': '1' } })
  await c.close()
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
  const todos = [...document.querySelectorAll('body *')].filter(visivel)

  const foraDaTela = todos
    .filter((el) => el.getBoundingClientRect().right > largura + 1)
    // Só o mais externo de cada galho: o filho de quem já vazou repete a mesma notícia.
    .filter((el, _, vazados) => !vazados.some((outro) => outro !== el && outro.contains(el)))
    .map((el) => `${descrever(el)} (direita ${Math.round(el.getBoundingClientRect().right)} > ${largura})`)

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

  const cortados = todos
    .filter((el) => {
      const s = getComputedStyle(el)
      if (s.clipPath !== 'none') return false // .oculto: escondido de propósito
      const esconde = (v) => v === 'hidden' || v === 'clip'
      const lado = esconde(s.overflowX) && el.scrollWidth > el.clientWidth + 1
      const alto = esconde(s.overflowY) && el.scrollHeight > el.clientHeight + 1
      return (lado || alto || (s.textOverflow === 'ellipsis' && el.scrollWidth > el.clientWidth + 1)) && el.innerText?.trim()
    })
    .map((el) => `${descrever(el)} (${el.scrollWidth}x${el.scrollHeight} em ${el.clientWidth}x${el.clientHeight})`)

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
  const passeio = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)
  while (passeio.nextNode()) {
    const no = passeio.currentNode
    const pai = no.parentElement
    if (!no.textContent.trim() || !pai || !visivel(pai) || pai.closest('.oculto')) continue
    tamanhos.push(parseFloat(getComputedStyle(pai).fontSize))
  }
  tamanhos.sort((a, b) => a - b)
  return {
    raiz: parseFloat(getComputedStyle(raiz).fontSize),
    corpo: parseFloat(getComputedStyle(document.body).fontSize),
    letraMediana: tamanhos[Math.floor(tamanhos.length / 2)] ?? 0,
    letraMenor: tamanhos[0] ?? 0,
    rolagemLateral: raiz.scrollWidth > raiz.clientWidth,
    larguraDaPagina: raiz.scrollWidth,
    foraDaTela,
    transbordam,
    cortados,
    pequenos,
  }
}

// ---------- rodada ----------
const ids = await semente(args.includes('--semear'))
const resultados = []
for (const tema of TEMAS) {
  for (const largura of LARGURAS) {
    // Um contexto por quem entra (o cookie da sessão é do contexto).
    const porQuem = {}
    for (const tela of escolhidas) {
      const caminho = tela.caminho.replace(/\{(\w+)\}/g, (_, k) => ids[k] ?? `sem-${k}`)
      if (caminho.includes('sem-')) {
        console.log(`pulada: ${tela.nome} (sem dado; rode com --semear)`)
        continue
      }
      if (!porQuem[tela.quem]) {
        porQuem[tela.quem] = await contexto(largura, tema)
        if (tela.quem !== 'anonimo') await entrar(porQuem[tela.quem], QUEM[tela.quem])
      }
      for (const fonte of FONTES) {
        const pagina = await porQuem[tela.quem].newPage()
        const errosJs = []
        pagina.on('pageerror', (e) => errosJs.push(e.message))
        await usarFonte(pagina, fonte)
        await pagina.goto(`${BASE}${caminho}`, { waitUntil: 'networkidle' })
        await pagina.waitForTimeout(200)
        if (tela.depois) await tela.depois(pagina)
        const m = await pagina.evaluate(medir)
        const arquivo = `${tela.nome}-${largura}-${fonte}${tema === 'claro' ? '' : `-${tema}`}.png`
        await pagina.screenshot({ path: join(SAIDA, arquivo), fullPage: true })
        await pagina.close()
        const r = { tela: tela.nome, grupo: tela.grupo, largura, fonte, tema, arquivo, errosJs, ...m }
        resultados.push(r)
        const problemas = Number(m.rolagemLateral) + m.foraDaTela.length + m.cortados.length + m.pequenos.length + errosJs.length
        console.log(
          `${problemas ? 'PROBLEMA' : 'ok      '} ${tela.nome.padEnd(20)} ${String(largura).padStart(4)} px  fonte ${fonte}` +
            `  letra ${m.letraMediana}/${m.letraMenor}  rolagem ${m.rolagemLateral ? 'SIM' : 'não'}` +
            `  fora ${m.foraDaTela.length}  cortado ${m.cortados.length}  alvo<44 ${m.pequenos.length}`,
        )
      }
    }
    // Sai de cada sessão: sem isso, cada rodada deixa um "aparelho conectado" a mais na conta.
    for (const c of Object.values(porQuem)) {
      await c.request.post(`${BASE}/api/acesso/sair`, { headers: { 'X-Portal': '1' } }).catch(() => {})
      await c.close()
    }
  }
}
await navegador.close()

// ---------- relatório ----------
writeFileSync(join(SAIDA, 'resultado.json'), JSON.stringify(resultados, null, 2))
const linhas = []
linhas.push(`Conferência da letra (${TAREFA}) · ${resultados.length} prints em ${SAIDA}`)
linhas.push('')
linhas.push('fonte  largura  letra mediana (esperado)  com rolagem  com algo fora  com cortado  com alvo<44')
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
        `  ${String(rs.filter((r) => r.pequenos.length).length).padStart(11)}`,
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
    ...ate6('erro JS', r.errosJs),
  ]
  if (!itens.length) continue
  linhas.push(`## ${r.tela} · ${r.largura} px · fonte ${r.fonte}${r.tema === 'claro' ? '' : ` · ${r.tema}`} (${r.arquivo})`)
  for (const i of itens) linhas.push(`- ${i}`)
}
writeFileSync(join(SAIDA, 'resumo.txt'), linhas.join('\n') + '\n')
console.log(`\n${linhas.slice(0, 3 + FONTES.length * LARGURAS.length).join('\n')}\n\nDetalhes: ${join(SAIDA, 'resumo.txt')}`)
const algum = resultados.some(
  (r) => r.rolagemLateral || r.foraDaTela.length || r.cortados.length || r.pequenos.length || r.errosJs.length,
)
process.exit(algum ? 1 : 0)
