// Verificação da revisão do M1 no navegador: Chrome headless, contexto isolado por rodada.
// 320, 390 e 1366 px; claro e escuro; CSP; rolagem lateral; axe nas seis telas; checagens
// específicas de U2, U3, U4, U10. Banco portal_m1_revisao, API 8120, preview 5120.
import { chromium } from 'playwright'
import { AxeBuilder } from '@axe-core/playwright'
import { mkdirSync } from 'node:fs'

const BASE = 'http://localhost:5120'
const PRINTS = process.argv[2]
mkdirSync(PRINTS, { recursive: true })

const ADMIN = '1002'
const COMISSAO = '1003'
const COMUM = '1101'
const NAO_ATIVADA = '1001'
const SENHA = 'mudar123'
const LARGURAS = [320, 390, 1366]
const TEMAS = ['claro', 'escuro']

const problemas = []
const falhar = (msg) => {
  problemas.push(msg)
  console.log('PROBLEMA:', msg)
}

const navegador = await chromium.launch({ channel: 'chrome', headless: true })

async function novoContexto(largura, tema) {
  const contexto = await navegador.newContext({
    viewport: { width: largura, height: largura < 900 ? 800 : 900 },
    colorScheme: tema === 'escuro' ? 'dark' : 'light',
  })
  await contexto.addInitScript((t) => {
    try {
      localStorage.setItem('portal-tema', t)
    } catch {}
    window.__csp = []
    document.addEventListener('securitypolicyviolation', (e) =>
      window.__csp.push(`${e.violatedDirective} ${e.blockedURI}`),
    )
  }, tema)
  const pagina = await contexto.newPage()
  pagina.on('console', (m) => {
    if (/Content Security Policy/i.test(m.text())) falhar(`CSP (console): ${m.text()}`)
  })
  pagina.on('pageerror', (e) => falhar(`erro JS: ${e.message}`))
  return { contexto, pagina }
}

async function entrar(pagina, login, senha = SENHA) {
  await pagina.goto(`${BASE}/entrar`)
  await pagina.getByRole('radio', { name: `Bloco ${login[0]}` }).check({ force: true })
  await pagina.getByLabel('Apartamento').fill(login.slice(1))
  await pagina.getByLabel('Senha', { exact: true }).fill(senha)
  await pagina.getByRole('button', { name: 'Entrar' }).click()
}

async function api(pagina, metodo, caminho, corpo) {
  const r = await pagina.request.fetch(`${BASE}${caminho}`, {
    method: metodo,
    headers: { 'X-Portal': '1', 'Content-Type': 'application/json' },
    data: corpo ? JSON.stringify(corpo) : undefined,
  })
  if (r.status() >= 400) throw new Error(`${metodo} ${caminho}: ${r.status()} ${await r.text()}`)
  return r.status() === 204 ? null : r.json()
}

async function conferir(pagina, nome, largura, tema, { axe = true } = {}) {
  await pagina.waitForLoadState('networkidle')
  await pagina.waitForTimeout(150)
  const { sw, iw } = await pagina.evaluate(() => ({
    sw: document.documentElement.scrollWidth,
    iw: window.innerWidth,
  }))
  if (sw > iw) falhar(`${nome} ${largura} ${tema}: rolagem lateral (${sw} > ${iw})`)
  const csp = await pagina.evaluate(() => window.__csp)
  if (csp.length) falhar(`${nome} ${largura} ${tema}: CSP ${csp.join('; ')}`)
  if (axe) {
    const r = await new AxeBuilder({ page: pagina }).analyze()
    console.log(`axe ${nome} ${largura} ${tema}: ${r.passes.length} regras ok, ${r.violations.length} violações`)
    for (const v of r.violations) {
      falhar(`${nome} ${largura} ${tema}: axe ${v.id} (${v.impact}) ${v.nodes.length}x — ${v.nodes[0]?.target}`)
    }
  }
  await pagina.screenshot({ path: `${PRINTS}/${nome}-${largura}-${tema}.png`, fullPage: true })
}

// --- preparo: avisos pela Comissão (um fixado, um corrigido depois da leitura do comum) ------
const preparo = await novoContexto(390, 'claro')
await entrar(preparo.pagina, COMISSAO)
await preparo.pagina.waitForURL(/\/avisos/)
const fixado = await api(preparo.pagina, 'POST', '/api/avisos', {
  titulo: 'Vistoria da obra marcada para sábado, às 9h, com a construtora',
  texto: 'A construtora liberou uma visita guiada.\n\nLevem documento com foto.',
  para_todos: true,
  fixado: true,
})
const comum = await api(preparo.pagina, 'POST', '/api/avisos', {
  titulo: 'Reunião da Comissão',
  texto: 'Pauta: andamento da obra e prazos de entrega.',
  para_todos: false,
  blocos: [1, 2],
})
const morador = await novoContexto(390, 'claro')
await entrar(morador.pagina, COMUM)
await morador.pagina.waitForURL(/\/avisos/)
await api(morador.pagina, 'POST', `/api/avisos/${comum.id}/lido`)
await api(morador.pagina, 'POST', `/api/avisos/${fixado.id}/lido`)
await api(preparo.pagina, 'PUT', `/api/avisos/${fixado.id}`, {
  titulo: fixado.titulo,
  texto: 'A construtora liberou uma visita guiada.\n\nLevem documento com foto e usem sapato fechado.',
})
await preparo.contexto.close()
await morador.contexto.close()

