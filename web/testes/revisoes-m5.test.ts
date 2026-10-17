// M5 · revisões da "letra que cresce" (docs/superpowers/duvidas-m5-letra.md, seção Revisões):
// as regras de CSS que o jsdom não desenha. A prova visual é o scripts/dev/conferir-letra.mjs;
// aqui fica a guarda de que cada regra está no lugar (cada teste falhava antes das revisões).
// Rodar: npm test
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { describe, test } from 'node:test'

const ler = (caminho: string) =>
  readFileSync(new URL(`../src/${caminho}`, import.meta.url), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '')
const estilo = ler('estilo.css')

function regra(css: string, seletor: string): string {
  const escapado = seletor.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const achado = new RegExp(`(^|\\n)${escapado}\\s*\\{([^}]*)\\}`).exec(css)
  return achado ? achado[2] : ''
}

function bloco(css: string, condicao: string): string {
  const inicio = css.indexOf(`${condicao} {`)
  if (inicio < 0) return ''
  let nivel = 0
  for (let i = css.indexOf('{', inicio); i < css.length; i++) {
    if (css[i] === '{') nivel++
    if (css[i] === '}' && --nivel === 0) return css.slice(inicio, i)
  }
  return ''
}

describe('R1: a letra grande também no iPhone (container query em rem e marcas no html)', () => {
  test('a página é o contêiner `raiz`', () => {
    assert.match(regra(estilo, '#root'), /container:\s*raiz \/ inline-size/)
  })

  test('o layout de computador pergunta à raiz, em rem', () => {
    assert.match(bloco(estilo, '@container raiz (min-width: 56.25rem)'), /\.app\s*\{[^}]*display:\s*grid/)
  })

  test('"O que mudou" numa tela baixa usa a marca data-altura', () => {
    assert.match(ler('sobre/sobre.css'), /:root\[data-altura='baixa'\] \.janela-caixa\s*\{[^}]*overflow-y:\s*auto/)
  })

  test('a régua de 1rem do detector existe e não aparece', () => {
    assert.match(regra(estilo, '.regua-letra'), /width:\s*1rem/)
    assert.match(regra(estilo, '.regua-letra'), /visibility:\s*hidden/)
  })
})

describe('R3: ícone com atributo em número e tamanho em rem pelo CSS', () => {
  test('.icone mede pela variável --icone', () => {
    assert.match(regra(estilo, '.icone'), /width:\s*var\(--icone\)/)
    assert.match(regra(estilo, '.icone'), /height:\s*var\(--icone\)/)
  })
})

describe('U4 e U5: menu lateral que rola; coluna de 45rem também no layout de celular', () => {
  test('o menu lateral rola quando não cabe na altura', () => {
    assert.match(bloco(estilo, '@container raiz (min-width: 56.25rem)'), /\.nav,\s*\.app\.detalhe \.nav\s*\{[^}]*overflow-y:\s*auto/)
  })

  test('conteúdo, topo e abas de baixo na coluna de 45rem, centralizada', () => {
    assert.match(regra(estilo, '.conteudo'), /padding:[^;]*max\(16px, calc\(\(100% - 45rem\) \/ 2\)\)/)
    assert.match(regra(estilo, '.topo'), /padding:[^;]*max\(16px, calc\(\(100% - 45rem\) \/ 2\)\)/)
    assert.match(regra(estilo, '.nav'), /padding-inline:\s*max\(0rem, calc\(\(100% - 45rem\) \/ 2\)\)/)
  })
})

describe('R5: cinco abas a 320 px e 200 % sem rolagem lateral', () => {
  test('na tela estreita, com cinco abas, o respiro lateral cai para a metade', () => {
    assert.match(
      bloco(estilo, '@container raiz (max-width: 22rem)'),
      /\.nav:has\(> a:nth-of-type\(5\)\) a\s*\{[^}]*padding-inline:\s*0\.0625rem/,
    )
  })
})

describe('U6, U7, U8, U9, U11 e o mural', () => {
  test('U6: telefone preso numa linha; ficha empilhada com letra grande', () => {
    assert.match(regra(estilo, '.fone-numero'), /white-space:\s*nowrap/)
    const fim = estilo.lastIndexOf('@container conteudo (max-width: 17.5rem)')
    const ficha = bloco(estilo.slice(fim), '@container conteudo (max-width: 17.5rem)')
    assert.match(ficha, /\.ficha dd\s*\{[^}]*text-align:\s*left/)
    // Depois da regra de base da ficha (mesmo peso: a última vence).
    assert.ok(fim > estilo.indexOf('\n.ficha dd {'), 'a ficha de letra grande vem antes da de base')
  })

  test('U7: hifenização só com letra grande', () => {
    assert.match(estilo, /:root\[data-letra='grande'\] :is\([^)]*h1[^)]*\)\s*\{[^}]*hyphens:\s*auto/)
  })

  test('U8: rótulo do andar só na grade de 4 colunas', () => {
    assert.match(regra(estilo, '.grade-andar'), /display:\s*none/)
    assert.ok(estilo.indexOf('\n.grade-andar {') < estilo.indexOf('@container conteudo (max-width: 19.75rem)'))
    assert.match(bloco(estilo, '@container conteudo (max-width: 19.75rem)'), /\.grade-andar\s*\{[^}]*display:\s*block/)
  })

  test('U9: caixa com ícone empilha com letra grande', () => {
    assert.match(bloco(estilo, '@container conteudo (max-width: 17.5rem)'), /\.aviso-caixa\s*\{[^}]*flex-direction:\s*column/)
  })

  test('U11: espaço entre grupos (1.5rem) maior que entre rótulo e campo', () => {
    assert.match(estilo, /--entre-grupos:\s*1\.5rem/)
    assert.match(regra(estilo, 'label'), /margin:\s*var\(--entre-grupos\) 0 0\.375rem/)
  })

  test('mural: resumo em até 3 linhas com letra grande', () => {
    assert.match(ler('avisos/avisos.css'), /:root\[data-letra='grande'\] :is\(\.cartao-resumo, \.fixado > p\)\s*\{[^}]*line-clamp:\s*3/)
  })
})
