// M4 · ajustes das revisões finais: regras de CSS que o jsdom não desenha, conferidas no texto
// dos arquivos (os prints em 390 e 1280 px, claro e escuro, conferem o resto). Cada teste falhava
// antes da correção. Rodar: npm test
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { describe, test } from 'node:test'

const ler = (caminho: string) => readFileSync(new URL(`../src/${caminho}`, import.meta.url), 'utf8')
const estilo = ler('estilo.css')
const enquetes = ler('enquetes/votar/enquetes.css')
const gestao = ler('enquetes/gestao/gestao.css')

/** O bloco `{ … }` da primeira regra cujo seletor é exatamente `seletor`. */
function regra(css: string, seletor: string): string {
  const escapado = seletor.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const achado = new RegExp(`(^|\\n)\\s*${escapado}\\s*\\{([^}]*)\\}`).exec(css)
  return achado ? achado[2] : ''
}

function token(bloco: string, nome: string): string {
  const achado = new RegExp(`--${nome}:\\s*(#[0-9a-fA-F]{6})`).exec(bloco)
  assert.ok(achado, `token --${nome} não achado`)
  return achado[1]
}

function luminancia(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

function contraste(a: string, b: string): number {
  const [x, y] = [luminancia(a), luminancia(b)].sort((m, n) => n - m)
  return (x + 0.05) / (y + 0.05)
}

describe('8: o recado não fica por cima do conteúdo', () => {
  test('sem posição fixa: ocupa uma linha do topo', () => {
    assert.ok(regra(estilo, '.recado'), 'regra .recado não achada')
    assert.doesNotMatch(regra(estilo, '.recado'), /position:\s*fixed/)
    assert.match(regra(estilo, '.topo'), /flex-wrap:\s*wrap/)
    assert.match(regra(estilo, '.recado-lugar'), /flex-basis:\s*100%/)
  })
})

describe('7: botão desligado', () => {
  const claro = regra(estilo, ':root')
  const escuro = regra(estilo, ":root[data-tema='escuro']")

  test('tem fundo e texto próprios, não só transparência', () => {
    const desligado = regra(estilo, '.botao:disabled,\n.botao:disabled:hover')
    assert.match(desligado, /background:\s*var\(--desligado-fundo\)/)
    assert.match(desligado, /color:\s*var\(--desligado-tinta\)/)
    assert.doesNotMatch(desligado, /opacity/)
  })

  for (const [nome, tema] of [
    ['claro', claro],
    ['escuro', escuro],
  ]) {
    test(`no tema ${nome}, o texto se lê e o fundo é bem diferente do verde`, () => {
      const fundo = token(tema, 'desligado-fundo')
      assert.ok(contraste(token(tema, 'desligado-tinta'), fundo) >= 4.5)
      assert.ok(contraste(token(tema, 'mata'), fundo) >= 2)
    })
  }
})

describe('telas de enquete', () => {
  test('19: "ainda não votou" na cor de atenção', () => {
    assert.match(regra(enquetes, '.selo.enq-falta'), /var\(--ipe/)
  })

  test('18: no computador, 8 por linha e o andar novo começa a linha', () => {
    // 900 px = 56.25em desde o M5 (media query em em, que acompanha a letra).
    assert.match(enquetes, /@media \(min-width: 56\.25em\)\s*\{[^@]*\.enq-grade\s*\{[^}]*repeat\(8,/)
    assert.match(regra(enquetes, '.enq-andar-novo'), /grid-column-start:\s*1/)
  })

  test('21: no celular, dia e hora do término têm espaço entre eles', () => {
    // Em rem desde o M5 (letra que cresce): 1rem = 16 px com a letra de fábrica.
    const gap = /gap:\s*([\d.]+)rem/.exec(regra(gestao, '.enq-lado'))
    assert.ok(gap && Number(gap[1]) >= 1, `gap do .enq-lado: ${gap?.[0]}`)
  })
})
