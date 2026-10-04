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

test('a fonte vem do próprio Portal, não de terceiros', async () => {
  const resposta = await fetch(base)
  const html = await resposta.text()
  const css = html.match(/href="([^"]+\.css)"/)?.[1]
  assert.ok(css, 'build sem CSS')
  const estilo = await (await fetch(new URL(css, base))).text()
  assert.match(estilo, /Atkinson Hyperlegible/)
  assert.doesNotMatch(estilo, /fonts\.(googleapis|gstatic)\.com/)
})
