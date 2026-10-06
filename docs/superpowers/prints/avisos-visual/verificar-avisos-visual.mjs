// Verificação dos avisos com formatação, categoria e evento no navegador: Chrome headless,
// contexto isolado por rodada. 320, 390 e 1366 px; claro e escuro; CSP; rolagem lateral; axe no
// mural, no aviso aberto (com evento, sem evento, com versão antiga) e no formulário (escrevendo
// e na prévia); categoria pelas setas do teclado. Banco portal_avisos_visual, API 8140,
// preview 5140 (PORTAL_API_URL=http://127.0.0.1:8140 npx vite preview --port 5140).
//
// Uso: node verificar-avisos-visual.mjs <pasta-dos-prints>  (com playwright e @axe-core/playwright)
import { chromium } from 'playwright'
import { AxeBuilder } from '@axe-core/playwright'
import { mkdirSync } from 'node:fs'

const BASE = 'http://localhost:5140'
const PRINTS = process.argv[2]
mkdirSync(PRINTS, { recursive: true })

// Dados fictícios (semente fixa): 1003 Comissão, 1101 comum.
const COMISSAO = '1003'
const COMUM = '1101'
const SENHA = 'mudar123'
const LARGURAS = [320, 390, 1366]
const TEMAS = ['claro', 'escuro']

const BOAS_VINDAS = `Olá, vizinhos! Este é um espaço só nosso para os avisos do condomínio: o que é importante **não se perde mais no grupo**.

## Como entrar
Cada apartamento tem **uma conta só**, usada pela família. Escolha o bloco, digite o apartamento e troque a senha inicial no primeiro acesso.

## O que já dá para fazer
- Ler os avisos da Comissão; os importantes ficam fixados no topo.
- Ver só o que é para o seu bloco.
- Saber quando um aviso foi **corrigido**.
- Em **Minha unidade**: dados, senha e aparelhos.

> Seu celular só é visto pela **Comissão** e pela administração. Detalhes em Privacidade.

Dúvida ou ideia? Fale com a Comissão ou mande no grupo.`

const problemas = []
const falhar = (msg) => {
  problemas.push(msg)
  console.log('PROBLEMA:', msg)
}
const conferirQue = (ok, msg) => (ok ? console.log('ok:', msg) : falhar(msg))

// pt-BR: os campos de dia e hora aparecem como no celular do morador (revisão UX 12).
const navegador = await chromium.launch({ channel: 'chrome', headless: true, args: ['--lang=pt-BR'] })

