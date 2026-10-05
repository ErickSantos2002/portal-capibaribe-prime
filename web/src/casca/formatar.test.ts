import { describe, expect, it } from 'vitest'
import { formatarCelular, formatarData, nomeDaUnidade, nomeDoPapel } from './formatar'

describe('formatar', () => {
  it('unidade como o morador fala', () => {
    expect(nomeDaUnidade({ login: '1007', bloco: 1, apartamento: '007' })).toBe('Bloco 1, 007')
  })

  it('celular só com dígitos ganha a máscara', () => {
    expect(formatarCelular('81912345678')).toBe('(81) 9 1234-5678')
    expect(formatarCelular('8133334444')).toBe('(81) 3333-4444')
    expect(formatarCelular(null)).toBe('')
  })

  it('data no horário de Recife, não no UTC', () => {
    // 02:30 UTC do dia 4 ainda é dia 3 em Recife (UTC−3).
    expect(formatarData('2026-11-04T02:30:00Z')).toBe('3 de novembro')
  })

  it('nome do papel', () => {
    expect(nomeDoPapel('comissao')).toBe('Comissão')
    expect(nomeDoPapel('admin')).toBe('Administrador')
  })
})