// --- as seis telas em 3 larguras e 2 temas ----------------------------------------------------
for (const largura of LARGURAS) {
  for (const tema of TEMAS) {
    // entrar (sem sessão)
    let { contexto, pagina } = await novoContexto(largura, tema)
    await pagina.goto(`${BASE}/entrar`)
    await conferir(pagina, 'entrar', largura, tema)
    await contexto.close()

    // mural e aviso aberto (morador comum: vê "Corrigido" no fixado)
    ;({ contexto, pagina } = await novoContexto(largura, tema))
    await entrar(pagina, COMUM)
    await pagina.waitForURL(/\/avisos$/)
    await pagina.getByText('Reunião da Comissão').waitFor()
    await conferir(pagina, 'mural', largura, tema)
    // U1: só na primeira rodada; depois o morador já abriu a correção (e o selo some, certo).
    if (largura === 320 && tema === 'claro') {
      const selo = await pagina.locator('a.fixado .selo').first().textContent()
      if (selo !== 'Corrigido') falhar(`U1: selo do fixado é "${selo}", esperado "Corrigido"`)
      const meta = await pagina.locator('a.fixado .linha-meta').textContent()
      if (!/corrigido em/.test(meta)) falhar(`U1: fixado sem "corrigido em": ${meta}`)
    }
    if (largura === 390 && tema === 'claro') {
      const fontes = await pagina.evaluate(() => ({
        aba: parseFloat(getComputedStyle(document.querySelector('.nav a')).fontSize),
        meta: parseFloat(getComputedStyle(document.querySelector('.item .linha-meta')).fontSize),
      }))
      if (fontes.aba < 15 || fontes.meta < 15) falhar(`U10: fontes pequenas ${JSON.stringify(fontes)}`)
    }
    await pagina.goto(`${BASE}/avisos/${fixado.id}`)
    await pagina.getByRole('heading', { level: 1, name: fixado.titulo }).waitFor()
    if (!(await pagina.title()).startsWith(fixado.titulo)) falhar(`U9: título da aba: ${await pagina.title()}`)
    await conferir(pagina, 'aviso', largura, tema)

    // minha unidade (com a confirmação de apagar aberta, U2)
    await pagina.goto(`${BASE}/minha-unidade`)
    await pagina.getByRole('button', { name: 'Apagar meus dados' }).waitFor()
    await conferir(pagina, 'minha-unidade', largura, tema)
    await pagina.getByRole('button', { name: 'Apagar meus dados' }).click()
    await pagina.waitForTimeout(700)
    const u2 = await pagina.evaluate(() => {
      const bloco = document.querySelector('.acesso-confirmar').getBoundingClientRect()
      const nav = document.querySelector('.nav')?.getBoundingClientRect()
      const topo = document.querySelector('.topo')?.getBoundingClientRect()
      const fundo = nav && nav.top < window.innerHeight && getComputedStyle(document.querySelector('.nav')).display !== 'none' && nav.width < window.innerWidth + 1 && nav.height < 200 ? nav.top : window.innerHeight
      return { topo: bloco.top, fundo: bloco.bottom, limiteBaixo: fundo, limiteCima: topo?.bottom ?? 0, altura: window.innerHeight }
    })
    // O bloco inteiro cabe? Se for maior que a tela, ao menos o título fica visível.
    const cabe = u2.fundo - u2.topo <= u2.limiteBaixo - u2.limiteCima
    if (cabe && (u2.topo < u2.limiteCima - 1 || u2.fundo > u2.limiteBaixo + 1)) {
      falhar(`U2 ${largura} ${tema}: confirmação de apagar coberta ${JSON.stringify(u2)}`)
    }
    await conferir(pagina, 'minha-unidade-apagar', largura, tema, { axe: false })
    await contexto.close()

    // primeiro acesso (unidade não ativada)
    ;({ contexto, pagina } = await novoContexto(largura, tema))
    await entrar(pagina, NAO_ATIVADA)
    await pagina.waitForURL(/primeiro-acesso/)
    await pagina.getByRole('button', { name: 'Salvar e entrar' }).waitFor()
    await conferir(pagina, 'primeiro-acesso', largura, tema)
    await contexto.close()

    // ficha do admin (e-mail longo, U4)
    ;({ contexto, pagina } = await novoContexto(largura, tema))
    await entrar(pagina, ADMIN)
    await pagina.waitForURL(/\/avisos/)
    await pagina.goto(`${BASE}/unidades/${COMUM}`)
    await pagina.getByRole('heading', { name: 'Voltar para a senha inicial' }).waitFor()
    await conferir(pagina, 'ficha', largura, tema)
    await contexto.close()
  }
}

