// M4 · ajustes das revisões finais, ponto 8: o recado no fluxo da página (não cobre o conteúdo).
// As regras de CSS que o jsdom não desenha estão em `testes/estilo-m4.test.ts` (e nos prints).
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { createElement } from 'react'
import { createMemoryRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiFalsa, eu, json } from '../acesso/apoioDeTeste'
import { rotas } from '../rotas'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('8: o recado não cobre o conteúdo', () => {
  it('aparece numa linha própria do topo, antes do conteúdo, e continua anunciado', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, eu()),
      'GET /api/enquetes': json(200, { itens: [] }),
    })
    const roteador = createMemoryRouter(rotas, {
      initialEntries: [{ pathname: '/enquetes', state: { recado: 'Enquete publicada.' } }],
    })
    render(createElement(RouterProvider, { router: roteador }))
    await screen.findByText('Nenhuma enquete aberta agora.')
    const topo = document.querySelector('header.topo') as HTMLElement
    const fechar = within(topo).getByRole('button', { name: 'Fechar' })
    const recado = fechar.closest('.recado') as HTMLElement
    expect(recado.textContent).toContain('Enquete publicada.')
    // No fluxo da página, antes do conteúdo (o topo cresce; nada fica por cima).
    const conteudo = document.getElementById('conteudo') as HTMLElement
    expect(recado.compareDocumentPosition(conteudo) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(screen.getByRole('status').textContent).toBe('Enquete publicada.')
    fireEvent.click(fechar)
    expect(screen.queryByRole('button', { name: 'Fechar' })).toBeNull()
    expect(screen.getByRole('status').textContent).toBe('')
  })
})
