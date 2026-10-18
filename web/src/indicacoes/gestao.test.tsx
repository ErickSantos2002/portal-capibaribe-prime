// Indicações · a moderação (spec, seções 3.2, 4 e 8): "Para a gestão" no prestador aberto,
// esconder, resolver aviso, as categorias (só a administração) e as frases do histórico.
import { cleanup, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { abrir, eu, json } from '../acesso/apoioDeTeste'
import { oQueFez } from '../administracao/frases'
import type { ItemHistorico } from '../administracao/tipos'
import { apiIndicacoes, CATEGORIAS, prestador } from './apoioDeTeste'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

const MORADOR = eu()
const COMISSAO = eu(['comissao'], false, '2304')
const ADMIN = eu(['admin'], false, '1101')
const ESPERA = { timeout: 4000 }

const DA_GESTAO = prestador({
  pode_corrigir: true,
  avisos: [{ id: 5, motivo: 'O número não atende.', em: '2026-10-16T12:00:00Z' }],
})

async function aberto() {
  return screen.findByRole('heading', { level: 2, name: 'Marcenaria Exemplo' }, ESPERA)
}

describe('para a gestão', () => {
  it('morador não vê "Para a gestão"; Comissão e admin veem', async () => {
    apiIndicacoes(MORADOR, { 'GET /api/indicacoes/7': json(200, prestador()) })
    abrir('/indicacoes/7')
    await aberto()
    expect(screen.queryByRole('heading', { name: 'Para a gestão' })).toBeNull()
    expect(screen.queryByRole('button', { name: /Esconder/ })).toBeNull()

    for (const quem of [COMISSAO, ADMIN]) {
      cleanup()
      apiIndicacoes(quem, { 'GET /api/indicacoes/7': json(200, DA_GESTAO) })
      abrir('/indicacoes/7')
      await aberto()
      const secao = screen.getByRole('region', { name: 'Para a gestão' })
      expect(secao.textContent).toContain('O número não atende.')
      expect(within(secao).getByRole('button', { name: 'Esconder este prestador' })).toBeTruthy()
      expect(screen.getAllByRole('button', { name: 'Esconder esta opinião' })).toHaveLength(2)
    }
  })

  it('esconder o prestador pergunta e chama POST /api/indicacoes/7/esconder', async () => {
    const chamadas = apiIndicacoes(COMISSAO, {
      'GET /api/indicacoes/7': json(200, DA_GESTAO),
      'POST /api/indicacoes/7/esconder': json(204),
    })
    abrir('/indicacoes/7')
    await aberto()
    fireEvent.click(screen.getByRole('button', { name: 'Esconder este prestador' }))
    expect(chamadas.some((c) => c.metodo === 'POST')).toBe(false)
    const pergunta = screen.getByRole('group', { name: /Esconder este prestador\?/ })
    expect(pergunta.textContent).toContain(
      'Ele sai da lista e não volta. Quem tem o telefone dele não consegue indicá-lo de novo.',
    )
    fireEvent.click(within(pergunta).getByRole('button', { name: 'Esconder de vez' }))
    await waitFor(() =>
      expect(chamadas.some((c) => c.metodo === 'POST' && c.caminho === '/api/indicacoes/7/esconder')).toBe(
        true,
      ),
    )
  })

  it('esconder uma opinião chama POST /api/indicacoes/opinioes/31/esconder', async () => {
    const chamadas = apiIndicacoes(ADMIN, {
      'GET /api/indicacoes/7': json(200, DA_GESTAO),
      'POST /api/indicacoes/opinioes/31/esconder': json(204),
    })
    abrir('/indicacoes/7')
    await aberto()
    fireEvent.click(screen.getAllByRole('button', { name: 'Esconder esta opinião' })[0])
    const pergunta = screen.getByRole('group', { name: /Esconder esta opinião\?/ })
    fireEvent.click(within(pergunta).getByRole('button', { name: 'Esconder de vez' }))
    await waitFor(() =>
      expect(chamadas.some((c) => c.caminho === '/api/indicacoes/opinioes/31/esconder')).toBe(true),
    )
  })

  it('resolver um aviso chama POST /api/indicacoes/avisos/5/resolver e o tira da seção', async () => {
    let resolvido = false
    const chamadas = apiIndicacoes(COMISSAO, {
      'GET /api/indicacoes/7': () => json(200, resolvido ? { ...DA_GESTAO, avisos: [] } : DA_GESTAO),
      'POST /api/indicacoes/avisos/5/resolver': () => {
        resolvido = true
        return json(204)
      },
    })
    abrir('/indicacoes/7')
    await aberto()
    fireEvent.click(screen.getByRole('button', { name: 'Resolver' }))
    await waitFor(() => expect(screen.queryByText('O número não atende.')).toBeNull())
    expect(chamadas.some((c) => c.caminho === '/api/indicacoes/avisos/5/resolver')).toBe(true)
    expect(screen.getByText('Nenhum aviso aberto.')).toBeTruthy()
  })

  it('prestador escondido: o selo "Escondido da lista" e nada de esconder de novo', async () => {
    apiIndicacoes(ADMIN, {
      'GET /api/indicacoes/7': json(200, { ...DA_GESTAO, escondido: true, avisos: [] }),
    })
    abrir('/indicacoes/7')
    await aberto()
    expect(screen.getByText('Escondido da lista')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Esconder este prestador' })).toBeNull()
    expect(screen.queryByRole('button', { name: /minha opinião/ })).toBeNull()
  })
})

describe('categorias', () => {
  it('categorias: admin cria "Jardinagem" e renomeia; 409 categoria_ja_existe mostra o erro', async () => {
    const chamadas = apiIndicacoes(ADMIN, {
      'POST /api/indicacoes/categorias': (corpo) =>
        (corpo as { nome: string }).nome === 'Pintura'
          ? json(409, { codigo: 'categoria_ja_existe', mensagem: 'Já existe uma categoria com esse nome.' })
          : json(201, { id: 12, nome: 'Jardinagem' }),
      'PUT /api/indicacoes/categorias/5': json(200, { id: 5, nome: 'Eletricista e antena' }),
    })
    abrir('/indicacoes/categorias')
    await screen.findByRole('heading', { level: 1, name: 'Categorias das indicações' }, ESPERA)
    const lista = await screen.findByRole('list', { name: 'Categorias' }, ESPERA)
    expect(within(lista).getAllByRole('listitem').map((i) => i.textContent)).toEqual(
      CATEGORIAS.map((c) => expect.stringContaining(c.nome)),
    )
    expect(screen.queryByRole('button', { name: /Apagar/ })).toBeNull()

    const nova = screen.getByLabelText('Categoria nova')
    fireEvent.change(nova, { target: { value: 'Pintura' } })
    fireEvent.click(screen.getByRole('button', { name: 'Criar categoria' }))
    expect(await screen.findByText('Já existe uma categoria com esse nome.')).toBeTruthy()
    fireEvent.change(nova, { target: { value: 'Jardinagem' } })
    fireEvent.click(screen.getByRole('button', { name: 'Criar categoria' }))
    await waitFor(() =>
      expect(chamadas.filter((c) => c.metodo === 'POST').map((c) => c.corpo)).toEqual([
        { nome: 'Pintura' },
        { nome: 'Jardinagem' },
      ]),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Renomear Eletricista' }))
    const campo = screen.getByLabelText('Novo nome de Eletricista')
    fireEvent.change(campo, { target: { value: 'Eletricista e antena' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar o nome' }))
    await waitFor(() =>
      expect(chamadas.find((c) => c.metodo === 'PUT')?.corpo).toEqual({ nome: 'Eletricista e antena' }),
    )
  })

  it('a Comissão não abre a tela de categorias', async () => {
    apiIndicacoes(COMISSAO)
    abrir('/indicacoes/categorias')
    expect(await screen.findByText(/só da administração|Sem permissão|não tem permissão/i, {}, ESPERA)).toBeTruthy()
  })

  it('Comissão não vê o link de categorias no painel; admin vê', async () => {
    const PAINEL = { resumo: { total: 0, ativadas: 0, percentual: 0 }, blocos: [], unidades: [] }
    apiIndicacoes(COMISSAO, { 'GET /api/admin/unidades': json(200, PAINEL) })
    abrir('/unidades')
    await screen.findByRole('heading', { level: 1 }, ESPERA)
    await waitFor(() => expect(screen.queryByText('Carregando…')).toBeNull())
    expect(screen.queryByRole('link', { name: /Categorias das indicações/ })).toBeNull()

    cleanup()
    apiIndicacoes(ADMIN, { 'GET /api/admin/unidades': json(200, PAINEL) })
    abrir('/unidades')
    const link = await screen.findByRole('link', { name: /Categorias das indicações/ }, ESPERA)
    expect(link.getAttribute('href')).toBe('/indicacoes/categorias')
  })
})

describe('histórico', () => {
  const base: ItemHistorico = {
    id: 1,
    ocorrido_em: '2026-11-02T21:03:00Z',
    unidade: { login: '2304', bloco: 2, apartamento: '304' },
    acao: 'indicacao_escondida',
    entidade: 'prestador',
    entidade_id: 7,
    unidade_afetada: null,
    aviso_titulo: null,
    detalhes: {},
  }

  it('frases do histórico das 6 ações novas', () => {
    expect(oQueFez(base)).toBe('escondeu uma indicação')
    expect(oQueFez({ ...base, acao: 'indicacao_opiniao_escondida', detalhes: { opiniao: 3 } })).toBe(
      'escondeu uma opinião numa indicação',
    )
    expect(oQueFez({ ...base, acao: 'indicacao_opiniao_apagada' })).toBe(
      'apagou a própria opinião numa indicação',
    )
    expect(oQueFez({ ...base, acao: 'indicacao_aviso_resolvido' })).toBe('resolveu um aviso numa indicação')
    expect(
      oQueFez({ ...base, unidade: null, acao: 'indicacao_aviso_email', detalhes: { reservados: 2 } }),
    ).toBe('mandou 2 e-mails à administração sobre um aviso numa indicação')
    expect(
      oQueFez({ ...base, unidade: null, acao: 'indicacao_aviso_email', detalhes: { reservados: 1 } }),
    ).toBe('mandou e-mail à administração sobre um aviso numa indicação')
    expect(
      oQueFez({ ...base, acao: 'categoria_criada', entidade: 'categoria_servico', detalhes: { categoria: 'Jardinagem' } }),
    ).toBe('criou a categoria “Jardinagem”')
    expect(
      oQueFez({ ...base, acao: 'categoria_renomeada', entidade: 'categoria_servico', detalhes: { categoria: 'Gesso' } }),
    ).toBe('renomeou uma categoria para “Gesso”')
  })
})
