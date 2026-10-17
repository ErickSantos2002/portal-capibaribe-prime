// M5 · revisões (A, R2): com letra grande, o topo vira uma faixa fixa fina (voltar ou placa à
// esquerda, tema à direita) e o título sai dela para o começo do conteúdo, rolando com a página.
// O recado continua DENTRO da faixa fixa: aparece na vista mesmo com a página rolada. Com a letra
// de fábrica, o topo é o de sempre. Ver duvidas-m5-letra.md, seção Revisões.
import { cleanup, render, screen, within } from '@testing-library/react'
import { createElement } from 'react'
import { createMemoryRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiFalsa, eu, json } from '../acesso/apoioDeTeste'
import { rotas } from '../rotas'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  delete document.documentElement.dataset.letra
})

async function abrirEnquetes(recado?: string) {
  apiFalsa({
    'GET /api/acesso/eu': json(200, eu()),
    'GET /api/enquetes': json(200, { itens: [] }),
  })
  const roteador = createMemoryRouter(rotas, {
    initialEntries: [{ pathname: '/enquetes', state: recado ? { recado } : null }],
  })
  render(createElement(RouterProvider, { router: roteador }))
  await screen.findByText('Nenhuma enquete aberta agora.')
  return {
    topo: document.querySelector('header.topo') as HTMLElement,
    conteudo: document.getElementById('conteudo') as HTMLElement,
    titulo: screen.getByRole('heading', { level: 1 }),
  }
}

describe('topo com a letra de fábrica', () => {
  it('é o de sempre: o título dentro do topo', async () => {
    const { topo, titulo } = await abrirEnquetes()
    expect(topo.classList.contains('faixa')).toBe(false)
    expect(topo.contains(titulo)).toBe(true)
  })
})

describe('topo com letra grande', () => {
  it('a faixa tem só a placa e o tema; o título é o primeiro do conteúdo', async () => {
    document.documentElement.dataset.letra = 'grande'
    const { topo, conteudo, titulo } = await abrirEnquetes()
    expect(topo.classList.contains('faixa')).toBe(true)
    expect(topo.contains(titulo)).toBe(false)
    expect(conteudo.firstElementChild).toBe(titulo)
    expect(titulo.textContent).toBe('Enquetes')
    // Continua sendo o título da página: o foco de troca de tela vai para ele.
    expect(titulo.getAttribute('tabindex')).toBe('-1')
    expect(within(topo).getByRole('button', { name: /tema/ })).toBeTruthy()
    expect(within(topo).getByRole('img', { name: /Bloco/ })).toBeTruthy()
  })

  it('R2: o recado aparece dentro da faixa fixa, não no conteúdo que rola', async () => {
    document.documentElement.dataset.letra = 'grande'
    const { topo, conteudo } = await abrirEnquetes('Enquete publicada.')
    const fechar = within(topo).getByRole('button', { name: 'Fechar' })
    expect((fechar.closest('.recado') as HTMLElement).textContent).toContain('Enquete publicada.')
    expect(conteudo.contains(fechar)).toBe(false)
  })
})
