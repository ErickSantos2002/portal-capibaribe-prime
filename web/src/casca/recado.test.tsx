import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { createMemoryRouter, Outlet, useNavigate } from 'react-router'
import { RouterProvider } from 'react-router/dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useRecado } from './contextoRecado'
import { RecadoProvider } from './RecadoProvider'

function TelaA() {
  const recado = useRecado()
  const navegar = useNavigate()
  return (
    <>
      <button onClick={() => recado('Voto registrado.')}>na mesma tela</button>
      <button onClick={() => navegar('/b', { state: { recado: 'Aviso publicado.' } })}>
        publicar
      </button>
      <button onClick={() => navegar('/b')}>ir</button>
    </>
  )
}

function abrir() {
  const roteador = createMemoryRouter(
    [
      {
        element: (
          <RecadoProvider>
            <Outlet />
          </RecadoProvider>
        ),
        children: [
          { path: '/a', element: <TelaA /> },
          { path: '/b', element: <p>tela B</p> },
        ],
      },
    ],
    { initialEntries: ['/a'] },
  )
  render(<RouterProvider router={roteador} />)
}

const status = () => screen.getByRole('status')

beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }))
afterEach(() => {
  cleanup()
  vi.useRealTimers()
})

// Fechamento do M3: o recado sumia em 2,6 s, rápido demais para quem lê devagar. Agora fica até
// a pessoa fechar ou trocar de tela; vale para o de sucesso e para o de erro.
describe('recado', () => {
  it('aparece na mesma tela e fica até a pessoa fechar', () => {
    abrir()
    expect(status().textContent).toBe('')
    expect(screen.queryByRole('button', { name: 'Fechar' })).toBeNull()
    fireEvent.click(screen.getByText('na mesma tela'))
    expect(status().textContent).toBe('Voto registrado.')
    act(() => vi.advanceTimersByTime(60_000))
    expect(status().textContent).toBe('Voto registrado.')
    fireEvent.click(screen.getByRole('button', { name: 'Fechar' }))
    expect(status().textContent).toBe('')
    expect(screen.queryByRole('button', { name: 'Fechar' })).toBeNull()
  })

  it('é anunciado pelo leitor de tela, sem o botão no anúncio', () => {
    abrir()
    expect(status().getAttribute('aria-live')).toBe('polite')
    fireEvent.click(screen.getByText('na mesma tela'))
    expect(status().contains(screen.getByRole('button', { name: 'Fechar' }))).toBe(false)
  })

  it('um recado novo troca o de antes', () => {
    abrir()
    fireEvent.click(screen.getByText('na mesma tela'))
    fireEvent.click(screen.getByText('na mesma tela'))
    expect(screen.getAllByRole('button', { name: 'Fechar' })).toHaveLength(1)
  })

  it('some quando se troca de tela', async () => {
    abrir()
    fireEvent.click(screen.getByText('na mesma tela'))
    fireEvent.click(screen.getByText('ir'))
    await screen.findByText('tela B')
    expect(status().textContent).toBe('')
    expect(screen.queryByRole('button', { name: 'Fechar' })).toBeNull()
  })

  it('vem junto com a navegação e fica até a pessoa fechar', async () => {
    abrir()
    fireEvent.click(screen.getByText('publicar'))
    await screen.findByText('tela B')
    expect(status().textContent).toBe('Aviso publicado.')
    act(() => vi.advanceTimersByTime(60_000))
    expect(status().textContent).toBe('Aviso publicado.')
    fireEvent.click(screen.getByRole('button', { name: 'Fechar' }))
    expect(status().textContent).toBe('')
  })
})
