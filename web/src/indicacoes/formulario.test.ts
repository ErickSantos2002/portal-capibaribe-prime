// Indicações · as regras do formulário do prestador, sem tela.
import { describe, expect, it } from 'vitest'
import { conferirPrestador, digitosDoTelefone } from './formulario'

const BASE = { categoria: '1', nome: 'Marcenaria Exemplo', telefone: '', instagram: '' }

describe('telefone do prestador', () => {
  it('celular sem o nono dígito ganha o 9 (o mesmo número que a API guarda)', () => {
    expect(digitosDoTelefone('(81) 9999-0001')).toBe('81999990001')
    expect(digitosDoTelefone('81 8765-4321')).toBe('81987654321')
    expect(digitosDoTelefone('+55 81 6123-4567')).toBe('81961234567')
    expect(digitosDoTelefone('(81) 9 9999-0001')).toBe('81999990001')
  })

  it('fixo começa de 2 a 5 e fica com 10 dígitos', () => {
    expect(digitosDoTelefone('81 3333-4444')).toBe('8133334444')
    expect(digitosDoTelefone('55 81 2123-4567')).toBe('8121234567')
  })

  it('recusa o que não é celular nem fixo', () => {
    for (const ruim of ['81 1999-0001', '81 0999-0001', '81 8999-00011', '0819999-0001', '9999-0001']) {
      expect(digitosDoTelefone(ruim), ruim).toBeNull()
      expect(conferirPrestador({ ...BASE, telefone: ruim }).telefone, ruim).toBeTruthy()
    }
    expect(conferirPrestador({ ...BASE, telefone: '(81) 9999-0001' }).telefone).toBeUndefined()
  })
})
