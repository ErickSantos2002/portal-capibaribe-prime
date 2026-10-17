// M5 · letra que cresce (spec docs/superpowers/specs/m5-letra.md, seção 3): guarda automática da
// regra. Lê todo .css de web/src e falha se houver tamanho de letra em px, media query em px ou px
// fora das exceções permitidas. Os CSS dos épicos que ainda não foram convertidos estão em
// PENDENTES; quem converte um arquivo tira a linha dele daqui (plano m5-letra, tarefas G1 a G3).
// Rodar: npm test (ou node --test testes/letra.test.ts, de web/)
import assert from 'node:assert/strict'
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'
import { describe, test } from 'node:test'

const SRC = new URL('../src/', import.meta.url).pathname

/** Ainda em px: cada grupo apaga as suas linhas ao converter (e o teste passa a cobri-las). */
const PENDENTES = new Set([
  // G1
  // G2
  // G3
])

/** Propriedades que podem ter px sem justificar: espessura de linha, sombra e cantos (spec 3.3). */
const PROPRIEDADES_EM_PX = [
  /^border(-(top|right|bottom|left|block|inline)(-(start|end))?)?(-width)?$/,
  /^border(-(top|right|bottom|left|start|end)(-(left|right|start|end))?)?-radius$/,
  /^outline(-width|-offset)?$/,
  /^(box|text)-shadow$/,
  /^text-underline-offset$/,
  /^text-decoration-thickness$/,
]
/** Tokens de :root que são canto ou sombra (os mesmos casos de cima). */
const TOKENS_EM_PX = new Set(['--r-pequeno', '--r-medio', '--sombra'])

interface Achado {
  linha: number
  texto: string
  motivo: string
}

// O que fica no lugar de um comentário `/* px: motivo */` enquanto a regra lê o CSS.
const LIBERA = '«px-liberado»'

const PX = /(?<![\w.-])-?\d*\.?\d+px\b/

/** Confere um CSS contra a regra (o primeiro bloco de testes prova que ela pega o errado). */
function conferir(css: string): Achado[] {
  const achados: Achado[] = []
  // Comentário `/* px: motivo */` libera a declaração em que está (ou a que acabou logo antes,
  // na mesma linha); os outros comentários somem, mantendo as quebras de linha para numerar.
  const limpo = css.replace(/\/\*([\s\S]*?)\*\//g, (_, dentro: string) =>
    /^\s*px:\s*\S/.test(dentro) ? LIBERA : dentro.replace(/[^\n]/g, ' '),
  )
  let posicao = 0
  const pedacos = limpo.split(/([;{}])/)
  let anterior: Achado | null = null
  for (let i = 0; i < pedacos.length; i += 2) {
    const pedaco = pedacos[i]
    const fim = pedacos[i + 1] ?? ''
    const linha = limpo.slice(0, posicao + pedaco.search(/\S|$/)).split('\n').length
    // Liberação logo depois do `;` da declaração anterior, na mesma linha.
    const semEspaco = pedaco.replace(/^[ \t]*/, '')
    const liberaAnterior = semEspaco.startsWith(LIBERA)
    if (liberaAnterior && anterior) {
      achados.splice(achados.indexOf(anterior), 1)
    }
    const texto = pedaco.replaceAll(LIBERA, '').trim()
    const liberado = (liberaAnterior ? semEspaco.slice(LIBERA.length) : pedaco).includes(LIBERA)
    anterior = null
    if (texto && PX.test(texto)) {
      if (fim === '{') {
        if (/^@(media|container|supports)/.test(texto)) {
          achados.push({ linha, texto, motivo: 'media query em px (use em: 900px = 56.25em)' })
        }
      } else {
        const dois = texto.indexOf(':')
        const propriedade = texto.slice(0, dois).trim().toLowerCase()
        let motivo = ''
        if (/^(font-size|font|line-height)$/.test(propriedade)) {
          motivo = `${propriedade} em px (letra em rem, line-height sem unidade)`
        } else if (liberado) {
          motivo = ''
        } else if (propriedade.startsWith('--')) {
          if (!TOKENS_EM_PX.has(propriedade)) motivo = `token ${propriedade} em px fora da lista`
        } else if (!PROPRIEDADES_EM_PX.some((re) => re.test(propriedade))) {
          motivo = `${propriedade} em px fora das exceções (use rem, ou /* px: motivo */)`
        }
        if (motivo) {
          const achado = { linha, texto: texto.replace(/\s+/g, ' '), motivo }
          achados.push(achado)
          // Só a liberação da mesma linha vale para a declaração anterior.
          if (fim === ';') anterior = achado
        }
      }
    }
    posicao += pedaco.length + fim.length
  }
  return achados
}

