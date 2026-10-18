// Indicações · apoio dos testes de tela: dados fictícios no formato da API e a API de mentira
// com a sessão (o Portal inteiro montado, como em `acesso/apoioDeTeste`).
import type { Eu } from '../api/tipos'
import { apiFalsa, json, type Chamada } from '../acesso/apoioDeTeste'
import type { CategoriaServico, Prestador, PrestadorResumo } from './tipos'

export const CATEGORIAS: CategoriaServico[] = [
  { id: 1, nome: 'Móveis planejados' },
  { id: 2, nome: 'Ar-condicionado' },
  { id: 5, nome: 'Eletricista' },
  { id: 11, nome: 'Outros' },
]

export function resumo(id: number, extra: Partial<PrestadorResumo> = {}): PrestadorResumo {
  return {
    id,
    categoria: CATEGORIAS[0],
    nome: `Prestador ${id}`,
    recomendam: 1,
    nao_recomendam: 0,
    trecho: null,
    avisos_abertos: null,
    ...extra,
  }
}

export function prestador(extra: Partial<Prestador> = {}): Prestador {
  return {
    id: 7,
    categoria: CATEGORIAS[0],
    nome: 'Marcenaria Exemplo',
    telefone: '81999990001',
    celular: true,
    instagram: null,
    recomendam: 2,
    nao_recomendam: 1,
    opinioes: [
      {
        id: 31,
        unidade: { login: '1101', bloco: 1, apartamento: '101' },
        recomenda: true,
        comentario: 'Fez a cozinha no prazo.',
        em: '2026-10-15T15:00:00Z',
        minha: false,
      },
      {
        id: 32,
        unidade: { login: '2304', bloco: 2, apartamento: '304' },
        recomenda: false,
        comentario: null,
        em: '2026-10-10T15:00:00Z',
        minha: false,
      },
    ],
    minha_opiniao: null,
    pode_corrigir: false,
    ja_avisei: false,
    escondido: false,
    avisos: null,
    ...extra,
  }
}

/** A API de mentira com a sessão de `quem` e as categorias. */
export function apiIndicacoes(
  quem: Eu,
  respostas: Record<string, Response | ((corpo: unknown) => Response)> = {},
): Chamada[] {
  return apiFalsa({
    'GET /api/acesso/eu': json(200, quem),
    'GET /api/indicacoes/categorias': json(200, { itens: CATEGORIAS }),
    ...respostas,
  })
}