// --- U5: quem leu (Comissão), com axe ---------------------------------------------------------
for (const largura of [320, 390, 1366]) {
  const { contexto, pagina } = await novoContexto(largura, 'claro')
  await entrar(pagina, COMISSAO)
  await pagina.waitForURL(/\/avisos/)
  await pagina.goto(`${BASE}/avisos/${comum.id}/leitura`)
  await pagina.getByRole('heading', { name: /Ainda não entrou no Portal/ }).waitFor()
  await conferir(pagina, 'quem-leu', largura, 'claro')
  await contexto.close()
}

// --- U2: recado não cobre "Tirar papel de Comissão" nem "Novo aviso" (celular) -----------------
{
  const { contexto, pagina } = await novoContexto(390, 'claro')
  await entrar(pagina, ADMIN)
  await pagina.waitForURL(/\/avisos/)
  await pagina.goto(`${BASE}/unidades/1105`)
  await pagina.getByRole('button', { name: 'Dar papel de Comissão' }).click()
  const tirar = pagina.getByRole('button', { name: 'Tirar papel de Comissão' })
  await tirar.waitFor()
  await pagina.locator('.recado.on').waitFor()
  await pagina.waitForTimeout(300)
  const sobrepoe = await pagina.evaluate(() => {
    const a = document.querySelector('.recado.on').getBoundingClientRect()
    const b = [...document.querySelectorAll('button')]
      .find((x) => x.textContent.includes('Tirar papel de Comissão'))
      .getBoundingClientRect()
    return !(a.bottom <= b.top || a.top >= b.bottom || a.right <= b.left || a.left >= b.right)
  })
  if (sobrepoe) falhar('U2: recado cobre "Tirar papel de Comissão"')
  await pagina.screenshot({ path: `${PRINTS}/u2-recado-ficha-390-claro.png` })
  await pagina.getByRole('button', { name: 'Tirar papel de Comissão' }).click()

  await pagina.goto(`${BASE}/avisos`)
  await pagina.locator('.flutuante').waitFor()
  const fab = await pagina.evaluate(() => {
    const r = document.querySelector('.recado')
    r.textContent = 'Aviso publicado.'
    r.classList.add('on')
    const a = r.getBoundingClientRect()
    const b = document.querySelector('.flutuante').getBoundingClientRect()
    return !(a.bottom <= b.top || a.top >= b.bottom || a.right <= b.left || a.left >= b.right)
  })
  if (fab) falhar('U2: recado cobre "Novo aviso"')
  await pagina.screenshot({ path: `${PRINTS}/u2-recado-mural-390-claro.png` })
  // O fim do mural rola até acima do botão flutuante.
  await pagina.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
  const fim = await pagina.evaluate(() => {
    const ultimo = document.querySelector('.avisos-arquivados').getBoundingClientRect()
    const b = document.querySelector('.flutuante').getBoundingClientRect()
    return ultimo.bottom <= b.top
  })
  if (!fim) falhar('U2: "Ver os avisos arquivados" fica embaixo do "Novo aviso"')
  await contexto.close()
}

// --- U3: faltam N tentativas e o horário do bloqueio -----------------------------------------
{
  const { contexto, pagina } = await novoContexto(390, 'claro')
  for (let i = 1; i <= 5; i++) {
    await entrar(pagina, '1302', 'senha-errada')
    await pagina.getByRole('alert').waitFor()
    const texto = await pagina.getByRole('alert').textContent()
    if (i === 3 && !/Faltam 2 tentativas/.test(texto)) falhar(`U3: 3º erro sem "Faltam 2": ${texto}`)
    if (i === 3) await pagina.screenshot({ path: `${PRINTS}/u3-terceiro-erro-390-claro.png` })
    if (i === 5 && !/Tente de novo às \d{2}h\d{2}/.test(texto)) falhar(`U3: bloqueio sem horário: ${texto}`)
  }
  await pagina.screenshot({ path: `${PRINTS}/u3-bloqueio-390-claro.png` })
  await pagina.getByRole('button', { name: 'Mostrar senha' }).click()
  if ((await pagina.getByLabel('Senha', { exact: true }).getAttribute('type')) !== 'text') {
    falhar('U3: "Mostrar senha" não mostrou')
  }
  await contexto.close()
}

await navegador.close()
console.log(problemas.length ? `\n${problemas.length} problema(s).` : '\nTudo certo.')
process.exit(problemas.length ? 1 : 0)
