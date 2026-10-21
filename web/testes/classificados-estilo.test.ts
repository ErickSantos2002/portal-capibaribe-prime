// Classificados · revisão de UX: regras de CSS que o jsdom não desenha, conferidas no texto dos
// arquivos (a conferência visual headless confere o resto). Cada teste falhava antes da correção.
// Rodar: npm test (ou node --test testes/classificados-estilo.test.ts, de web/)
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { describe, test } from 'node:test'

const ler = (caminho: string) =>
  readFileSync(new URL(`../src/${caminho}`, import.meta.url), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '')
const anexos = ler('avisos/anexos.css')
const classificados = ler('classificados/classificados.css')

function regra(css: string, seletor: string): string {
  const escapado = seletor.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const achado = new RegExp(`(^|\\n)\\s*${escapado}\\s*\\{([^}]*)\\}`).exec(css)
  return achado ? achado[2] : ''
}

describe('visor de fotos (comum)', () => {
  test('botões claros nos dois temas (o fundo é sempre preto)', () => {
    for (const seletor of ['.anexo-visualizador-topo .botao', '.anexo-visualizador-passar .botao']) {
      assert.match(regra(anexos, seletor), /background:\s*#ffffff/, seletor)
      assert.match(regra(anexos, seletor), /color:\s*#1f5e3b/, seletor)
    }
  })

  test('com a letra grande, as setas ficam do tamanho delas (a foto fica com a tela)', () => {
    const bloco = regra(anexos, ":root[data-letra='grande'] .anexo-visualizador-passar .botao")
    assert.match(bloco, /width:\s*auto/)
    assert.match(regra(anexos, ":root[data-letra='grande'] .anexo-visualizador-texto"), /display:\s*none/)
  })
})

describe('faixa de tipo', () => {
  test('quebra em linha, nunca rola (as quatro à vista)', () => {
    const bloco = regra(classificados, '.cla-tipos')
    assert.match(bloco, /flex-wrap:\s*wrap/)
    assert.doesNotMatch(bloco, /overflow-x:\s*(auto|scroll)/)
  })
})
