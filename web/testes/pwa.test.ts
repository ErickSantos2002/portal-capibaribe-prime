// PWA (M2, H-05): o build servido pelo `vite preview` entrega o service worker como JavaScript
// (e não o index.html do rewrite), o manifest válido e a linha do manifest no index.html.
// Rodar depois do `npm run build`: npm test
import assert from 'node:assert/strict'
import { after, before, test } from 'node:test'
import { preview, type PreviewServer } from 'vite'

interface Manifest {
  name: string
  short_name?: string
  start_url: string
  scope: string
  display: string
  theme_color: string
  background_color: string
  lang: string
  icons: { src: string; sizes: string }[]
}

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

test('/sw.js sai como JavaScript, sem cache de páginas', async () => {
  const resposta = await fetch(new URL('sw.js', base))
  assert.equal(resposta.status, 200)
  assert.match(resposta.headers.get('content-type') ?? '', /javascript/)
  const codigo = await resposta.text()
  assert.ok(!codigo.includes('<!doctype'), 'veio o index.html em vez do sw.js')
  assert.ok(codigo.includes("addEventListener('push'"))
  assert.ok(!codigo.includes("addEventListener('fetch'"), 'o sw não intercepta requisições')
  assert.ok(!/caches\./.test(codigo), 'o sw não usa a Cache API')
})

test('manifest com nome, início no mural, janela própria, cores e ícones', async () => {
  const resposta = await fetch(new URL('manifest.webmanifest', base))
  assert.equal(resposta.status, 200)
  const manifest = (await resposta.json()) as Manifest
  assert.equal(manifest.name, 'Portal Capibaribe Prime')
  assert.ok(manifest.short_name && manifest.short_name.length <= 12)
  assert.equal(manifest.start_url, '/avisos')
  assert.equal(manifest.scope, '/')
  assert.equal(manifest.display, 'standalone')
  assert.equal(manifest.theme_color, '#1f5e3b')
  assert.equal(manifest.background_color, '#f4f6f2')
  assert.equal(manifest.lang, 'pt-BR')
  const tamanhos = manifest.icons.map((i) => i.sizes).sort()
  assert.deepEqual(tamanhos, ['192x192', '512x512'])
  for (const icone of manifest.icons) {
    const arquivo = await fetch(new URL(icone.src.slice(1), base))
    assert.equal(arquivo.status, 200, icone.src)
    assert.equal(arquivo.headers.get('content-type'), 'image/png', icone.src)
  }
})

test('index.html aponta para o manifest e dá nome ao ícone do iPhone', async () => {
  const html = await (await fetch(base)).text()
  assert.ok(html.includes('<link rel="manifest" href="/manifest.webmanifest"'))
  assert.ok(html.includes('<meta name="apple-mobile-web-app-title"'))
})
