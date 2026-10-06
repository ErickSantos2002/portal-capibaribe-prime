// Datas do mural e do evento, sempre no horário de Recife.
import { describe, expect, it } from 'vitest'
import {
  dataEmBloco,
  dataPorExtenso,
  deRecife,
  eventoCurto,
  eventoNaLinha,
  eventoPorExtenso,
  paraOFormulario,
} from './datas'

describe('datas do aviso (America/Recife)', () => {
  it('data em bloco: dia com dois dígitos e mês abreviado', () => {
    expect(dataEmBloco('2026-10-04T12:00:00Z')).toEqual({ dia: '04', mes: 'out' })
    // 01:00 em UTC ainda é dia 3 em Recife.
    expect(dataEmBloco('2026-11-04T01:00:00Z')).toEqual({ dia: '03', mes: 'nov' })
  })

  it('evento no mural: "Sáb, 11/10 · 9h", com minutos quando há', () => {
    const antes = new Date('2026-10-01T00:00:00Z')
    expect(eventoCurto('2026-10-10T12:00:00Z', antes)).toBe('Sáb, 10/10 · 9h')
    expect(eventoCurto('2026-10-10T22:30:00Z', antes)).toBe('Sáb, 10/10 · 19h30')
  })

  it('evento que já passou: "Já aconteceu" no lugar do horário', () => {
    const depois = new Date('2026-10-12T00:00:00Z')
    expect(eventoCurto('2026-10-10T12:00:00Z', depois)).toBe('Sáb, 10/10 · Já aconteceu')
  })

  it('evento por extenso, para o quadro "Quando"', () => {
    expect(eventoPorExtenso('2026-10-10T12:00:00Z')).toBe('Sábado, 10 de outubro, 9h')
    expect(eventoPorExtenso('2026-12-01T13:05:00Z')).toBe('Terça-feira, 1º de dezembro, 10h05')
  })

  it('revisão UX 1: evento em outro ano mostra o ano (senão parece desta semana)', () => {
    const em2026 = new Date('2026-10-06T12:00:00Z')
    expect(eventoCurto('2027-10-09T12:00:00Z', em2026)).toBe('Sáb, 09/10/27 · 9h')
    expect(eventoPorExtenso('2027-10-09T12:00:00Z', em2026)).toBe(
      'Sábado, 9 de outubro de 2027, 9h',
    )
    expect(eventoCurto('2025-10-11T12:00:00Z', em2026)).toBe('Sáb, 11/10/25 · Já aconteceu')
    // No mesmo ano, sem o ano.
    expect(eventoPorExtenso('2026-10-10T12:00:00Z', em2026)).toBe('Sábado, 10 de outubro, 9h')
  })

  it('dúvida A: bloco com o ano quando é de outro ano', () => {
    const em2026 = new Date('2026-10-06T12:00:00Z')
    expect(dataEmBloco('2026-10-10T12:00:00Z', em2026)).toEqual({ dia: '10', mes: 'out' })
    expect(dataEmBloco('2027-10-09T12:00:00Z', em2026)).toEqual({
      dia: '09',
      mes: 'out',
      ano: '2027',
    })
  })

  it('dúvida A: linha do evento no cartão sem repetir a data do bloco', () => {
    const em2026 = new Date('2026-10-06T12:00:00Z')
    const publicado = '2026-10-06T12:00:00Z'
    expect(eventoNaLinha('2026-10-10T12:00:00Z', publicado, em2026)).toBe(
      'Sáb, 9h · publicado 6/10',
    )
    expect(eventoNaLinha('2026-10-03T22:30:00Z', publicado, em2026)).toBe(
      'Já aconteceu · publicado 6/10',
    )
  })

  it('dúvida A: data por extenso para o leitor de tela', () => {
    const em2026 = new Date('2026-10-06T12:00:00Z')
    expect(dataPorExtenso('2026-10-10T12:00:00Z', em2026)).toBe('10 de outubro')
    expect(dataPorExtenso('2027-10-09T12:00:00Z', em2026)).toBe('9 de outubro de 2027')
  })

  it('formulário: dia e hora de Recife, ida e volta', () => {
    expect(paraOFormulario('2026-10-11T12:00:00Z')).toEqual({ data: '2026-10-11', hora: '09:00' })
    expect(deRecife('2026-10-11', '09:00')).toBe('2026-10-11T09:00:00-03:00')
    expect(paraOFormulario(deRecife('2026-12-31', '23:30'))).toEqual({
      data: '2026-12-31',
      hora: '23:30',
    })
  })
})
