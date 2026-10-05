// Casca: guardas de rota, menu e layout com a API de mentira (spec do M1, seção 5.3).
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { createMemoryRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Eu, Papel } from './api/tipos'
import { rotas } from './rotas'

function eu(papeis: Papel[] = [], precisa_trocar_senha = false): Eu {
  return {
    unidade: { login: '1203', bloco: 1, apartamento: '203' },
    papeis,
    gestao: papeis.length > 0,
    admin: papeis.includes('admin'),
    precisa_trocar_senha,
  }
}

function json(status: number, corpo: unknown) {
  return new Response(JSON.stringify(corpo), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

/** API de mentira: `/api/acesso/eu` devolve `sessao` (ou 401); o resto, 404. */
function api(sessao: Eu | null, naoLidos = 0) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (caminho: string) => {
      if (caminho === '/api/acesso/eu') {
        return sessao
          ? json(200, sessao)
          : json(401, { codigo: 'sem_sessao', mensagem: 'Entre de novo.' })
      }
      if (caminho === '/api/avisos/nao-lidos') return json(200, { quantidade: naoLidos })
      return json(404, { detail: 'Not Found' })
    }),
  )
}

function abrir(caminho: string) {
  const roteador = createMemoryRouter(rotas, { initialEntries: [caminho] })
  render(<RouterProvider router={roteador} />)
  return roteador
}

beforeEach(() => localStorage.clear())
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('guardas', () => {
  it('sem sessão, o mural manda para a entrada', async () => {
    api(null)
    const roteador = abrir('/avisos')
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/entrar'))
    expect(await screen.findByText(/H-02/)).toBeTruthy()
  })

  it('sessão restrita vai para o primeiro acesso', async () => {
    api(eu([], true))
    const roteador = abrir('/avisos')
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/primeiro-acesso'))
  })

  it('a raiz abre o mural', async () => {
    api(eu())
    const roteador = abrir('/')
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/avisos'))
    expect(await screen.findByRole('heading', { level: 1, name: 'Avisos' })).toBeTruthy()
  })

  it('quem já entrou não vê a tela de entrar', async () => {
    api(eu())
    const roteador = abrir('/entrar')
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/avisos'))
  })

  it('unidade comum em tela de admin vê "Sem permissão"', async () => {
    api(eu())
    abrir('/unidades')
    expect(await screen.findByRole('heading', { name: 'Sem permissão' })).toBeTruthy()
  })

  it('unidade comum em tela de gestão vê "Sem permissão"', async () => {
    api(eu())
    abrir('/avisos/novo')
    expect(await screen.findByRole('heading', { name: 'Sem permissão' })).toBeTruthy()
  })

  it('Comissão abre a tela de novo aviso, mas não a de unidades', async () => {
    api(eu(['comissao']))
    abrir('/avisos/novo')
    expect(await screen.findByRole('heading', { name: 'Novo aviso' })).toBeTruthy()
    cleanup()
    abrir('/unidades')
    expect(await screen.findByRole('heading', { name: 'Sem permissão' })).toBeTruthy()
  })

  it('admin abre o painel de unidades', async () => {
    api(eu(['admin']))
    abrir('/unidades')
    expect(await screen.findByRole('heading', { name: 'Unidades' })).toBeTruthy()
  })

  it('a política de privacidade abre sem sessão', async () => {
    api(null)
    abrir('/privacidade')
    expect(await screen.findByRole('heading', { name: 'Política de privacidade' })).toBeTruthy()
  })

  it('caminho desconhecido mostra "Não encontrado"', async () => {
    api(eu())
    abrir('/qualquer-coisa')
    expect(await screen.findByRole('heading', { name: 'Não encontrado' })).toBeTruthy()
  })

  it('API fora do ar mostra o aviso e o botão de tentar de novo', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('Failed to fetch')
      }),
    )
    abrir('/avisos')
    expect(await screen.findByRole('button', { name: 'Tentar de novo' })).toBeTruthy()
  })
})

describe('layout', () => {
  it('menu de unidade comum: Avisos e Minha unidade, sem Unidades', async () => {
    api(eu())
    abrir('/avisos')
    const menu = await screen.findByRole('navigation', { name: 'Seções do Portal' })
    expect(menu.textContent).toContain('Avisos')
    expect(menu.textContent).toContain('Minha unidade')
    expect(menu.textContent).not.toContain('Unidades')
  })

  it('menu do admin tem Unidades', async () => {
    api(eu(['admin']))
    abrir('/avisos')
    const menu = await screen.findByRole('navigation', { name: 'Seções do Portal' })
    expect(menu.textContent).toContain('Unidades')
    expect(menu.textContent).toContain('Administrador')
  })

  it('a aba ativa é marcada e mostra os não lidos', async () => {
    api(eu(), 3)
    abrir('/avisos')
    const aba = await screen.findByRole('link', { name: /Avisos/ })
    expect(aba.getAttribute('aria-current')).toBe('page')
    expect(await screen.findByLabelText('3 não lidos')).toBeTruthy()
  })

  it('o topo mostra a placa da unidade', async () => {
    api(eu())
    abrir('/avisos')
    expect(
      (await screen.findAllByRole('img', { name: 'Bloco 1, apartamento 203' })).length,
    ).toBeGreaterThan(0)
  })

  it('tela de detalhe tem voltar e esconde as abas no celular', async () => {
    api(eu())
    abrir('/avisos/12')
    expect(await screen.findByRole('button', { name: 'Voltar' })).toBeTruthy()
    expect(document.querySelector('.app')?.classList.contains('detalhe')).toBe(true)
  })

  it('a entrada não tem topo nem menu, e tem o botão de tema solto', async () => {
    api(null)
    abrir('/entrar')
    await screen.findByText(/H-02/)
    expect(document.querySelector('.topo')).toBeNull()
    expect(screen.queryByRole('navigation')).toBeNull()
    expect(document.querySelector('.tema-btn.solto')).not.toBeNull()
  })

  it('o título da aba acompanha a tela', async () => {
    api(eu())
    abrir('/minha-unidade')
    await screen.findByRole('heading', { name: 'Minha unidade' })
    expect(document.title).toBe('Minha unidade · Portal Capibaribe Prime')
  })
})
