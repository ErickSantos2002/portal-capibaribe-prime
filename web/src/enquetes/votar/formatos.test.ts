import { describe, expect, it } from 'vitest'
import { noDestino, participacaoEmTexto, porcentagem, quandoTermina, votosEmTexto } from './formatos'

describe('quandoTermina', () => {
  const agora = new Date('2026-10-20T12:00:00Z')

  it('dia e hora de Recife, como se fala', () => {
    expect(quandoTermina('2026-11-10T23:00:00Z', agora)).toBe('10 de novembro, às 20h')
    expect(quandoTermina('2026-11-10T22:30:00Z', agora)).toBe('10 de novembro, às 19h30')
  })

  it('meia-noite e outro ano', () => {
    expect(quandoTermina('2026-11-01T03:00:00Z', agora)).toBe('1 de novembro, às 0h')
    expect(quandoTermina('2027-01-05T15:00:00Z', agora)).toBe('5 de janeiro de 2027, às 12h')
  })
})

describe('porcentagem', () => {
  it('arredonda e não divide por zero', () => {
    expect(porcentagem(1, 3)).toBe(33)
    expect(porcentagem(2, 3)).toBe(67)
    expect(porcentagem(0, 0)).toBe(0)
    expect(porcentagem(320, 320)).toBe(100)
  })
})

describe('textos', () => {
  it('votos no singular e no plural', () => {
    expect(votosEmTexto(0)).toBe('0 votos')
    expect(votosEmTexto(1)).toBe('1 voto')
    expect(votosEmTexto(88)).toBe('88 votos')
  })

  it('participação', () => {
    expect(participacaoEmTexto({ votaram: 192, total: 320 })).toBe(
      '192 de 320 apartamentos votaram (60%).',
    )
    expect(participacaoEmTexto({ votaram: 1, total: 64 })).toBe('1 de 64 apartamentos votou (2%).')
    expect(participacaoEmTexto({ votaram: 0, total: 64 })).toBe('Nenhum apartamento votou ainda.')
  })

  it('a unidade está no destino', () => {
    expect(noDestino({ para_todos: true, blocos: [] }, 3)).toBe(true)
    expect(noDestino({ para_todos: false, blocos: [1, 2] }, 2)).toBe(true)
    expect(noDestino({ para_todos: false, blocos: [1, 2] }, 3)).toBe(false)
  })
})
