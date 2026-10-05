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

describe('recado', () => {
  it('aparece na mesma tela e some sozinho', () => {
    abrir()
    expect(status().textContent).toBe('')
    fireEvent.click(screen.getByText('na mesma tela'))
    expect(status().textContent).toBe('Voto registrado.')
    act(() => vi.advanceTimersByTime(3000))
    expect(status().textContent).toBe('')
  })

  it('some quando se troca de tela', async () => {
    abrir()
    fireEvent.click(screen.getByText('na mesma tela'))
    fireEvent.click(screen.getByText('ir'))
    await screen.findByText('tela B')
    expect(status().textContent).toBe('')
  })

  it('vem junto com a navegação e some sozinho', async () => {
    abrir()
    fireEvent.click(screen.getByText('publicar'))
    await screen.findByText('tela B')
    expect(status().textContent).toBe('Aviso publicado.')
    act(() => vi.advanceTimersByTime(3000))
    expect(status().textContent).toBe('')
  })
})
