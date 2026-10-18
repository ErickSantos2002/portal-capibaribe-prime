// Navegação com a bola do Menu (spec docs/superpowers/specs/2026-10-18-navegacao-bola-design.md,
// seção 3): as regras da barra do celular que o jsdom não desenha, conferidas no texto do CSS. A
// prova visual é o scripts/dev/conferir-letra.mjs (16/24/32 px, 320/360/412, claro e escuro).
// Rodar: npm test (ou node --test testes/navegacao-bola.test.ts, de web/)
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { describe, test } from 'node:test'

const semComentario = (css: string) => css.replace(/\/\*[\s\S]*?\*\//g, '')
const estilo = semComentario(readFileSync(new URL('../src/estilo.css', import.meta.url), 'utf8'))
const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8')

/** O bloco `{ … }` da primeira regra cujo seletor é exatamente `seletor` (no nível de cima). */
function regra(css: string, seletor: string): string {
  const escapado = seletor.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const achado = new RegExp(`(^|\\n)${escapado}\\s*\\{([^}]*)\\}`).exec(css)
  return achado ? achado[2] : ''
}

/** Todas as regras (seletor e corpo), em qualquer nível. */
function regras(css: string): { seletor: string; corpo: string }[] {
  return [...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)].map((m) => ({ seletor: m[1].trim(), corpo: m[2] }))
}

const claro = regra(estilo, ':root')
const escuro = regra(estilo, ":root[data-tema='escuro']")
const estreita = regra(estilo, ":root[data-largura='estreita']")

function token(bloco: string, nome: string): string {
  const achado = new RegExp(`--${nome}:\\s*([^;]+);`).exec(bloco)
  assert.ok(achado, `token --${nome} não achado`)
  return achado[1].trim()
}

// ---------- contraste (WCAG 2.x) ----------
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

// ---------- a conta da altura ----------
/** Resolve um valor de token em px, para uma letra (rem) e uma largura de tela (vw). Entende
 *  var(), min(<rem>, <vw>), calc() com + e *, e números. */
