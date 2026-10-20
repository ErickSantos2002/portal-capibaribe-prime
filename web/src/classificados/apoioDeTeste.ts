// Classificados · apoio dos testes de tela: dados fictícios no formato da API e a API de mentira
// com a sessão (o Portal inteiro montado, como em `acesso/apoioDeTeste`).
import type { Eu } from '../api/tipos'
import { apiFalsa, json, type Chamada } from '../acesso/apoioDeTeste'
import type { Anuncio, AnuncioResumo, CategoriaClassificado } from './tipos'

export const CATEGORIAS: CategoriaClassificado[] = [
  { id: 1, nome: 'Móveis' },
  { id: 2, nome: 'Eletrodomésticos' },
  { id: 4, nome: 'Material de obra e acabamento' },
  { id: 8, nome: 'Outros' },
]

export const CAPA = 'https://conta.r2.cloudflarestorage.com/portal/classificados/capa?x=1'

export function resumo(id: number, extra: Partial<AnuncioResumo> = {}): AnuncioResumo {
  return {
    id,
    tipo: 'venda',
    categoria: CATEGORIAS[0],
    titulo: `Anúncio ${id}`,
    preco_centavos: 35000,
    capa: null,
    unidade: { login: '2304', bloco: 2, apartamento: '304' },
    em: new Date().toISOString(),
    situacao: 'ativo',
    vencido: false,
    escondido: false,
    avisos_abertos: null,
    ...extra,
  }
}

export function anuncio(extra: Partial<Anuncio> = {}): Anuncio {
  return {
    id: 7,
    tipo: 'venda',
    categoria: CATEGORIAS[0],
    titulo: 'Sofá de 3 lugares',
    descricao: 'Sofá cinza, sem manchas.\nRetirar no Bloco 2.',
    preco_centavos: 35000,
    contato: '81999990001',
    celular: true,
    unidade: { login: '2304', bloco: 2, apartamento: '304' },
    publicado_em: '2026-10-15T15:00:00Z',
    renovado_em: null,
    vence_em: '2026-11-14T15:00:00Z',
    situacao: 'ativo',
    motivo_encerramento: null,
    vencido: false,
    escondido: false,
    fotos: [
      { id: 11, url: 'https://conta.r2.cloudflarestorage.com/portal/classificados/a?x=1' },
      { id: 12, url: 'https://conta.r2.cloudflarestorage.com/portal/classificados/b?x=1' },
    ],
    meu: false,
    pode_renovar: false,
    ja_avisei: false,
    avisos: null,
    ...extra,
  }
}

/** A API de mentira com a sessão de `quem` e as categorias. */
export function apiClassificados(
  quem: Eu,
  respostas: Record<string, Response | ((corpo: unknown) => Response)> = {},
): Chamada[] {
  return apiFalsa({
    'GET /api/acesso/eu': json(200, quem),
    'GET /api/classificados/categorias': json(200, { itens: CATEGORIAS }),
    ...respostas,
  })
}
