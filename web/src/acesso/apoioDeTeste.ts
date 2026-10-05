// Apoio dos testes de tela do épico A: uma API de mentira por rota e o Portal inteiro montado
// num roteador de memória (as mesmas rotas e guardas de produção).
import { render } from '@testing-library/react'
import { createElement } from 'react'
import { createMemoryRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'
import { vi } from 'vitest'
import type { Eu, Papel } from '../api/tipos'
import { rotas } from '../rotas'

export function eu(papeis: Papel[] = [], precisa_trocar_senha = false, login = '1203'): Eu {
  return {
    unidade: { login, bloco: Number(login[0]), apartamento: login.slice(1) },
    papeis,
    gestao: papeis.length > 0,
    admin: papeis.includes('admin'),
    precisa_trocar_senha,
  }
}

export function json(status: number, corpo?: unknown): Response {
  if (status === 204) return new Response(null, { status })
  return new Response(JSON.stringify(corpo), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

type Resposta = Response | ((corpo: unknown) => Response)

export interface Chamada {
  metodo: string
  caminho: string
  corpo: unknown
}

/**
 * `apiFalsa({ 'POST /api/acesso/entrar': json(200, eu()) })`. `GET /api/acesso/eu` responde 401
 * se não for dado; o que não estiver na lista responde 404. Devolve a lista de chamadas feitas.
 */
export function apiFalsa(respostas: Record<string, Resposta>): Chamada[] {
  const chamadas: Chamada[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (caminho: string, opcoes?: RequestInit) => {
      const metodo = opcoes?.method ?? 'GET'
      const corpo = opcoes?.body ? JSON.parse(String(opcoes.body)) : undefined
      chamadas.push({ metodo, caminho, corpo })
      const resposta = respostas[`${metodo} ${caminho}`]
      if (typeof resposta === 'function') return resposta(corpo)
      if (resposta) return resposta.clone()
      if (caminho === '/api/acesso/eu') {
        return json(401, { codigo: 'sem_sessao', mensagem: 'Entre de novo.' })
      }
      if (caminho === '/api/avisos/nao-lidos') return json(200, { quantidade: 0 })
      return json(404, { detail: 'Not Found' })
    }),
  )
  return chamadas
}

export function abrir(caminho: string) {
  const roteador = createMemoryRouter(rotas, { initialEntries: [caminho] })
  render(createElement(RouterProvider, { router: roteador }))
  return roteador
}
