// M5 · revisões (U6): telefone que não quebra no meio do número e e-mail que quebra nos pontos
// naturais (depois do @, antes dos pontos), em vez de "example.co / m".
import { cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { Celular, Email } from './Contato'

afterEach(cleanup)

describe('Celular', () => {
  it('mostra o número formatado, com o número (sem o DDD) preso numa linha', () => {
    const { container } = render(<Celular digitos="81900000003" />)
    expect(container.textContent).toBe('(81) 9 0000-0003')
    expect(container.querySelector('.fone-numero')!.textContent).toBe('9 0000-0003')
  })

  it('número que não se reconhece fica como veio', () => {
    const { container } = render(<Celular digitos="123" />)
    expect(container.textContent).toBe('123')
  })
})

describe('Email', () => {
  it('o texto é o e-mail inteiro (copiar e colar continua igual)', () => {
    const { container } = render(<Email endereco="gabriela.rangel.1101@example.com" />)
    expect(container.textContent).toBe('gabriela.rangel.1101@example.com')
  })

  it('pontos de quebra depois do @ e antes de cada ponto', () => {
    const { container } = render(<Email endereco="gabriela.rangel.1101@example.com" />)
    expect(container.querySelector('.email')!.innerHTML).toBe(
      'gabriela<wbr>.rangel<wbr>.1101@<wbr>example<wbr>.com',
    )
  })
})
