// M5 · letra que cresce (spec docs/superpowers/specs/m5-letra.md, seção 3): guarda automática da
// regra. Lê todo .css de web/src, o <style> do index.html e os `style={{…}}` dos .tsx, e falha se
// houver tamanho de letra em unidade absoluta, media query de tamanho, ou unidade absoluta fora
// das exceções permitidas. Os CSS dos épicos que ainda não foram convertidos estariam em
// PENDENTES; quem converte um arquivo tira a linha dele daqui (plano m5-letra, tarefas G1 a G3).
// Revisões do M5 (R6): os buracos que a revisão achou estão fechados, cada um com o seu teste
// no primeiro bloco ("a regra pega o que deve pegar").
// Rodar: npm test (ou node --test testes/letra.test.ts, de web/)
import assert from 'node:assert/strict'
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'
import { describe, test } from 'node:test'

const SRC = new URL('../src/', import.meta.url).pathname
const INDEX = new URL('../index.html', import.meta.url).pathname

/** Ainda em px: cada grupo apaga as suas linhas ao converter (e o teste passa a cobri-las). */
const PENDENTES = new Set<string>([
  // G1
  // G2
  // G3
])

/** Propriedades que podem ter px sem justificar: espessura de linha (spec 3.3). A espessura tem
 *  teto (R6): uma "borda" de 20 px já é um bloco, e tem de crescer com a letra. A sombra saiu da
 *  lista: em px, só no token `--sombra`; no resto, em rem. */
const LINHA = [
  /^border(-(top|right|bottom|left|block|inline)(-(start|end))?)?(-width)?$/,
  /^outline(-width|-offset)?$/,
  /^text-underline-offset$/,
  /^text-decoration-thickness$/,
]
/** Teto das espessuras acima, em px. */
const TETO_DA_LINHA = 4
/** Canto: qualquer valor (não ocupa o lugar do texto). */
const CANTO = /^border(-(top|right|bottom|left|start|end)(-(left|right|start|end))?)?-radius$/
/** Tokens de :root que podem ser px: os cantos e a sombra. */
const TOKENS_EM_PX = new Set(['--r-pequeno', '--r-medio', '--sombra'])

/** Unidades absolutas (R6: não só px, e sem diferenciar maiúsculas). */
const ABSOLUTA = String.raw`(?<![\w.#-])-?\d*\.?\d+(?:px|pt|pc|cm|mm|in|q)(?![\w-])`
const PX = new RegExp(ABSOLUTA, 'i')
const PX_TODOS = new RegExp(ABSOLUTA, 'gi')
/** Unidade da janela (vw, vh, svh, dvb…), que não acompanha a letra. */
const JANELA = /(?<![\w.-])-?\d*\.?\d+[sld]?v(?:w|h|i|b|min|max)(?![\w-])/i
/** O único jeito aceito de vw na letra: o teto `min(<rem>, <vw>)` (spec 3.5, abas de baixo). */
const TETO_DA_LETRA = /^min\(\s*\d*\.?\d+rem\s*,\s*\d*\.?\d+vw\s*\)$/i

interface Achado {
  linha: number
  texto: string
  motivo: string
}

// O que fica no lugar de um comentário `/* px: motivo */` enquanto a regra lê o CSS.
const LIBERA = '«px-liberado»'

