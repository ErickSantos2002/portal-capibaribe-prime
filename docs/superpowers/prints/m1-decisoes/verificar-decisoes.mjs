// Verificação das decisões do fim do M1 no navegador: Chrome headless, contexto isolado por
// rodada. 320, 390 e 1366 px; claro e escuro; CSP; rolagem lateral; axe no painel e na ficha
// como Comissão, na ficha como admin (e na confirmação de dar Comissão), em Minha unidade (com a
// ajuda do celular) e na política de privacidade. Banco portal_m1_decisoes, API 8130,
// preview 5130 (PORTAL_API_URL=http://127.0.0.1:8130 npx vite preview --port 5130).
//
// Uso: node verificar-decisoes.mjs <pasta-dos-prints>  (com playwright e @axe-core/playwright)
import { chromium } from 'playwright'
import { AxeBuilder } from '@axe-core/playwright'
import { mkdirSync } from 'node:fs'

const BASE = 'http://localhost:5130'
const PRINTS = process.argv[2]
mkdirSync(PRINTS, { recursive: true })

// Dados fictícios (semente fixa): 1002 admin, 1003 e 1006 Comissão, 1101 comum com e-mail.
const ADMIN = '1002'
const COMISSAO = '1003'
const ALVO = '1006'
const COMUM = '1101'
const SENHA = 'mudar123'
const LARGURAS = [320, 390, 1366]
const TEMAS = ['claro', 'escuro']

const problemas = []
const falhar = (msg) => {
  problemas.push(msg)
  console.log('PROBLEMA:', msg)
}
const conferirQue = (ok, msg) => (ok ? console.log('ok:', msg) : falhar(msg))

const visivel = (local) =>
  local.waitFor({ timeout: 5000 }).then(
    () => true,
    () => false,
  )

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

async function entrar(pagina, login) {
  await pagina.goto(`${BASE}/entrar`)
  await pagina.getByRole('radio', { name: `Bloco ${login[0]}` }).check({ force: true })
  await pagina.getByLabel('Apartamento').fill(login.slice(1))
  await pagina.getByLabel('Senha', { exact: true }).fill(SENHA)
  await pagina.getByRole('button', { name: 'Entrar' }).click()
  await pagina.waitForURL(/\/avisos/)
}

async function conferir(pagina, nome, largura, tema) {
  await pagina.waitForLoadState('networkidle')
  await pagina.waitForTimeout(150)
  const { sw, iw } = await pagina.evaluate(() => ({
    sw: document.documentElement.scrollWidth,
    iw: window.innerWidth,
  }))
  if (sw > iw) falhar(`${nome} ${largura} ${tema}: rolagem lateral (${sw} > ${iw})`)
  const csp = await pagina.evaluate(() => window.__csp)
  if (csp.length) falhar(`${nome} ${largura} ${tema}: CSP ${csp.join('; ')}`)
  const r = await new AxeBuilder({ page: pagina }).analyze()
  console.log(`axe ${nome} ${largura} ${tema}: ${r.passes.length} ok, ${r.violations.length} violações`)
  for (const v of r.violations) {
    falhar(`${nome} ${largura} ${tema}: axe ${v.id} (${v.impact}) ${v.nodes.length}x ${v.nodes[0]?.target}`)
  }
  await pagina.screenshot({ path: `${PRINTS}/${nome}-${largura}-${tema}.png`, fullPage: true })
}