function cssDe(pasta: string): string[] {
  return readdirSync(pasta).flatMap((nome) => {
    const caminho = join(pasta, nome)
    if (statSync(caminho).isDirectory()) return cssDe(caminho)
    return nome.endsWith('.css') ? [relative(SRC, caminho)] : []
  })
}

const TODOS = cssDe(SRC).sort()

describe('a regra pega o que deve pegar', () => {
  const caso = (css: string) => conferir(css).map((a) => a.motivo.split(' ')[0])
  test('letra, line-height e media query em px', () => {
    assert.deepEqual(caso('a { font-size: 18px; }'), ['font-size'])
    assert.deepEqual(caso('a { font: 700 18px/1.2 x; }'), ['font'])
    assert.deepEqual(caso('a { line-height: 24px; }'), ['line-height'])
    assert.deepEqual(caso('@media (min-width: 900px) { a { color: red; } }'), ['media'])
    // Nem com o comentário de liberação: a letra nunca é fixa.
    assert.deepEqual(caso('a { font-size: 18px /* px: não */; }'), ['font-size'])
  })
  test('espaço e tamanho em px só com motivo escrito', () => {
    assert.deepEqual(caso('a { padding: 12px 16px; }'), ['padding'])
    assert.deepEqual(caso('a { min-height: 44px; }'), ['min-height'])
    assert.deepEqual(caso(':root { --logo-respiro: 14px; }'), ['token'])
    assert.deepEqual(caso('a { padding: 1rem 16px /* px: margem lateral fixa */; }'), [])
    assert.deepEqual(caso('a {\n  width: 1px; /* px: escondido */\n  height: 3px;\n}'), ['height'])
  })
  test('exceções: linha, sombra, canto e foco', () => {
    assert.deepEqual(
      caso(
        'a { border: 2px solid red; border-top-width: 1px; border-radius: 0 0 3px 3px; ' +
          'outline: 3px solid; outline-offset: 2px; box-shadow: inset 0 -4px 0 red; ' +
          'text-underline-offset: 3px; } :root { --r-medio: 12px; --sombra: 0 1px 0 #000; }',
      ),
      [],
    )
  })
  test('rem, em, porcentagem e números sem unidade passam', () => {
    assert.deepEqual(caso('a { font-size: 1.125rem; line-height: 1.5; padding: 0.5em 2%; }'), [])
    assert.deepEqual(caso('@media (min-width: 56.25em) { a { gap: 1rem; } }'), [])
  })
})

describe('os CSS do Portal seguem a regra', () => {
  test('a lista de pendentes só tem arquivo que existe', () => {
    for (const arquivo of PENDENTES) assert.ok(TODOS.includes(arquivo), `${arquivo} não existe mais`)
  })

  for (const arquivo of TODOS) {
    const achados = conferir(readFileSync(join(SRC, arquivo), 'utf8'))
    if (PENDENTES.has(arquivo)) {
      test(`${arquivo}: ainda pendente (tire da lista quando converter)`, () => {
        assert.ok(achados.length > 0, `${arquivo} já está convertido: tire-o de PENDENTES`)
      })
      continue
    }
    test(arquivo, () => {
      assert.deepEqual(
        achados.map((a) => `linha ${a.linha}: ${a.texto} → ${a.motivo}`),
        [],
      )
    })
  }
})