/** Os tokens (`--nome: valor`) de um CSS, para saber se `var(--nome)` traz unidade absoluta. */
function tokensDe(css: string): Map<string, string> {
  const tokens = new Map<string, string>()
  for (const m of css.replace(/\/\*[\s\S]*?\*\//g, '').matchAll(/(--[\w-]+)\s*:\s*([^;{}]+)/g)) {
    tokens.set(m[1], m[2].trim())
  }
  return tokens
}

/** Uma declaração (`propriedade: valor`) contra a regra; '' quando passa. */
function motivoDa(propriedade: string, valor: string, liberado: boolean, tokens: Map<string, string>): string {
  const temPx = PX.test(valor)
  if (/^(font-size|font|line-height)$/.test(propriedade)) {
    // A letra nunca é fixa, nem com o comentário de liberação.
    if (temPx) return `${propriedade} em px (letra em rem, line-height sem unidade)`
    if (JANELA.test(valor) && !TETO_DA_LETRA.test(valor)) {
      return `${propriedade} em vw/vh (só como teto: min(<rem>, <vw>))`
    }
    const absolutos = [...valor.matchAll(/var\(\s*(--[\w-]+)/g)]
      .map((m) => m[1])
      .filter((t) => PX.test(tokens.get(t) ?? ''))
    if (absolutos.length) return `${propriedade} com token em px (${absolutos.join(', ')})`
    return ''
  }
  if (!temPx || liberado) return ''
  if (propriedade.startsWith('--')) {
    return TOKENS_EM_PX.has(propriedade) ? '' : `token ${propriedade} em px fora da lista`
  }
  if (CANTO.test(propriedade)) return ''
  if (LINHA.some((re) => re.test(propriedade))) {
    const medidas = [...valor.matchAll(PX_TODOS)].map((m) => m[0].toLowerCase())
    const passa = medidas.every((m) => m.endsWith('px') && Math.abs(parseFloat(m)) <= TETO_DA_LINHA)
    return passa ? '' : `${propriedade} acima de ${TETO_DA_LINHA}px ou em outra unidade absoluta (use rem)`
  }
  return `${propriedade} em px fora das exceções (use rem, ou /* px: motivo */)`
}

/** Confere um CSS contra a regra (o primeiro bloco de testes prova que ela pega o errado). */
function conferir(css: string, tokens: Map<string, string> = tokensDe(css)): Achado[] {
  const achados: Achado[] = []
  // Comentário `/* px: motivo */` libera a declaração em que está, ou a que acabou logo antes na
  // mesma linha; os outros comentários somem, mantendo as quebras de linha para numerar.
  const limpo = css.replace(/\/\*([\s\S]*?)\*\//g, (_, dentro: string) =>
    /^\s*px:\s*\S/.test(dentro) ? LIBERA : dentro.replace(/[^\n]/g, ' '),
  )
  let posicao = 0
  const pedacos = limpo.split(/([;{}])/)
  // A declaração anterior, se ainda pode ser liberada por um comentário logo depois do `;`: só
  // quando o px dela está na última linha dela (a mesma do `;` e do comentário).
  let anterior: Achado | null = null
  for (let i = 0; i < pedacos.length; i += 2) {
    let pedaco = pedacos[i]
    const fim = pedacos[i + 1] ?? ''
    const linha = limpo.slice(0, posicao + pedaco.search(/\S|$/)).split('\n').length
    const avanco = pedaco.length + fim.length
    // Liberação logo depois do `;` da declaração anterior, ainda na mesma linha.
    const comeco = /^[ \t]*«px-liberado»/.exec(pedaco)
    if (comeco) {
      if (anterior) achados.splice(achados.indexOf(anterior), 1)
      pedaco = pedaco.slice(comeco[0].length)
    }
    anterior = null
    const texto = pedaco.replaceAll(LIBERA, '').trim()
    if (texto && fim === '{') {
      if (/^@(media|container|supports)/.test(texto) && PX.test(texto)) {
        achados.push({ linha, texto, motivo: 'media query em px (use rem: 900px = 56.25rem)' })
      } else if (/^@media/.test(texto) && /\((min-|max-)?(width|height|inline-size|block-size)\s*:/.test(texto)) {
        // R1: media query de tamanho, em qualquer unidade, não acompanha o Dynamic Type do iPhone.
        achados.push({
          linha,
          texto,
          motivo: 'media query de tamanho (use @container raiz em rem, ou data-letra/data-altura)',
        })
      } else if (/^@container/.test(texto) && /\d(em)\b/.test(texto)) {
        achados.push({ linha, texto, motivo: 'container query em em (use rem)' })
      }
    } else if (texto && texto.includes(':')) {
      const dois = texto.indexOf(':')
      const propriedade = texto.slice(0, dois).trim().toLowerCase()
      const valor = texto.slice(dois + 1).trim()
      // R6: o comentário só vale na MESMA linha do px: cada linha com px precisa do seu.
      const linhas = pedaco.split('\n')
      const comPx = linhas.filter((l) => PX.test(l))
      const liberado = comPx.length > 0 && comPx.every((l) => l.includes(LIBERA))
      const motivo = motivoDa(propriedade, valor, liberado, tokens)
      if (motivo) {
        const achado = { linha, texto: texto.replace(/\s+/g, ' '), motivo }
        achados.push(achado)
        const soNaUltima = comPx.length === 1 && PX.test(linhas.at(-1) ?? '')
        const ehLetra = /^(font-size|font|line-height)$/.test(propriedade)
        if (fim === ';' && soNaUltima && !ehLetra) anterior = achado
      }
    }
    posicao += avanco
  }
  return achados
}

/** Os `style={{…}}` de um .tsx: tamanho em unidade absoluta, ou número puro (o React põe px). */
const MEDIDAS_REACT =
  /^(width|height|(min|max)(Width|Height)|margin\w*|padding\w*|top|right|bottom|left|inset\w*|gap|rowGap|columnGap|fontSize|lineHeight|flexBasis)$/
function conferirTsx(codigo: string): Achado[] {
  const achados: Achado[] = []
  for (const m of codigo.matchAll(/style=\{\{([\s\S]*?)\}\}/g)) {
    const linha = codigo.slice(0, m.index).split('\n').length
    for (const par of m[1].matchAll(/(['"]?[\w-]+['"]?)\s*:\s*([^,]+)/g)) {
      const chave = par[1].replace(/['"]/g, '')
      const valor = par[2].trim()
      const numero = /^-?\d*\.?\d+$/.test(valor) && valor !== '0' && chave !== 'lineHeight'
      if (MEDIDAS_REACT.test(chave) && (PX.test(valor) || numero)) {
        achados.push({ linha, texto: `${chave}: ${valor}`, motivo: `style={{ ${chave} }} em px (use rem)` })
      }
    }
  }
  return achados
}

/** O conteúdo dos `<style>` de um HTML. */
const estilosDoHtml = (html: string) => [...html.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/gi)].map((m) => m[1]).join('\n')

function arquivosDe(pasta: string, fim: (nome: string) => boolean): string[] {
  return readdirSync(pasta).flatMap((nome) => {
    const caminho = join(pasta, nome)
    if (statSync(caminho).isDirectory()) return arquivosDe(caminho, fim)
    return fim(nome) ? [relative(SRC, caminho)] : []
  })
}

const TODOS = arquivosDe(SRC, (n) => n.endsWith('.css')).sort()
const TSX = arquivosDe(SRC, (n) => n.endsWith('.tsx') && !n.includes('.test.')).sort()
// Os tokens valem em todo o Portal (o `:root` do estilo.css é lido por todos os CSS).
const TOKENS = new Map(TODOS.flatMap((a) => [...tokensDe(readFileSync(join(SRC, a), 'utf8'))]))

describe('a regra pega o que deve pegar', () => {
  const caso = (css: string, tokens?: Map<string, string>) =>
    conferir(css, tokens).map((a) => a.motivo.split(' ')[0])
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
  test('exceções: linha fina, canto, foco e o token da sombra', () => {
    assert.deepEqual(
      caso(
        'a { border: 2px solid red; border-top-width: 1px; border-radius: 0 0 3px 3px; ' +
          'outline: 3px solid; outline-offset: 2px; border-radius: 999px; ' +
          'text-underline-offset: 3px; } :root { --r-medio: 12px; --sombra: 0 1px 0 #000; }',
      ),
      [],
    )
  })
  test('rem, em, porcentagem e números sem unidade passam', () => {
    assert.deepEqual(caso('a { font-size: 1.125rem; line-height: 1.5; padding: 0.5em 2%; }'), [])
    assert.deepEqual(caso('@container raiz (min-width: 56.25rem) { a { gap: 1rem; } }'), [])
    assert.deepEqual(caso('a { color: #1f5e3b; background: #9cc; }'), [])
  })

  // ---- revisões do M5 (R6 e R1): cada buraco que a revisão achou ----
  test('R6: as outras unidades absolutas, e em maiúsculas', () => {
    assert.deepEqual(caso('a { padding: 12PX; }'), ['padding'])
    assert.deepEqual(caso('a { font-size: 12pt; }'), ['font-size'])
    assert.deepEqual(caso('a { margin: 1cm 2mm; }'), ['margin'])
    assert.deepEqual(caso('a { width: 1in; height: 4Q; gap: 2pc; }'), ['width', 'height', 'gap'])
  })
  test('R6: vw/vh na letra só como teto min(rem, vw)', () => {
    assert.deepEqual(caso('a { font-size: 5vw; }'), ['font-size'])
    assert.deepEqual(caso('a { font-size: calc(1rem + 2vh); }'), ['font-size'])
    assert.deepEqual(caso('a { font: 700 4dvh/1.2 x; }'), ['font'])
    assert.deepEqual(caso('a { font-size: max(0.9375rem, 5vw); }'), ['font-size'])
    assert.deepEqual(caso('a { font-size: min(0.9375rem, 5.5vw); }'), [])
  })
  test('R6: var() na letra com token de unidade absoluta', () => {
    const tokens = new Map([
      ['--letra-fixa', '18px'],
      ['--letra-boa', '1.125rem'],
      ['--comentado', '20px'],
    ])
    assert.deepEqual(caso('a { font-size: var(--letra-fixa); }', tokens), ['font-size'])
    assert.deepEqual(caso('a { font: 700 var(--letra-fixa)/1.2 x; }', tokens), ['font'])
    assert.deepEqual(caso('a { font-size: var(--letra-boa); }', tokens), [])
    // O token liberado com comentário continua não servindo para letra.
    assert.deepEqual(
      caso(':root { --comentado: 20px; /* px: imagem */ } a { font-size: var(--comentado); }'),
      ['font-size'],
    )
  })
  test('R6: teto de 4px na espessura; sombra em px só no token --sombra', () => {
    assert.deepEqual(caso('a { border-left: 5px solid red; }'), ['border-left'])
    assert.deepEqual(caso('a { border-width: 0 2.5px 20px 0; }'), ['border-width'])
    assert.deepEqual(caso('a { outline: 6px solid; }'), ['outline'])
    assert.deepEqual(caso('a { border-top: 1pt solid; }'), ['border-top'])
    assert.deepEqual(caso('a { box-shadow: inset 0 -4px 0 red; }'), ['box-shadow'])
    assert.deepEqual(caso('a { text-shadow: 0 1px 0 red; }'), ['text-shadow'])
    assert.deepEqual(caso('a { box-shadow: inset 0 -0.25rem 0 red; box-shadow: var(--sombra); }'), [])
  })
  test('R6: o comentário /* px: */ só vale na mesma linha do px', () => {
    assert.deepEqual(caso('a {\n  width: 10px;\n  /* px: imagem */\n}'), ['width'])
    assert.deepEqual(caso('a {\n  /* px: imagem */\n  width: 10px;\n}'), ['width'])
    assert.deepEqual(caso('a {\n  padding: 1rem\n    16px\n    /* px: margem */;\n}'), ['padding'])
    assert.deepEqual(caso('a {\n  width: 10px; /* px: imagem */\n}'), [])
    assert.deepEqual(caso('a {\n  /* px: imagem */ width: 10px;\n}'), [])
  })
  test('R1: media query de tamanho em em/rem (não acompanha o iPhone); container query em em', () => {
    assert.deepEqual(caso('@media (min-width: 56.25em) { a { gap: 1rem; } }'), ['media'])
    assert.deepEqual(caso('@media (max-height: 35em) { a { gap: 1rem; } }'), ['media'])
    assert.deepEqual(caso('@media not all and (min-width: 56.25rem) { a { gap: 1rem; } }'), ['media'])
    assert.deepEqual(caso('@container raiz (max-width: 22em) { a { gap: 1rem; } }'), ['container'])
    assert.deepEqual(caso('@media (prefers-reduced-motion: reduce) { a { gap: 1rem; } }'), [])
  })
  test('R6: style={{}} dos .tsx com px (texto ou número puro)', () => {
    const tsx = (codigo: string) => conferirTsx(codigo).map((a) => a.texto.split(':')[0])
    assert.deepEqual(tsx('<span style={{ width: 24 }} />'), ['width'])
    assert.deepEqual(tsx("<span style={{ marginTop: '12px', opacity: 0.5 }} />"), ['marginTop'])
    assert.deepEqual(tsx("<span style={{ fontSize: '1.125rem', width: `${x}%` }} />"), [])
    assert.deepEqual(tsx('<span style={{ lineHeight: 1.5, zIndex: 3 }} />'), [])
  })
  test('R6: o <style> do index.html também é lido', () => {
    const html = '<head><style>\n  body { padding: 8px; }\n</style></head>'
    assert.deepEqual(conferir(estilosDoHtml(html)).map((a) => a.motivo.split(' ')[0]), ['padding'])
  })
})

describe('os CSS do Portal seguem a regra', () => {
  test('a lista de pendentes só tem arquivo que existe', () => {
    for (const arquivo of PENDENTES) assert.ok(TODOS.includes(arquivo), `${arquivo} não existe mais`)
  })

  for (const arquivo of TODOS) {
    const achados = conferir(readFileSync(join(SRC, arquivo), 'utf8'), TOKENS)
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

  test('o <style> do index.html', () => {
    const achados = conferir(estilosDoHtml(readFileSync(INDEX, 'utf8')), TOKENS)
    assert.deepEqual(achados.map((a) => `${a.texto} → ${a.motivo}`), [])
  })

  test('os style={{…}} dos .tsx', () => {
    const achados = TSX.flatMap((a) =>
      conferirTsx(readFileSync(join(SRC, a), 'utf8')).map((x) => `${a}:${x.linha}: ${x.texto} → ${x.motivo}`),
    )
    assert.deepEqual(achados, [])
  })
})