async function novoContexto(largura, tema) {
  const contexto = await navegador.newContext({
    viewport: { width: largura, height: largura < 900 ? 800 : 900 },
    locale: 'pt-BR',
    timezoneId: 'America/Recife',
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

// --- avisos fictícios das 5 categorias (uma vez, pela API, como a Comissão) --------------------
const ids = {}
{
  const { contexto, pagina } = await novoContexto(390, 'claro')
  await entrar(pagina, COMISSAO)
  const req = async (metodo, caminho, corpo) => {
    const r = await pagina.request.fetch(`${BASE}${caminho}`, {
      method: metodo,
      headers: { 'X-Portal': '1', 'Content-Type': 'application/json' },
      data: corpo ? JSON.stringify(corpo) : undefined,
    })
    return { status: r.status(), corpo: await r.json().catch(() => null) }
  }
  const existentes = (await req('GET', '/api/avisos')).corpo.itens
  const achar = (titulo) => existentes.find((a) => a.titulo === titulo)?.id
  async function garantir(chave, corpo) {
    ids[chave] = achar(corpo.titulo) ?? (await req('POST', '/api/avisos', corpo)).corpo.id
  }
  await garantir('reajuste', {
    titulo: 'Reajuste do INCC de setembro',
    texto: 'O índice de setembro foi **0,42%**. A parcela de outubro já vem corrigida.\n\nDetalhes: https://www.caixa.gov.br',
    para_todos: true,
    categoria: 'financeiro',
  })
  await garantir('assembleia', {
    titulo: 'Assembleia de instalação (resumo)',
    texto: 'Obrigado a todos que foram.\n\n1. Eleição da Comissão\n2. Cronograma da obra\n3. Taxa de condomínio',
    para_todos: true,
    categoria: 'reuniao',
    evento: { quando: '2026-10-03T19:00:00-03:00' },
  })
  await garantir('vistoria', {
    titulo: 'Vistoria da obra no sábado',
    texto: 'A construtora liberou uma **visita guiada** às áreas comuns do Bloco 3.\n\n## O que levar\n- Documento com foto.\n- Sapato fechado (obrigatório).\n\n> **Vagas limitadas:** confirme no grupo até quinta.',
    para_todos: true,
    categoria: 'obra',
    evento: { quando: '2027-10-09T09:00:00-03:00', onde: 'Stand de vendas, na entrada da obra' },
  })
  if (!achar('Prazo do contrato com a Caixa')) {
    await garantir('prazo', {
      titulo: 'Prazo do contrato com a Caixa',
      texto: 'Assinatura até **sexta**. Leve os documentos.',
      para_todos: true,
      categoria: 'geral',
    })
    const corrigido = await req('PUT', `/api/avisos/${ids.prazo}`, {
      titulo: 'Prazo do contrato com a Caixa',
      texto: 'Assinatura até **sexta, às 17h**.\n\n- RG e CPF\n- Comprovante de residência',
      categoria: 'urgente',
    })
    conferirQue(corrigido.status === 200, 'correção do aviso urgente (200)')
  } else ids.prazo = achar('Prazo do contrato com a Caixa')
  await garantir('boasvindas', {
    titulo: 'Bem-vindos ao Portal do Capibaribe Prime',
    texto: BOAS_VINDAS,
    para_todos: true,
    fixado: true,
    categoria: 'geral',
  })
  conferirQue(Object.values(ids).every(Boolean), `avisos fictícios prontos (${JSON.stringify(ids)})`)

  // Categoria e evento inválidos voltam 422; morador comum não publica (403).
  conferirQue(
    (await req('POST', '/api/avisos', { titulo: 'X', texto: 'Y', para_todos: true, categoria: 'festa' })).status === 422,
    'categoria inválida: 422',
  )
  conferirQue(
    (await req('POST', '/api/avisos', { titulo: 'X', texto: 'Y', para_todos: true, evento: { onde: 'Stand' } })).status === 422,
    'onde sem quando: 422',
  )
  await contexto.close()
}
{
  const { contexto, pagina } = await novoContexto(390, 'claro')
  await entrar(pagina, COMUM)
  const r = await pagina.request.fetch(`${BASE}/api/avisos`, {
    method: 'POST',
    headers: { 'X-Portal': '1', 'Content-Type': 'application/json' },
    data: JSON.stringify({ titulo: 'X', texto: 'Y', para_todos: true, categoria: 'urgente' }),
  })
  conferirQue(r.status() === 403, 'morador comum não publica (403)')
  // O texto formatado nunca vira HTML de fora: nenhum <script> nem <img> no aviso aberto.
  await pagina.goto(`${BASE}/avisos/${ids.boasvindas}`)
  await pagina.getByRole('heading', { level: 2, name: 'Como entrar' }).waitFor()
  conferirQue((await pagina.locator('.texto-aviso :is(script, img, iframe)').count()) === 0, 'texto do aviso sem script/img/iframe')
  await contexto.close()
}

// --- categoria pelas setas do teclado (rádio de verdade) ---------------------------------------
{
  const { contexto, pagina } = await novoContexto(390, 'claro')
  await entrar(pagina, COMISSAO)
  await pagina.goto(`${BASE}/avisos/novo`)
  await pagina.getByRole('radio', { name: 'Geral' }).focus()
  await pagina.keyboard.press('ArrowRight')
  await pagina.keyboard.press('ArrowRight')
  conferirQue(await pagina.getByRole('radio', { name: 'Reunião' }).isChecked(), 'categoria: setas do teclado escolhem "Reunião"')
  // A barra devolve o foco ao texto com a palavra selecionada.
  const texto = pagina.getByLabel('Texto do aviso')
  await texto.fill('Leve documento')
  await texto.evaluate((t) => t.setSelectionRange(5, 14))
  await pagina.getByRole('button', { name: 'Negrito' }).click()
  conferirQue((await texto.inputValue()) === 'Leve **documento**', 'barra: Negrito envolve a seleção')
  conferirQue(await texto.evaluate((t) => document.activeElement === t), 'barra: foco volta ao texto')
  await contexto.close()
}

for (const largura of LARGURAS) {
  for (const tema of TEMAS) {
    // morador: mural, aviso com evento, sem evento, boas-vindas, com versão antiga
    let { contexto, pagina } = await novoContexto(largura, tema)
    await entrar(pagina, COMUM)
    await pagina.getByRole('heading', { name: 'Vistoria da obra no sábado' }).waitFor()
    await conferir(pagina, 'mural', largura, tema)
    await pagina.goto(`${BASE}/avisos/${ids.vistoria}`)
    await pagina.locator('.aviso-evento').waitFor()
    await conferir(pagina, 'aviso-com-evento', largura, tema)
    await pagina.goto(`${BASE}/avisos/${ids.reajuste}`)
    await pagina.getByText('O índice de setembro', { exact: false }).waitFor()
    if (await pagina.locator('.aviso-evento').count()) falhar(`aviso sem evento ${largura} ${tema}: quadro aparece`)
    await conferir(pagina, 'aviso-sem-evento', largura, tema)
    await pagina.goto(`${BASE}/avisos/${ids.assembleia}`)
    await pagina.getByText('Já aconteceu', { exact: false }).waitFor()
    await conferir(pagina, 'aviso-evento-passado', largura, tema)
    await pagina.goto(`${BASE}/avisos/${ids.boasvindas}`)
    await pagina.getByRole('heading', { level: 2, name: 'Como entrar' }).waitFor()
    await conferir(pagina, 'aviso-boas-vindas', largura, tema)
    await pagina.goto(`${BASE}/avisos/${ids.prazo}`)
    await pagina.getByText('Ver como era antes').click()
    await pagina.locator('.avisos-versao').getByText('Geral').waitFor()
    await conferir(pagina, 'aviso-versao-antiga', largura, tema)
    await contexto.close()

    // Comissão: formulário escrevendo, "Ver como fica" e a prévia de publicar
    ;({ contexto, pagina } = await novoContexto(largura, tema))
    await entrar(pagina, COMISSAO)
    await pagina.goto(`${BASE}/avisos/novo`)
    await pagina.getByLabel('Título').fill('Mutirão de limpeza do stand')
    await pagina.getByText('Obra', { exact: true }).click()
    await pagina.getByLabel('Texto do aviso').fill(
      'Vamos ajudar a deixar o stand **pronto** para a vistoria.\n\n## O que levar\n- Luvas\n- Água\n\n> Crianças só com um adulto.',
    )
    await pagina.getByLabel('É um evento? (reunião, vistoria, mutirão)').check()
    await pagina.getByLabel('Dia').fill('2027-10-16')
    await pagina.getByLabel('Hora').fill('08:30')
    await pagina.getByLabel('Onde (se quiser)').fill('Stand de vendas')
    await conferir(pagina, 'formulario-escrevendo', largura, tema)
    await pagina.getByRole('button', { name: 'Ver como fica' }).click()
    await pagina.locator('.avisos-como-fica').getByRole('heading', { name: 'O que levar' }).waitFor()
    await conferir(pagina, 'formulario-ver-como-fica', largura, tema)
    await pagina.getByRole('button', { name: 'Voltar a escrever' }).click()
    await pagina.getByRole('button', { name: 'Ver prévia' }).click()
    await pagina.getByText('Prévia: assim vai aparecer no mural').waitFor()
    await conferir(pagina, 'formulario-previa', largura, tema)
    await contexto.close()
  }
}

await navegador.close()
console.log(problemas.length ? `\n${problemas.length} problema(s)` : '\nnenhum problema')
process.exit(problemas.length ? 1 : 0)
