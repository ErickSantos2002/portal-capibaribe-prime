// A versão do Portal e o "O que mudou" andam juntos (README, seção Versões).
import { describe, expect, it } from 'vitest'
import pacote from '../../package.json'
import { NOVIDADES, VERSAO, formatarDataDaVersao } from './novidades'

const SEMVER = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/

function comparar(a: string, b: string): number {
  const [x, y] = [a, b].map((v) => v.split('.').map(Number))
  for (let i = 0; i < 3; i++) if (x[i] !== y[i]) return x[i] - y[i]
  return 0
}

describe('versão e novidades', () => {
  it('a versão vem do package.json, injetada pelo Vite', () => {
    expect(VERSAO).toBe(pacote.version)
    expect(pacote.version).toBe('1.1.0')
  })

  it('a primeira novidade é a da versão atual', () => {
    expect(NOVIDADES[0].versao).toBe(pacote.version)
  })

  it('versões no formato semver, da mais nova para a mais velha, sem repetir', () => {
    for (const { versao } of NOVIDADES) expect(versao).toMatch(SEMVER)
    for (let i = 1; i < NOVIDADES.length; i++) {
      expect(comparar(NOVIDADES[i - 1].versao, NOVIDADES[i].versao)).toBeGreaterThan(0)
    }
  })

  it('datas reais (AAAA-MM-DD), nenhuma no futuro, e nunca mais nova que a versão anterior', () => {
    const hoje = new Date().toISOString().slice(0, 10)
    for (const { data } of NOVIDADES) {
      expect(data).toMatch(/^\d{4}-\d{2}-\d{2}$/)
      expect(Number.isNaN(new Date(`${data}T12:00:00Z`).getTime())).toBe(false)
      expect(data <= hoje).toBe(true)
    }
    for (let i = 1; i < NOVIDADES.length; i++) {
      expect(NOVIDADES[i - 1].data >= NOVIDADES[i].data).toBe(true)
    }
  })

  it('toda versão tem ao menos um item escrito', () => {
    for (const { itens } of NOVIDADES) {
      expect(itens.length).toBeGreaterThan(0)
      for (const item of itens) expect(item.trim()).not.toBe('')
    }
  })

  it('a data aparece por extenso, sem escorregar de dia pelo fuso', () => {
    expect(formatarDataDaVersao('2026-10-06')).toBe('6 de outubro de 2026')
    expect(formatarDataDaVersao('2027-01-01')).toBe('1 de janeiro de 2027')
  })
})
