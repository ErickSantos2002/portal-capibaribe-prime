// "Sair" só esquece a sessão quando a API confirmou (204) ou já não havia sessão (401).
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Eu } from '../api/tipos'
import { useSessao } from './contextoSessao'
import { SessaoProvider } from './SessaoProvider'

const EU: Eu = {
  unidade: { login: '1203', bloco: 1, apartamento: '203' },
  papeis: [],
  gestao: false,
  admin: false,
  precisa_trocar_senha: false,
}

function api(statusDoSair: number) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (caminho: string) => {
      if (caminho === '/api/acesso/eu') {
        return new Response(JSON.stringify(EU), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }
      if (statusDoSair === 204) return new Response(null, { status: 204 })
      const corpo =
        statusDoSair === 401
          ? { codigo: 'sem_sessao', mensagem: 'Entre de novo.' }
          : { detail: 'Erro interno' }
      return new Response(JSON.stringify(corpo), {
        status: statusDoSair,
        headers: { 'Content-Type': 'application/json' },
      })
    }),
  )
}

function Sair() {
  const { eu, sair } = useSessao()
  const [erro, setErro] = useState('')
  return (
    <>
      <p>{eu ? `logado ${eu.unidade.login}` : 'sem sessão'}</p>
      <button onClick={() => sair().catch((e: Error) => setErro(e.message))}>sair</button>
      {erro && <p role="alert">{erro}</p>}
    </>
  )
}

function abrir() {
  render(
    <SessaoProvider>
      <Sair />
    </SessaoProvider>,
  )
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('sair', () => {
  it.each([204, 401])('com %i esquece a sessão', async (status) => {
    api(status)
    abrir()
    await screen.findByText('logado 1203')
    fireEvent.click(screen.getByText('sair'))
    expect(await screen.findByText('sem sessão')).toBeTruthy()
  })

  it('se a API falhar, continua logado e mostra o erro', async () => {
    api(500)
    abrir()
    await screen.findByText('logado 1203')
    fireEvent.click(screen.getByText('sair'))
    expect(await screen.findByRole('alert')).toBeTruthy()
    expect(screen.getByText('logado 1203')).toBeTruthy()
  })
})
