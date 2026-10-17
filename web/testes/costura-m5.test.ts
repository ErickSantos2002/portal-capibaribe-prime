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

describe('4: abas de baixo nunca encostam', () => {
  test('com a tela estreita para a letra, a aba tem pelo menos a largura da palavra', () => {
    assert.match(bloco(estilo, '@container raiz (max-width: 22rem)'), /\.nav a\s*\{[^}]*min-width:\s*min-content/)
  })

  test('com cinco abas, sempre (com a letra de fábrica "Documentos" já não cabia)', () => {
    const cinco = bloco(estilo, '@container raiz not (min-width: 56.25rem)')
    assert.match(cinco, /\.nav:has\(> a:nth-of-type\(5\)\) a\s*\{[^}]*min-width:\s*min-content/)
  })

  test('o teto da letra das abas (dúvida 1) continua', () => {
    assert.match(regra(estilo, '.nav a'), /font-size:\s*min\(0\.9375rem, 5\.5vw\)/)
  })

  test('o número de não lidos não passa da borda da aba (R4: preso no canto, letra com teto)', () => {
    assert.match(regra(estilo, '.nav .conta'), /font-size:\s*min\(0\.8125rem, 4\.75vw\)/)
    assert.match(regra(estilo, '.nav .conta'), /min-width:\s*1\.385em/)
    const estreita = estilo.slice(estilo.lastIndexOf('@container raiz (max-width: 22rem)'))
    assert.match(bloco(estreita, '@container raiz (max-width: 22rem)'), /\.nav \.conta\s*\{[^}]*right:\s*0\.125rem/)
    // Depois da regra de base (mesmo peso: a última vence).
    assert.ok(estilo.lastIndexOf('@container raiz (max-width: 22rem)') > estilo.indexOf('\n.nav .conta {'))
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