function emPx(valor: string, remPx: number, larguraPx: number, bloco: string): number {
  let expr = valor
  for (let i = 0; i < 10 && expr.includes('var('); i++) {
    expr = expr.replace(/var\(\s*--([\w-]+)\s*\)/g, (_, nome: string) => `(${token(bloco, nome)})`)
  }
  expr = expr
    .replace(/env\([^)]*\)/g, '0')
    .replace(/calc\(/g, '(')
    .replace(/(-?\d*\.?\d+)rem/g, (_, n: string) => String(Number(n) * remPx))
    .replace(/(-?\d*\.?\d+)vw/g, (_, n: string) => String((Number(n) * larguraPx) / 100))
    .replace(/min\(/g, 'Math.min(')
  assert.match(expr, /^[\d\s.+*()/,-]*(Math\.min[\d\s.+*()/,-]*)*$/, `não sei resolver: ${expr}`)
  return Function(`return ${expr}`)() as number
}

describe('a barra não cresce com a letra', () => {
  test('a letra das abas tem piso de 15 px e teto pela largura: min(0.9375rem, <vw>)', () => {
    assert.match(regra(estilo, '.nav-barra a'), /font-size:\s*min\(0\.9375rem, \d*\.?\d+vw\)/)
  })

  test('nada dentro da barra tem letra maior (só min(<= 0.9375rem, vw))', () => {
    const naBarra = regras(estilo).filter((r) => r.seletor.includes('.nav-barra') && /font-size/.test(r.corpo))
    assert.ok(naBarra.length >= 2)
    for (const { seletor, corpo } of naBarra) {
      const tamanho = /font-size:\s*([^;]+)/.exec(corpo)?.[1].trim() ?? ''
      const achado = /^min\((\d*\.?\d+)rem, \d*\.?\d+vw\)$/.exec(tamanho)
      assert.ok(achado, `${seletor}: font-size ${tamanho}`)
      assert.ok(Number(achado[1]) <= 0.9375, `${seletor}: ${tamanho}`)
    }
  })

  test('a letra da barra continua com 15 px em toda largura de celular (320 a 430)', () => {
    for (const largura of [320, 339]) {
      assert.ok(emPx(token(estreita, 'barra-letra'), 32, largura, claro + estreita) >= 15 - 0.05, `${largura}`)
    }
    for (const largura of [340, 360, 412, 430]) {
      assert.ok(emPx(token(claro, 'barra-letra'), 32, largura, claro) >= 15 - 0.05, `${largura}`)
    }
  })

  test('a regra da letra das abas e o token dizem a mesma coisa', () => {
    assert.match(regra(estilo, '.nav-barra a'), new RegExp(`font-size:\\s*${token(claro, 'barra-letra').replace(/[()]/g, '\\$&')}`))
    assert.match(
      regra(estilo, ":root[data-largura='estreita'] .nav-barra a"),
      new RegExp(`font-size:\\s*${token(estreita, 'barra-letra').replace(/[()]/g, '\\$&')}`),
    )
  })

  test('altura total (saliência da bola incluída): ≤ 96 px a 16 px e ≤ 104 px a 24 e 32 px', () => {
    for (const largura of [320, 360, 412]) {
      const bloco = largura < 340 ? claro + estreita : claro
      for (const letra of [16, 24, 32]) {
        const altura = emPx('var(--altura-barra)', letra, largura, bloco)
        assert.ok(altura <= (letra === 16 ? 96 : 104), `${largura} px, letra ${letra}: ${altura.toFixed(1)} px`)
      }
    }
  })

  test('a barra tem a altura do token, e a bola sobressai no máximo meia altura', () => {
    assert.match(regra(estilo, '.nav-barra'), /height:\s*calc\(var\(--altura-barra\) \+ env\(safe-area-inset-bottom\)\)/)
    for (const largura of [320, 360, 412]) {
      for (const letra of [16, 32]) {
        const bola = emPx('var(--bola)', letra, largura, claro)
        const saliencia = emPx('var(--barra-saliencia)', letra, largura, claro)
        assert.ok(saliencia <= bola / 2)
      }
    }
  })
})

describe('Documentos vira "Docs" só na tela estreita', () => {
  test('com data-largura="estreita", o longo some da vista e o curto aparece', () => {
    assert.match(regra(estilo, ":root[data-largura='estreita'] .nav-barra .rot-longo"), /clip-path:\s*inset\(50%\)/)
    assert.match(regra(estilo, ":root[data-largura='estreita'] .nav-barra .rot-curto"), /display:\s*inline/)
    assert.match(regra(estilo, '.nav-barra .rot-curto'), /display:\s*none/)
  })
})

describe('nada fica escondido atrás da barra', () => {
  test('a barra fica no fluxo, no fim da página (sticky): o fim do conteúdo para acima dela', () => {
    assert.match(regra(estilo, '.nav'), /position:\s*sticky/)
  })

  test('o foco e as âncoras param acima da barra inteira (scroll-padding pela altura dela)', () => {
    assert.match(regra(estilo, 'html'), /scroll-padding-bottom:\s*calc\(var\(--altura-barra\)[^;]*\)/)
  })

  test('o botão flutuante fica acima da barra', () => {
    assert.match(regra(estilo, '.flutuante'), /bottom:\s*calc\(var\(--altura-barra\)[^;]*\)/)
  })

  test('os cantos transparentes do arco não pegam o toque', () => {
    assert.match(regra(estilo, '.nav-barra'), /pointer-events:\s*none/)
    assert.match(regra(estilo, '.nav-barra > *'), /pointer-events:\s*auto/)
    assert.match(regra(estilo, '.nav-arco'), /pointer-events:\s*none/)
  })
})

describe('iPhone: o indicador de início não cobre os rótulos', () => {
  test('a barra soma a safe-area embaixo, e o index.html pede viewport-fit=cover', () => {
    assert.match(regra(estilo, '.nav-barra'), /padding-bottom:\s*env\(safe-area-inset-bottom\)/)
    assert.match(index, /<meta name="viewport" content="[^"]*viewport-fit=cover[^"]*"/)
  })
})

describe('a bola nos dois temas', () => {
  for (const [nome, tema] of [
    ['claro', claro],
    ['escuro', escuro],
  ]) {
    test(`no tema ${nome}, ícone e fundo da bola com contraste ≥ 3:1 (WCAG 1.4.11)`, () => {
      const fundo = token(tema, 'bola-fundo')
      const icone = token(tema, 'bola-icone')
      assert.match(fundo, /^#[0-9a-f]{6}$/i)
      assert.match(icone, /^#[0-9a-f]{6}$/i)
      assert.ok(contraste(fundo, icone) >= 3, `${nome}: ${contraste(fundo, icone).toFixed(2)}`)
    })
  }

  test('a bola usa os tokens, e o anel e o arco usam papel e folha', () => {
    assert.match(regra(estilo, '.nav-bola-circulo'), /background:\s*var\(--bola-fundo\)/)
    assert.match(regra(estilo, '.nav-bola-circulo'), /color:\s*var\(--bola-icone\)/)
    assert.match(regra(estilo, '.nav-bola-circulo'), /border:[^;]*var\(--papel\)/)
    assert.match(regra(estilo, '.nav-arco'), /fill:\s*var\(--folha\)/)
  })

  test('nenhum hex solto nas regras da barra', () => {
    for (const { seletor, corpo } of regras(estilo).filter((r) => /\.nav-(barra|bola|arco)/.test(r.seletor))) {
      assert.doesNotMatch(corpo, /#[0-9a-f]{3,8}\b/i, seletor)
    }
  })
})

describe('as regras velhas das abas saíram', () => {
  test('sem os tetos 5.5vw/4.3vw e sem o caso de cinco abas', () => {
    assert.doesNotMatch(estilo, /5\.5vw|4\.3vw/)
    assert.doesNotMatch(estilo, /nth-of-type\(5\)/)
  })
})

describe('a folha do Menu (seção 4)', () => {
  test('cresce até perto do topo (dvh) e a lista rola por dentro, sem levar a página junto', () => {
    assert.match(regra(estilo, '.menu-folha'), /max-height:\s*calc\(100dvh - [\d.]+rem\)/)
    assert.match(regra(estilo, '.menu-folha-lista'), /overflow-y:\s*auto/)
    assert.match(regra(estilo, '.menu-folha-lista'), /overscroll-behavior:\s*contain/)
  })

  test('encosta no fundo e cobre a barra; a bola-X fica no lugar da bola', () => {
    assert.match(regra(estilo, '.menu-folha'), /margin:\s*auto 0 0/)
    assert.match(regra(estilo, '.menu-folha-pe'), /height:\s*calc\(var\(--altura-barra\) \+ env\(safe-area-inset-bottom\)\)/)
  })

  test('só a pegadinha e o cabeçalho arrastam (o navegador não rola ali)', () => {
    assert.match(regra(estilo, '.menu-folha-topo'), /touch-action:\s*none/)
  })

  test('a animação de subir é curta e tem nome próprio (o prefers-reduced-motion global a desliga)', () => {
    assert.match(regra(estilo, '.menu-folha[open]'), /animation:\s*menu-folha-sobe 0\.\d+s/)
  })

  test('as linhas têm pelo menos 3rem de altura', () => {
    assert.match(regra(estilo, '.menu-folha-grupo a'), /min-height:\s*3(\.\d+)?rem/)
  })
})
