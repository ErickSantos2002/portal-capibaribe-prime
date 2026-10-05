// Política de privacidade (RNF-10, RNF-11, RNF-12).
import { cleanup, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { abrir, apiFalsa, eu } from './apoioDeTeste'

beforeEach(() => localStorage.clear())
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('política de privacidade', () => {
  it('abre sem sessão e diz a finalidade de cada dado pessoal', async () => {
    apiFalsa({})
    abrir('/privacidade')
    expect(await screen.findByRole('heading', { name: 'Política de privacidade' })).toBeTruthy()
    const texto = document.querySelector('main')?.textContent ?? ''
    for (const dado of ['Nome de quem responde', 'Celular', 'E-mail', 'Aparelho']) {
      expect(texto).toContain(dado)
    }
    expect(texto).toContain('Para quê')
  })

  it('diz o que não guardamos e como apagar', async () => {
    apiFalsa({})
    abrir('/privacidade')
    await screen.findByRole('heading', { name: 'Política de privacidade' })
    const texto = document.querySelector('main')?.textContent ?? ''
    expect(texto).toContain('CPF')
    expect(texto).toContain('Apagar meus dados')
  })

  it('sem sessão, voltar leva à entrada', async () => {
    apiFalsa({})
    abrir('/privacidade')
    expect(await screen.findByRole('button', { name: 'Voltar' })).toBeTruthy()
  })

  it('também abre com sessão, com o menu', async () => {
    apiFalsa({ 'GET /api/acesso/eu': new Response(JSON.stringify(eu())) })
    abrir('/privacidade')
    expect(await screen.findByRole('heading', { name: 'Política de privacidade' })).toBeTruthy()
  })
})
