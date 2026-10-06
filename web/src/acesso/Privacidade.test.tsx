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

  it('quem vê os contatos: o apartamento, a Comissão e a administração (A6)', async () => {
    apiFalsa({})
    abrir('/privacidade')
    const quemVe = await screen.findByRole('heading', { name: 'Quem vê' })
    const texto = quemVe.nextElementSibling?.textContent ?? ''
    expect(texto).toContain('pela Comissão e pela administração do Portal')
  })

  it('diz quem é o responsável, como pedir e onde os dados ficam (A7)', async () => {
    apiFalsa({})
    abrir('/privacidade')
    await screen.findByRole('heading', { name: 'Quem cuida dos dados' })
    const texto = document.querySelector('main')?.textContent ?? ''
    expect(texto).toContain(
      'Erick Santos, morador que mantém o Portal, em nome da Comissão dos compradores do Capibaribe Prime',
    )
    expect(texto).toContain('grupo de WhatsApp dos compradores')
    expect(texto).toMatch(/Neon/)
    expect(texto).toMatch(/Vercel/)
    expect(texto).toContain('São Paulo')
    // Repositório público: nada que identifique o apartamento do responsável.
    expect(texto).not.toMatch(/\bBloco \d|\bapto\b|\b[1-5]\d{3}\b|CPF d/i)
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
