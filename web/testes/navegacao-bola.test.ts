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
function emPx(
  valor: string,
  remPx: number,
  larguraPx: number,
  bloco: string,
  { cem = NaN, letraPx = NaN }: { cem?: number; letraPx?: number } = {},
): number {
  let expr = valor
  for (let i = 0; i < 10 && expr.includes('var('); i++) {
    expr = expr.replace(/var\(\s*--([\w-]+)\s*\)/g, (_, nome: string) => `(${token(bloco, nome)})`)
  }
  expr = expr
    .replace(/env\([^)]*\)/g, '0')
    .replace(/calc\(/g, '(')
    .replace(/(-?\d*\.?\d+)rem/g, (_, n: string) => String(Number(n) * remPx))
    .replace(/(-?\d*\.?\d+)em/g, (_, n: string) => String(Number(n) * letraPx))
    .replace(/(-?\d*\.?\d+)%/g, (_, n: string) => String((Number(n) * cem) / 100))
    .replace(/(-?\d*\.?\d+)vw/g, (_, n: string) => String((Number(n) * larguraPx) / 100))
    .replace(/(min|max)\(/g, 'Math.$1(')
  assert.match(expr, /^([\d\s.+*()/,-]|Math\.(min|max))*$/, `não sei resolver: ${expr}`)
  const px = Function(`return ${expr}`)() as number
  assert.ok(Number.isFinite(px), `faltou % ou em para resolver: ${valor}`)
  return px
}

/** Os tokens de vários blocos, o de depois por cima (como na cascata): `token()` pega o primeiro
 *  que acha, então o bloco que sobrescreve vem na frente. */
const cascata = (...blocos: string[]) => [...blocos].reverse().join('\n')

/** O miolo de cada `cabecalho { … }` (ex.: um @container), com as chaves de dentro. */
function blocos(css: string, cabecalho: string): string[] {
  const achados: string[] = []
  for (let i = css.indexOf(`${cabecalho} {`); i >= 0; i = css.indexOf(`${cabecalho} {`, i + 1)) {
    const abre = css.indexOf('{', i)
    let fundo = 1
    let j = abre + 1
    for (; j < css.length && fundo > 0; j++) {
      if (css[j] === '{') fundo++
      else if (css[j] === '}') fundo--
    }
    achados.push(css.slice(abre + 1, j - 1))
  }
  return achados
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
      const bloco = largura < 340 ? cascata(claro, estreita) : claro
      for (const letra of [16, 24, 32]) {
        const altura = emPx('var(--altura-barra)', letra, largura, bloco)
        assert.ok(altura <= (letra === 16 ? 96 : 104), `${largura} px, letra ${letra}: ${altura.toFixed(1)} px`)
      }
    }
  })

  test('na tela estreita, a conta da altura usa a letra da tela estreita (4.7vw), não a do :root', () => {
    const bloco = cascata(claro, estreita)
    const letra = emPx('var(--barra-letra)', 32, 320, bloco)
    assert.equal(letra, emPx(token(estreita, 'barra-letra'), 32, 320, claro))
    assert.notEqual(letra, emPx(token(claro, 'barra-letra'), 32, 320, claro))
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

  test('a bola usa os tokens, e o arco usa a folha', () => {
    assert.match(regra(estilo, '.nav-bola-circulo'), /background:\s*var\(--bola-fundo\)/)
    assert.match(regra(estilo, '.nav-bola-circulo'), /color:\s*var\(--bola-icone\)/)
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
    assert.match(regra(estilo, '.menu-folha-pe'), /min-height:\s*calc\(var\(--altura-barra\) \+ env\(safe-area-inset-bottom\)\)/)
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

describe('achados da conferência (Tarefa 5)', () => {
  test('o número de não lidos não fica menor que 13 px no celular de 320 px', () => {
    const tamanho = /font-size:\s*([^;]+)/.exec(regra(estilo, '.nav-barra .conta'))?.[1] ?? ''
    assert.ok(emPx(tamanho, 16, 320, claro) >= 12.95, tamanho)
  })

  test('folha com letra grande num celular: o nome ganha a linha inteira (o ícone sobe para cima dele)', () => {
    const bloco = blocos(estilo, '@container raiz (max-width: 15rem)').join('\n')
    assert.ok(bloco, 'sem o @container raiz (max-width: 15rem)')
    assert.match(bloco, /\.menu-folha-texto\s*\{[^}]*grid-column:\s*1 \/ -1/)
  })
})

describe('achados dos prints (Tarefa 5)', () => {
  test('o realce de passar o mouse na folha só vale com mouse (no toque, o :hover gruda)', () => {
    assert.doesNotMatch(estilo, /(^|\n)\.menu-folha-grupo a:hover/)
    assert.match(estilo, /@media \(hover: hover\) \{\s*\.menu-folha-grupo a:hover/)
  })
})

describe('revisões da navegação com bola', () => {
  test('C1: as regras do menu lateral (computador) não pegam os links da folha', () => {
    // A folha (<dialog>) mora dentro do .nav: `.nav a` pintava os lugares dela de branco sobre a
    // folha branca no tema claro, quando o iPhone grande gira com ela aberta.
    const computador = blocos(estilo, '@container raiz (min-width: 56.25rem)')
    assert.ok(computador.length > 0)
    for (const { seletor } of computador.flatMap(regras)) {
      for (const parte of seletor.split(',')) {
        assert.doesNotMatch(parte, /\.nav\s+(a\b|\.conta\b)/, `escopar em .nav-lateral: ${parte.trim()}`)
      }
    }
    assert.ok(computador.some((b) => /\.nav-lateral a\[aria-current='page'\]/.test(b)))
    assert.ok(computador.some((b) => /\.nav-lateral \.conta\s*\{/.test(b)))
  })

  test('C2: a plaquinha de não lidos (1, 12 e 120) fica dentro da aba a 320 px, em toda letra', () => {
    // Largura da plaquinha em em, medida no Chrome (Atkinson Hyperlegible negrito, 13 px):
    // 18 px com "1" (o min-width), 23,5 com "12", 31,9 com "120".
    const larguras: [string, number][] = [
      ['1', 1.385],
      ['12', 1.81],
      ['120', 2.46],
    ]
    const base = regra(estilo, '.nav-barra .conta')
    const bloco = cascata(claro, estreita)
    for (const letra of [16, 24, 32]) {
      // A 320 px, as quatro abas têm a mesma largura (com "Docs"): (320 − coluna da bola) / 4.
      const coluna = (320 - emPx('var(--bola-coluna)', letra, 320, bloco)) / 4
      const letraPx = emPx(/font-size:\s*([^;]+)/.exec(base)![1], letra, 320, bloco)
      const contexto = { cem: coluna, letraPx }
      const direita = /right:\s*([^;]+)/.exec(base)?.[1]
      const esquerda = /left:\s*([^;]+)/.exec(base)?.[1]
      for (const [numero, emLargura] of larguras) {
        const largura = emLargura * letraPx
        const [de, ate] =
          direita && esquerda === 'auto'
            ? [coluna - emPx(direita, letra, 320, bloco, contexto) - largura, coluna - emPx(direita, letra, 320, bloco, contexto)]
            : [emPx(esquerda!, letra, 320, bloco, contexto), emPx(esquerda!, letra, 320, bloco, contexto) + largura]
        assert.ok(ate <= coluna + 0.05, `letra ${letra}, "${numero}": borda direita ${ate.toFixed(1)} > aba ${coluna.toFixed(1)}`)
        assert.ok(de >= -0.05, `letra ${letra}, "${numero}": borda esquerda ${de.toFixed(1)} < 0`)
        // Com um algarismo, a plaquinha continua onde sempre esteve: no canto de cima do ícone.
        if (numero === '1') {
          const canto = coluna / 2 + emPx('min(0.375rem, 1.46vw)', letra, 320, bloco)
          assert.ok(Math.abs(de - canto) < 0.5, `"1" saiu do canto do ícone: ${de.toFixed(1)} ≠ ${canto.toFixed(1)}`)
        }
      }
    }
  })

  test('U2: um fio em cima do pé e embaixo do cabeçalho quando a lista continua', () => {
    assert.match(regra(estilo, '.menu-folha-lista[data-mais-abaixo] + .menu-folha-pe::before'), /border-top-color:\s*var\(--linha\)/)
    assert.match(regra(estilo, '.menu-folha-lista[data-mais-acima]'), /border-top-color:\s*var\(--linha\)/)
    // O fio transparente existe sempre: a lista não pula 1 px quando ele acende; no pé, ele é
    // desenhado por cima (::before absoluto), para a bola-X ficar no ponto exato da bola.
    assert.match(regra(estilo, '.menu-folha-pe::before'), /position:\s*absolute/)
    assert.match(regra(estilo, '.menu-folha-pe::before'), /border-top:\s*1px solid transparent/)
    assert.match(regra(estilo, '.menu-folha-lista'), /border-top:\s*1px solid transparent/)
  })

  test('U3: "Fechar" cresce com a letra (1rem, sem teto) e o pé cresce junto, a partir da altura da barra', () => {
    assert.match(regra(estilo, '.menu-folha-fechar'), /font-size:\s*1rem/)
    const pe = regra(estilo, '.menu-folha-pe')
    assert.match(pe, /min-height:\s*calc\(var\(--altura-barra\) \+ env\(safe-area-inset-bottom\)\)/)
    assert.doesNotMatch(pe, /(^|[^-])height:/)
  })

  test('U4: com letra grande, as linhas da folha têm fio entre elas e o ícone menor em cima; só a seta sai', () => {
    const bloco = blocos(estilo, '@container raiz (max-width: 15rem)').join('\n')
    assert.match(bloco, /\.menu-folha-grupo a > \.icone:last-child\s*\{[^}]*display:\s*none/)
    assert.doesNotMatch(bloco, /\.menu-folha-ic[^{]*\{[^}]*display:\s*none/)
    assert.match(bloco, /\.menu-folha-grupo a \+ a\s*\{[^}]*border-top:\s*1px solid var\(--linha\)/)
    assert.match(bloco, /\.menu-folha-texto\s*\{[^}]*grid-column:\s*1 \/ -1/)
  })

  test('U5: "Menu" na mesma linha dos nomes das abas: a bola mede o espaço até o nome da aba', () => {
    // O nome da aba começa em flecha + saliência + topo + ícone (+ o vão); o de "Menu", em bola
    // (+ o mesmo vão). Iguais em toda largura e letra.
    const ateONome = 'calc(var(--barra-flecha) + var(--barra-saliencia) + var(--barra-topo) + var(--barra-icone))'
    for (const largura of [320, 360, 412]) {
      for (const letra of [16, 24, 32]) {
        const bloco = largura < 340 ? cascata(claro, estreita) : claro
        const bola = emPx('var(--bola)', letra, largura, bloco)
        const aba = emPx(ateONome, letra, largura, bloco)
        assert.ok(Math.abs(bola - aba) < 0.01, `${largura} px, letra ${letra}: bola ${bola.toFixed(1)} ≠ ${aba.toFixed(1)}`)
      }
    }
  })

  test('U6: o lugar atual tem fundo arredondado atrás do ícone (aba) e do círculo (bola acesa)', () => {
    assert.match(regra(estilo, ".nav-barra a[aria-current='page'] .icone"), /background:\s*var\(--barra-aceso\)/)
    assert.match(regra(estilo, ".nav-barra a[aria-current='page'] .icone"), /border-radius/)
    assert.match(regra(estilo, '.nav-bola[data-aqui] .nav-bola-circulo'), /border-color:\s*var\(--barra-aceso\)/)
    assert.equal(token(claro, 'barra-aceso'), 'var(--mata-suave)')
    // No escuro, o --mata-suave (#1c2e23) some na barra (1,2:1 com a --folha): o token do escuro é
    // um verde que aparece, mas continua fundo (o ícone verde-claro por cima, com contraste).
    const acesoEscuro = token(escuro, 'barra-aceso')
    assert.match(acesoEscuro, /^#[0-9a-f]{6}$/i)
    assert.ok(contraste(acesoEscuro, token(escuro, 'folha')) >= 1.5, `aceso × folha: ${contraste(acesoEscuro, token(escuro, 'folha')).toFixed(2)}`)
    assert.ok(contraste(acesoEscuro, token(escuro, 'mata')) >= 4.5, `ícone × aceso: ${contraste(acesoEscuro, token(escuro, 'mata')).toFixed(2)}`)
  })

  test('U7: no escuro, o anel da bola é a --linha (separa a bola da barra); no claro, o --papel', () => {
    assert.match(regra(estilo, '.nav-bola-circulo'), /border:[^;]*var\(--bola-anel\)/)
    assert.equal(token(claro, 'bola-anel'), 'var(--papel)')
    assert.equal(token(escuro, 'bola-anel'), 'var(--linha)')
  })
})
