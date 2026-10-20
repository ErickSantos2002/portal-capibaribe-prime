// Classificados · a administração (spec, seções 4 e 9): as categorias (a mesma tela das
// indicações), o link no painel e as frases do histórico.
import { cleanup, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { abrir, eu, json } from '../acesso/apoioDeTeste'
import { oQueFez } from '../administracao/frases'
import type { ItemHistorico } from '../administracao/tipos'
import { apiClassificados, CATEGORIAS } from './apoioDeTeste'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

const COMISSAO = eu(['comissao'], false, '2304')
const ADMIN = eu(['admin'], false, '1101')
const ESPERA = { timeout: 4000 }

describe('categorias dos classificados', () => {
  it('admin vê a lista, cria e renomeia pelas rotas dos classificados', async () => {
    const chamadas = apiClassificados(ADMIN, {
      'POST /api/classificados/categorias': json(201, { id: 12, nome: 'Livros' }),
      'PUT /api/classificados/categorias/2': json(200, { id: 2, nome: 'Eletrodomésticos e cozinha' }),
    })
    abrir('/classificados/categorias')
    await screen.findByRole('heading', { level: 1, name: 'Categorias dos classificados' }, ESPERA)
    const lista = await screen.findByRole('list', { name: 'Categorias' }, ESPERA)
    expect(within(lista).getAllByRole('listitem')).toHaveLength(CATEGORIAS.length)
    fireEvent.change(screen.getByLabelText('Categoria nova'), { target: { value: 'Livros' } })
    fireEvent.click(screen.getByRole('button', { name: 'Criar categoria' }))
    fireEvent.click(screen.getByRole('button', { name: 'Renomear Eletrodomésticos' }))
    fireEvent.change(screen.getByLabelText('Novo nome de Eletrodomésticos'), {
      target: { value: 'Eletrodomésticos e cozinha' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar o nome' }))
    await waitFor(() =>
      expect(chamadas.filter((c) => c.metodo !== 'GET').map((c) => [c.metodo, c.caminho, c.corpo])).toEqual([
        ['POST', '/api/classificados/categorias', { nome: 'Livros' }],
        ['PUT', '/api/classificados/categorias/2', { nome: 'Eletrodomésticos e cozinha' }],
      ]),
    )
  })

  it('Comissão não vê o link no painel; admin vê', async () => {
    const PAINEL = { resumo: { total: 0, ativadas: 0, percentual: 0 }, blocos: [], unidades: [] }
    apiClassificados(COMISSAO, { 'GET /api/admin/unidades': json(200, PAINEL) })
    abrir('/unidades')
    await screen.findByRole('heading', { level: 1 }, ESPERA)
    await waitFor(() => expect(screen.queryByText('Carregando…')).toBeNull())
    expect(screen.queryByRole('link', { name: /Categorias dos classificados/ })).toBeNull()
    cleanup()
    apiClassificados(ADMIN, { 'GET /api/admin/unidades': json(200, PAINEL) })
    abrir('/unidades')
    const link = await screen.findByRole('link', { name: /Categorias dos classificados/ }, ESPERA)
    expect(link.getAttribute('href')).toBe('/classificados/categorias')
  })
})

describe('histórico', () => {
  const base: ItemHistorico = {
    id: 1,
    ocorrido_em: '2026-11-02T21:03:00Z',
    unidade: { login: '2304', bloco: 2, apartamento: '304' },
    acao: 'classificado_escondido',
    entidade: 'anuncio',
    entidade_id: 7,
    unidade_afetada: null,
    aviso_titulo: null,
    detalhes: {},
  }

  it('frases das ações novas, sem o título do anúncio', () => {
    expect(oQueFez(base)).toBe('escondeu um anúncio dos classificados')
    expect(oQueFez({ ...base, acao: 'classificado_aviso_resolvido' })).toBe(
      'resolveu um aviso num anúncio dos classificados',
    )
    expect(
      oQueFez({ ...base, unidade: null, acao: 'classificado_aviso_email', detalhes: { reservados: 1 } }),
    ).toBe('mandou e-mail à administração sobre um aviso num anúncio')
    expect(
      oQueFez({
        ...base,
        acao: 'categoria_classificado_criada',
        entidade: 'categoria_classificado',
        detalhes: { categoria: 'Livros' },
      }),
    ).toBe('criou a categoria “Livros” nos classificados')
    expect(
      oQueFez({
        ...base,
        acao: 'categoria_classificado_renomeada',
        entidade: 'categoria_classificado',
        detalhes: { categoria: 'Brinquedos' },
      }),
    ).toBe('renomeou uma categoria dos classificados para “Brinquedos”')
    expect(
      oQueFez({
        ...base,
        unidade: null,
        acao: 'classificados_faxina',
        entidade: null,
        entidade_id: null,
        detalhes: { anuncios: 2, fotos: 1 },
      }),
    ).toBe('apagou 2 anúncios e 1 foto dos classificados que já tinham acabado')
  })
})
