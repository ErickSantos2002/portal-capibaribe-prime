// Navegação com a bola do Menu (spec docs/superpowers/specs/2026-10-18-navegacao-bola-design.md,
// seções 3 e 6): a barra do celular (4 lugares fixos e a bola no meio) e o menu lateral agrupado
// do computador, os dois saindo da lista única de lugares. O CSS mostra um ou outro; o jsdom não
// desenha, então aqui os dois estão no DOM e cada teste olha dentro do seu.
import { cleanup, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { abrir, apiFalsa, eu, json } from '../acesso/apoioDeTeste'
import type { Eu } from '../api/tipos'

function api(quem: Eu, naoLidos = 0) {
  apiFalsa({
    'GET /api/acesso/eu': json(200, quem),
    'GET /api/avisos/nao-lidos': json(200, { quantidade: naoLidos }),
  })
}

async function barra(): Promise<HTMLElement> {
  await screen.findByRole('navigation', { name: 'Seções do Portal' })
  const elemento = document.querySelector<HTMLElement>('.nav-barra')
  if (!elemento) throw new Error('sem .nav-barra')
  return elemento
}

function lateral(): HTMLElement {
  const elemento = document.querySelector<HTMLElement>('.nav-lateral')
  if (!elemento) throw new Error('sem .nav-lateral')
  return elemento
}

beforeEach(() => localStorage.clear())
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  delete document.documentElement.dataset.largura
})

describe('a barra do celular', () => {
  for (const [quem, sessao] of [
    ['morador', eu()],
    ['admin', eu(['admin'])],
  ] as const) {
    it(`${quem}: 4 lugares na ordem e a bola "Menu" entre o 2º e o 3º`, async () => {
      api(sessao)
      abrir('/avisos')
      const nav = await barra()
      const links = within(nav).getAllByRole('link')
      expect(links.map((l) => l.textContent?.replace(/Docs$/, ''))).toEqual([
        'Avisos',
        'Enquetes',
        'Documentos',
        'Minha unidade',
      ])
      const bola = within(nav).getByRole('button', { name: 'Menu' })
      expect(bola.getAttribute('aria-haspopup')).toBe('dialog')
      expect(bola.getAttribute('aria-expanded')).toBe('false')
      const ordem = [...nav.querySelectorAll('a, button')]
      expect(ordem.indexOf(bola)).toBe(2)
      expect(within(nav).queryByText('Unidades')).toBeNull()
    })
  }

  it('Unidades fica no menu lateral do admin, sob o título "Gestão"', async () => {
    api(eu(['admin']))
    abrir('/avisos')
    await barra()
    const titulos = within(lateral()).getAllByRole('heading', { level: 2 })
    expect(titulos.map((t) => t.textContent)).toEqual(['Dia a dia', 'Gestão'])
    const gestao = titulos[1]
    const unidades = within(lateral()).getByRole('link', { name: 'Unidades' })
    expect(gestao.compareDocumentPosition(unidades) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('o morador não tem o título "Gestão" no menu lateral', async () => {
    api(eu())
    abrir('/avisos')
    await barra()
    expect(within(lateral()).queryByRole('heading', { name: 'Gestão' })).toBeNull()
  })

  it('em /avisos, a aba Avisos é a atual e mostra os não lidos', async () => {
    api(eu(), 3)
    abrir('/avisos')
    const nav = await barra()
    const aba = within(nav).getByRole('link', { name: /Avisos/ })
    expect(aba.getAttribute('aria-current')).toBe('page')
    expect(await within(nav).findByLabelText('3 não lidos')).toBeTruthy()
    expect(within(nav).getByRole('button', { name: 'Menu' }).hasAttribute('data-aqui')).toBe(false)
  })

  it('num lugar fora da barra (Unidades), nenhuma aba é a atual e a bola acende', async () => {
    api(eu(['admin']))
    abrir('/unidades')
    const nav = await barra()
    await waitFor(() => expect(within(nav).getByRole('button', { name: 'Menu' }).hasAttribute('data-aqui')).toBe(true))
    for (const link of within(nav).getAllByRole('link')) expect(link.hasAttribute('aria-current')).toBe(false)
  })

  it('o link Documentos se chama "Documentos" também na tela estreita ("Docs" é só visual)', async () => {
    document.documentElement.dataset.largura = 'estreita'
    api(eu())
    abrir('/avisos')
    const nav = await barra()
    const documentos = within(nav).getByRole('link', { name: 'Documentos' })
    expect(documentos.querySelector('.rot-curto')?.getAttribute('aria-hidden')).toBe('true')
    expect(documentos.querySelector('.rot-curto')?.textContent).toBe('Docs')
  })
})