// --- checagens de permissão (uma vez) ---------------------------------------------------------
{
  const { contexto, pagina } = await novoContexto(390, 'claro')
  await entrar(pagina, COMISSAO)
  const menu = pagina.getByRole('navigation', { name: 'Seções do Portal' })
  conferirQue(await menu.getByText('Unidades').count() > 0, 'menu da Comissão tem "Unidades"')
  const req = (metodo, caminho, corpo) =>
    pagina.request.fetch(`${BASE}${caminho}`, {
      method: metodo,
      headers: { 'X-Portal': '1', 'Content-Type': 'application/json' },
      data: corpo ? JSON.stringify(corpo) : undefined,
    })
  conferirQue((await req('GET', '/api/admin/unidades')).status() === 200, 'Comissão lê o painel (200)')
  conferirQue((await req('GET', `/api/admin/unidades/${ALVO}`)).status() === 200, 'Comissão lê a ficha (200)')
  conferirQue((await req('POST', `/api/admin/unidades/${COMUM}/resetar`, { confirmo: true })).status() === 403, 'Comissão não volta senha (403)')
  conferirQue((await req('PUT', `/api/admin/unidades/${COMUM}/papeis/comissao`)).status() === 403, 'Comissão não dá papel (403)')
  conferirQue((await req('DELETE', `/api/admin/unidades/${ALVO}/papeis/comissao`)).status() === 403, 'Comissão não tira papel (403)')
  conferirQue((await req('GET', '/api/admin/historico')).status() === 403, 'Comissão não lê o histórico (403)')
  await pagina.goto(`${BASE}/historico`)
  conferirQue(await visivel(pagina.getByRole('heading', { name: 'Sem permissão' })), 'tela do histórico: "Sem permissão" para a Comissão')

  // "Para a gestão" no aviso aberto (avisos 13)
  const aviso = await (await req('POST', '/api/avisos', { titulo: 'Reunião da Comissão', texto: 'Pauta: obra.', para_todos: true })).json()
  await pagina.goto(`${BASE}/avisos/${aviso.id}`)
  conferirQue(await visivel(pagina.getByRole('heading', { level: 2, name: 'Para a gestão' })), 'aviso aberto: "Para a gestão"')
  await contexto.close()
}

for (const largura of LARGURAS) {
  for (const tema of TEMAS) {
    // privacidade (sem sessão)
    let { contexto, pagina } = await novoContexto(largura, tema)
    await pagina.goto(`${BASE}/privacidade`)
    await pagina.getByRole('heading', { name: 'Quem cuida dos dados' }).waitFor()
    await conferir(pagina, 'privacidade', largura, tema)
    await contexto.close()

    // Comissão: painel (grade e lista) e ficha, só leitura
    ;({ contexto, pagina } = await novoContexto(largura, tema))
    await entrar(pagina, COMISSAO)
    await pagina.goto(`${BASE}/unidades`)
    await pagina.getByText(/Bloco 1: \d+ de/).waitFor()
    if (await pagina.getByRole('link', { name: 'Histórico de ações' }).count()) {
      falhar(`painel da Comissão ${largura} ${tema}: link do histórico aparece`)
    }
    await conferir(pagina, 'painel-comissao', largura, tema)
    await pagina.getByRole('button', { name: 'Lista com contatos' }).click()
    await pagina.getByText('(81) 9 0000-0000').first().waitFor()
    await conferir(pagina, 'painel-lista-comissao', largura, tema)
    await pagina.goto(`${BASE}/unidades/${ALVO}`)
    await pagina.getByText('Só a administração do Portal volta').waitFor()
    const botoes = await pagina.getByRole('button').allTextContents()
    if (botoes.some((b) => /senha inicial|papel/i.test(b))) {
      falhar(`ficha da Comissão ${largura} ${tema}: botão de ação aparece (${botoes.join(', ')})`)
    }
    await conferir(pagina, 'ficha-comissao', largura, tema)
    await contexto.close()

    // admin: ficha e confirmação de dar Comissão (sem confirmar)
    ;({ contexto, pagina } = await novoContexto(largura, tema))
    await entrar(pagina, ADMIN)
    await pagina.goto(`${BASE}/unidades/${COMUM}`)
    await pagina.getByRole('button', { name: 'Dar papel de Comissão' }).waitFor()
    await conferir(pagina, 'ficha-admin', largura, tema)
    await pagina.getByRole('button', { name: 'Dar papel de Comissão' }).click()
    await pagina.getByText('Ele passa a ver o celular e o e-mail de todas as unidades.').waitFor()
    await conferir(pagina, 'ficha-admin-confirmar-comissao', largura, tema)
    await contexto.close()

    // minha unidade, com o formulário aberto (ajuda do celular)
    ;({ contexto, pagina } = await novoContexto(largura, tema))
    await entrar(pagina, COMUM)
    await pagina.goto(`${BASE}/minha-unidade`)
    await pagina.getByRole('button', { name: 'Mudar meus dados' }).click()
    await pagina.getByText('pela Comissão e pela administração do Portal', { exact: false }).waitFor()
    await conferir(pagina, 'minha-unidade-dados', largura, tema)
    await contexto.close()
  }
}

await navegador.close()
console.log(problemas.length ? `\n${problemas.length} problema(s)` : '\nnenhum problema')
process.exit(problemas.length ? 1 : 0)
