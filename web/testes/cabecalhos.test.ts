// Cabeçalhos de segurança: os mesmos do vercel.json, aplicados pelo `vite preview` ao build.
// Rodar depois do `npm run build`: npm test
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { after, before, test } from 'node:test'
import { preview, type PreviewServer } from 'vite'
import { cabecalhosDoVercel } from '../cabecalhos.ts'

const raiz = new URL('..', import.meta.url).pathname
let servidor: PreviewServer
let base: string

before(async () => {
  servidor = await preview({ root: raiz, preview: { port: 0, host: '127.0.0.1' }, logLevel: 'silent' })
  base = servidor.resolvedUrls!.local[0]
})

after(async () => {
  await servidor.close()
})

test('o vercel.json traz a CSP e a Permissions-Policy combinadas', () => {
  const cabecalhos = cabecalhosDoVercel()
  const csp = cabecalhos['Content-Security-Policy']
  assert.ok(csp, 'falta Content-Security-Policy')
  for (const diretiva of [
    "default-src 'self'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
  ]) {
    assert.ok(csp.includes(diretiva), `CSP sem ${diretiva}`)
  }
  const permissoes = cabecalhos['Permissions-Policy']
  assert.ok(permissoes, 'falta Permissions-Policy')
  for (const recurso of ['camera=()', 'microphone=()', 'geolocation=()']) {
    assert.ok(permissoes.includes(recurso), `Permissions-Policy sem ${recurso}`)
  }
})

/** Fontes que valem para uma diretiva, seguindo o recuo da CSP 3 até a `default-src`. */
function fontesEfetivas(csp: string, cadeia: string[]): string[] {
  const diretivas = new Map(
    csp.split(';').map((d) => {
      const [nome, ...fontes] = d.trim().split(/\s+/)
      return [nome, fontes] as const
    }),
  )
  for (const nome of cadeia) {
    const fontes = diretivas.get(nome)
    if (fontes) return fontes
  }
  return ['*']
}

test('a CSP deixa o service worker e o manifest do PWA (M2) virem do próprio Portal', () => {
  // Spec do M2, seção 8: worker-src recua para child-src, script-src e default-src;
  // manifest-src recua para default-src. Com default-src 'self' os dois já valem, sem mudar a
  // CSP. Se alguém endurecer uma diretiva da cadeia, este teste lembra do /sw.js.
  const csp = cabecalhosDoVercel()['Content-Security-Policy']
  const worker = fontesEfetivas(csp, ['worker-src', 'child-src', 'script-src', 'default-src'])
  const manifest = fontesEfetivas(csp, ['manifest-src', 'default-src'])
  assert.ok(worker.includes("'self'"), `worker-src efetivo: ${worker.join(' ')}`)
  assert.ok(manifest.includes("'self'"), `manifest-src efetivo: ${manifest.join(' ')}`)
  // O push não passa pela CSP (quem fala com o serviço de push é o navegador), e o toque na
  // notificação abre uma página do próprio Portal: nada de terceiros é liberado.
  assert.doesNotMatch(csp, /https?:\/\//, 'CSP com endereço de terceiros')
})

test('o vite preview responde com os mesmos cabeçalhos do vercel.json', async () => {
  const resposta = await fetch(base)
  assert.equal(resposta.status, 200)
  for (const [nome, valor] of Object.entries(cabecalhosDoVercel())) {
    assert.equal(resposta.headers.get(nome), valor, nome)
  }
})

test('o HTML do build não tem script nem estilo embutido (a CSP bloquearia)', async () => {
  const html = await readFile(new URL('../dist/index.html', import.meta.url), 'utf8')
  assert.doesNotMatch(html, /<script(?![^>]*\bsrc=)[^>]*>/i, 'script embutido')
  assert.doesNotMatch(html, /<style[\s>]/i, 'style embutido')
  assert.doesNotMatch(html, /\sstyle=/i, 'atributo style')
  assert.doesNotMatch(html, /https?:\/\/(?!www\.w3\.org)/i, 'recurso de terceiros')
})

test('o tema escolhido é aplicado por arquivo próprio, antes do React', async () => {
  const html = await readFile(new URL('../dist/index.html', import.meta.url), 'utf8')
  const tema = html.indexOf('<script src="/tema.js">')
  assert.ok(tema > 0, 'index.html sem /tema.js')
  assert.ok(tema < html.indexOf('type="module"'), '/tema.js precisa vir antes do app')
  const resposta = await fetch(new URL('/tema.js', base))
  assert.equal(resposta.status, 200)
  assert.match(await resposta.text(), /portal-tema/)
})

test('o ícone do Portal: favicon e tela inicial, servidos pelo próprio site', async () => {
  const html = await readFile(new URL('../dist/index.html', import.meta.url), 'utf8')
  const icones: [RegExp, string, string][] = [
    [/<link rel="icon" href="\/favicon\.ico" sizes="48x48"/, '/favicon.ico', 'image/'],
    [/<link rel="apple-touch-icon" href="\/apple-touch-icon\.png"/, '/apple-touch-icon.png', 'image/png'],
  ]
  for (const [link, caminho, tipo] of icones) {
    assert.match(html, link, `index.html sem ${caminho}`)
    const resposta = await fetch(new URL(caminho, base))
    assert.equal(resposta.status, 200, caminho)
    assert.ok(resposta.headers.get('content-type')?.startsWith(tipo), `${caminho}: tipo errado`)
  }
  // Os ícones grandes ficam prontos para o PWA do M2.
  for (const caminho of ['/icon-192.png', '/icon-512.png']) {
    assert.equal((await fetch(new URL(caminho, base))).status, 200, caminho)
  }
  assert.doesNotMatch(html, /favicon\.svg/, 'o ícone antigo continua no index.html')
})

test('a fonte vem do próprio Portal, não de terceiros', async () => {
  const resposta = await fetch(base)
  const html = await resposta.text()
  const css = html.match(/href="([^"]+\.css)"/)?.[1]
  assert.ok(css, 'build sem CSS')
  const estilo = await (await fetch(new URL(css, base))).text()
  assert.match(estilo, /Atkinson Hyperlegible/)
  assert.doesNotMatch(estilo, /fonts\.(googleapis|gstatic)\.com/)
})
