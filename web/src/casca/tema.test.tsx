import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { BotaoTema } from './BotaoTema'
import { CHAVE_TEMA, lerTema } from './tema'

beforeEach(() => {
  localStorage.clear()
  delete document.documentElement.dataset.tema
})

afterEach(cleanup)

describe('tema', () => {
  it('começa no claro, mesmo com o aparelho no escuro', () => {
    expect(lerTema()).toBe('claro')
    render(<BotaoTema />)
    expect(screen.getByRole('img', { name: 'Usar tema escuro' })).toBeTruthy()
    expect(document.documentElement.dataset.tema).toBeUndefined()
  })

  it('o botão alterna, grava a escolha e troca o ícone', () => {
    render(<BotaoTema />)
    fireEvent.click(screen.getByRole('button'))
    expect(document.documentElement.dataset.tema).toBe('escuro')
    expect(localStorage.getItem(CHAVE_TEMA)).toBe('escuro')
    expect(screen.getByRole('img', { name: 'Usar tema claro' })).toBeTruthy()

    fireEvent.click(screen.getByRole('button'))
    expect(document.documentElement.dataset.tema).toBeUndefined()
    expect(localStorage.getItem(CHAVE_TEMA)).toBe('claro')
  })

  it('lembra a escolha salva', () => {
    localStorage.setItem(CHAVE_TEMA, 'escuro')
    expect(lerTema()).toBe('escuro')
    render(<BotaoTema />)
    expect(screen.getByRole('img', { name: 'Usar tema claro' })).toBeTruthy()
  })

  it('valor estranho no armazenamento vira claro', () => {
    localStorage.setItem(CHAVE_TEMA, 'roxo')
    expect(lerTema()).toBe('claro')
  })
})
