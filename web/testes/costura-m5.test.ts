// M5 · costura da "letra que cresce": as regras do comum que os grupos G1, G2 e G3 pediram
// (docs/superpowers/duvidas-m5-letra.md, seção Costura). O jsdom não desenha; a prova visual é o
// scripts/dev/conferir-letra.mjs (ícone encolhido, palavra quebrada, texto que passa da borda),
// e aqui fica a guarda de que a regra está no lugar certo e de que os contornos locais saíram.
// Cada teste falhava antes da costura. Rodar: npm test
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { describe, test } from 'node:test'

const ler = (caminho: string) => readFileSync(new URL(`../src/${caminho}`, import.meta.url), 'utf8')
const semComentario = (css: string) => css.replace(/\/\*[\s\S]*?\*\//g, '')
const estilo = semComentario(ler('estilo.css'))
const avisos = semComentario(ler('avisos/avisos.css'))
const anexos = semComentario(ler('avisos/anexos.css'))
const notificacoes = semComentario(ler('notificacoes/notificacoes.css'))
const enquetes = semComentario(ler('enquetes/votar/enquetes.css'))
const sobre = semComentario(ler('sobre/sobre.css'))

/** O bloco `{ … }` da primeira regra cujo seletor é exatamente `seletor` (no nível de cima). */
function regra(css: string, seletor: string): string {
  const escapado = seletor.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const achado = new RegExp(`(^|\\n)${escapado}\\s*\\{([^}]*)\\}`).exec(css)
  return achado ? achado[2] : ''
}

/** O conteúdo de um `@container`/`@media` cuja condição é exatamente `condicao`. */
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

describe('1: ícone nunca encolhe, uma regra só no comum', () => {
  test('todo SVG do Portal (Icone, anexos, documentos) com flex-shrink 0, seletor de elemento', () => {
    assert.match(regra(estilo, 'svg'), /flex-shrink:\s*0/)
  })

  test('o pontinho do selo também', () => {
    assert.match(regra(estilo, '.selo::before'), /flex:\s*none/)
  })

  test('os contornos dos grupos saíram', () => {
    assert.doesNotMatch(avisos, /\.fixado \.rotulo svg|\.avisos-busca label svg|\.avisos-arquivados \.texto-link svg/)
    assert.doesNotMatch(anexos, /\.anexos-escolher label svg/)
    assert.doesNotMatch(notificacoes, /\.notif-cartao \.com-icone svg/)
    assert.doesNotMatch(regra(enquetes, '.selo.enq-falta::before'), /flex:\s*none/)
  })
})

describe('2 e 5: com letra grande, o que não é texto encolhe (.opcao, .item, .botao)', () => {
  const grande = bloco(estilo, '@container conteudo (max-width: 17.5rem)')

  test('existe o limite de letra grande no comum', () => {
    assert.ok(grande, '@container conteudo (max-width: 17.5rem) não achado no estilo.css')
  })

  test('.opcao: gap, padding e rádio menores', () => {
    assert.match(grande, /\.opcao\s*\{[^}]*gap:\s*0\.5rem/)
    assert.match(grande, /\.opcao input\s*\{[^}]*width:\s*1\.25rem/)
  })

  test('.item: padding menor e seta menor', () => {
    assert.match(grande, /\.item\s*\{[^}]*padding:/)
    assert.match(grande, /\.item \.seta svg\s*\{[^}]*width:\s*1rem/)
  })

  test('.botao: o ícone sobe quando o rótulo não cabe ao lado', () => {
    assert.match(grande, /\.botao\s*\{[^}]*flex-wrap:\s*wrap/)
  })
})

describe('3 (revisões do M5, A): o topo continua fixo; com letra grande vira faixa fina', () => {
  test('sem o @media (max-height) que soltava o topo (o recado e o voltar sumiam ao rolar)', () => {
    assert.doesNotMatch(estilo, /@media \(max-height/)
  })

  test('o topo é sempre fixo, também como faixa (o recado mora nela)', () => {
    assert.match(regra(estilo, '.topo'), /position:\s*sticky/)
    assert.doesNotMatch(regra(estilo, '.topo.faixa'), /position:/)
  })
})

// Navegação com a bola (spec 2026-10-18-navegacao-bola-design.md): as cinco abas saíram, e a
// barra tem tamanho fixo em qualquer letra (testes/navegacao-bola.test.ts). Ficam as garantias.
describe('4: abas de baixo nunca encostam', () => {
  test('cada aba tem pelo menos a largura da palavra', () => {
    assert.match(regra(estilo, '.nav-barra a'), /min-width:\s*min-content/)
  })

  test('o teto da letra das abas (agora fixa pela largura) continua', () => {
    assert.match(regra(estilo, '.nav-barra a'), /font-size:\s*min\(0\.9375rem, \d*\.?\d+vw\)/)
  })

  test('o número de não lidos não passa da borda da aba (R4: em em, letra com teto)', () => {
    assert.match(regra(estilo, '.nav-barra .conta'), /font-size:\s*min\(0\.8125rem, \d*\.?\d+vw\)/)
    assert.match(regra(estilo, '.nav .conta'), /min-width:\s*1\.385em/)
  })
})

describe('telas que a conferência passou a ver', () => {
  test('foto grande: Anterior e Próxima dividem a linha sem passar da tela, e empilham com letra grande', () => {
    assert.match(regra(anexos, '.anexo-visualizador-passar .botao'), /min-width:\s*0/)
    assert.match(regra(anexos, '.anexo-visualizador-topo'), /flex-wrap:\s*wrap/)
    assert.match(bloco(anexos, '@container (max-width: 17.5rem)'), /flex-direction:\s*column/)
  })

  test('aviso aberto com letra grande: uma foto por linha e o PDF com o nome embaixo do ícone', () => {
    const grande = bloco(anexos, '@container conteudo (max-width: 17.5rem)')
    assert.match(grande, /\.anexos-fotos\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)/)
    assert.match(grande, /\.anexo-pdf\s*\{[^}]*flex-direction:\s*column/)
  })

  test('"O que mudou" com letra grande: recuos menores', () => {
    assert.match(sobre, /\.janela-caixa\s*\{\s*container:\s*janela \/ inline-size/)
    assert.match(bloco(sobre, '@container janela (max-width: 17.5rem)'), /\.novidades > li\s*\{[^}]*padding-left:\s*1rem/)
  })
})
