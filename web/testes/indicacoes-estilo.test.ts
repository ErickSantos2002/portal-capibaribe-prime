// Indicações · revisão: regras de CSS que o jsdom não desenha, conferidas no texto dos arquivos
// (a conferência visual headless confere o resto). Cada teste falhava antes da correção.
// Rodar: npm test (ou node --test testes/indicacoes-estilo.test.ts, de web/)
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { describe, test } from 'node:test'

const ler = (caminho: string) => readFileSync(new URL(`../src/${caminho}`, import.meta.url), 'utf8')
const estilo = ler('estilo.css')
const indicacoes = ler('indicacoes/indicacoes.css').replace(/\/\*[\s\S]*?\*\//g, '')

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

describe('faixa de categorias', () => {
  test('rola para o lado dentro dela, também com a letra grande (não quebra em linhas)', () => {
    assert.match(regra(indicacoes, '.faixa-categorias'), /overflow-x:\s*auto/)
    assert.match(regra(indicacoes, '.faixa-categorias'), /flex-wrap:\s*nowrap/)
    // Com a letra grande, nada de quebrar em linhas nem de soltar a rolagem.
    for (const m of indicacoes.matchAll(/data-letra='grande'\]\s*\.faixa-categorias[^{]*\{([^}]*)\}/g)) {
      assert.doesNotMatch(m[1], /flex-wrap:\s*wrap|overflow-x:\s*visible|white-space:\s*normal/)
    }
  })
})

describe('o primeiro cartão na primeira tela, com a letra grande', () => {
  // A 320 px e 200 %, o cartão ficava logo abaixo da dobra (y = 715 numa janela de 780). Medido
  // depois: y = 581, acima das abas de baixo (698).
  test('o rótulo da busca sem o respiro de grupo; sem o ícone e a faixa mais baixa na letra grande', () => {
    assert.match(regra(indicacoes, '.ind-busca label'), /margin-top:\s*0/)
    assert.match(regra(indicacoes, ":root[data-letra='grande'] .ind-busca label svg"), /display:\s*none/)
    assert.match(regra(indicacoes, ":root[data-letra='grande'] .faixa-categorias .chip"), /min-height:\s*0/)
  })
})

describe('categoria do prestador', () => {
  test('usa --ipe-texto, não --ipe-forte', () => {
    assert.match(regra(indicacoes, '.ind-categoria'), /color:\s*var\(--ipe-texto\)/)
  })

  for (const [nome, tema] of [
    ['claro', regra(estilo, ':root')],
    ['escuro', regra(estilo, ":root[data-tema='escuro']")],
  ]) {
    test(`no tema ${nome}, --ipe-texto tem 4,5:1 no papel, na folha e no ipê-suave`, () => {
      for (const fundo of ['papel', 'folha', 'ipe-suave']) {
        const valor = contraste(token(tema, 'ipe-texto'), token(tema, fundo))
        assert.ok(valor >= 4.5, `--ipe-texto sobre --${fundo}: ${valor.toFixed(2)}:1`)
      }
    })
  }
})

describe('telefone', () => {
  test('o número não quebra no meio', () => {
    assert.match(regra(indicacoes, '.ind-numero'), /white-space:\s*nowrap/)
    assert.doesNotMatch(regra(indicacoes, '.ind-contatos .botao'), /overflow-wrap:\s*anywhere/)
  })
})
