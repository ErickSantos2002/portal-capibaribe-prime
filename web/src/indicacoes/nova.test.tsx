// Indicações · indicar alguém (spec, seção 3.3): os campos, o aviso de nome parecido, o 409 do
// telefone repetido e "Sair sem publicar?".
import { cleanup, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { abrir, eu, json } from '../acesso/apoioDeTeste'
import { apiIndicacoes, prestador } from './apoioDeTeste'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

const MORADOR = eu()
const ESPERA = { timeout: 4000 }

async function formulario() {
  await screen.findByRole('heading', { level: 1, name: 'Indicar alguém' }, ESPERA)
  // As categorias chegaram.
  await screen.findByRole('option', { name: 'Eletricista' }, ESPERA)
}

function preencher({ recomenda = true } = {}) {
  fireEvent.change(screen.getByLabelText('Que serviço?'), { target: { value: '5' } })
  fireEvent.change(screen.getByLabelText('Nome do prestador ou da empresa'), {
    target: { value: 'Fios & Cia' },
  })
  fireEvent.change(screen.getByLabelText('WhatsApp ou telefone'), {
    target: { value: '(81) 9 9999-0001' },
  })
  fireEvent.change(screen.getByLabelText('Instagram (opcional)'), { target: { value: '@fios' } })
  fireEvent.click(screen.getByRole('radio', { name: recomenda ? /Recomendo$/ : /Não recomendo/ }))
  fireEvent.change(screen.getByLabelText(/Conte como foi/), { target: { value: 'Rápido.' } })
}

describe('indicar alguém', () => {
  it('os campos na ordem do spec, sem recomendo marcado', async () => {
    apiIndicacoes(MORADOR)
    abrir('/indicacoes/nova')
    await formulario()
    const rotulos = [...document.querySelectorAll('form label, form legend')].map((r) =>
      r.textContent?.trim(),
    )
    expect(rotulos).toEqual([
      'Que serviço?',
      'Nome do prestador ou da empresa',
      'WhatsApp ou telefone',
      'Instagram (opcional)',
      'Você recomenda?',
      '👍 Recomendo',
      '👎 Não recomendo',
      'Conte como foi (opcional)',
    ])
    expect(screen.getAllByRole('radio').every((r) => !(r as HTMLInputElement).checked)).toBe(true)
  })

  it('digitar "Marcen" mostra "Já tem uma Marcenaria Silva na lista" com o link para /indicacoes/3?opinar=1', async () => {
    const chamadas = apiIndicacoes(MORADOR, {
      'GET /api/indicacoes/parecidos?nome=Marcen': json(200, {
        itens: [{ id: 3, nome: 'Marcenaria Silva', categoria: { id: 1, nome: 'Móveis planejados' } }],
      }),
    })
    abrir('/indicacoes/nova')
    await formulario()
    fireEvent.change(screen.getByLabelText('Nome do prestador ou da empresa'), {
      target: { value: 'Marcen' },
    })
    const aviso = await screen.findByText(/Já tem uma/, {}, ESPERA)
    expect(aviso.closest('div')?.textContent).toContain('Já tem uma Marcenaria Silva na lista. É a mesma?')
    const link = screen.getByRole('link', { name: 'Dar minha opinião lá' })
    expect(link.getAttribute('href')).toBe('/indicacoes/3?opinar=1')
    expect(chamadas.filter((c) => c.caminho.startsWith('/api/indicacoes/parecidos'))).toHaveLength(1)
  })

  it('menos de 3 letras não procura parecidos', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    try {
      const chamadas = apiIndicacoes(MORADOR)
      abrir('/indicacoes/nova')
      await formulario()
      fireEvent.change(screen.getByLabelText('Nome do prestador ou da empresa'), {
        target: { value: 'Ma' },
      })
      await vi.advanceTimersByTimeAsync(1000)
      expect(chamadas.some((c) => c.caminho.startsWith('/api/indicacoes/parecidos'))).toBe(false)
    } finally {
      vi.useRealTimers()
    }
  })

  it('não publica sem categoria, nome, telefone e recomendo/não recomendo; erros nos campos', async () => {
    const chamadas = apiIndicacoes(MORADOR)
    abrir('/indicacoes/nova')
    await formulario()
    fireEvent.click(screen.getByRole('button', { name: 'Publicar indicação' }))
    expect(await screen.findByText('Escolha o serviço.')).toBeTruthy()
    expect(screen.getByText('Escreva o nome do prestador ou da empresa.')).toBeTruthy()
    expect(screen.getByText('Escreva o WhatsApp ou o telefone, com DDD.')).toBeTruthy()
    expect(screen.getByText('Escolha se você recomenda ou não.')).toBeTruthy()
    expect(chamadas.some((c) => c.metodo === 'POST')).toBe(false)
    expect(screen.getByLabelText('Nome do prestador ou da empresa').getAttribute('aria-invalid')).toBe(
      'true',
    )
  })

  it('publicar manda POST /api/indicacoes com os campos e vai para o prestador criado', async () => {
    const chamadas = apiIndicacoes(MORADOR, {
      'POST /api/indicacoes': json(201, { id: 7 }),
      'GET /api/indicacoes/7': json(200, prestador()),
    })
    abrir('/indicacoes/nova')
    await formulario()
    preencher()
    fireEvent.click(screen.getByRole('button', { name: 'Publicar indicação' }))
    await screen.findByRole('heading', { level: 2, name: 'Marcenaria Exemplo' }, ESPERA)
    expect(chamadas.find((c) => c.metodo === 'POST')?.corpo).toEqual({
      categoria_id: 5,
      nome: 'Fios & Cia',
      telefone: '(81) 9 9999-0001',
      instagram: '@fios',
      recomenda: true,
      comentario: 'Rápido.',
    })
    // Publicou: nada de "Sair sem publicar?".
    expect(screen.queryByRole('alertdialog')).toBeNull()
  })

  it('409 prestador_ja_existe leva ao prestador com o formulário de opinião aberto', async () => {
    apiIndicacoes(MORADOR, {
      'POST /api/indicacoes': json(409, {
        codigo: 'prestador_ja_existe',
        mensagem: 'Esse telefone já está na lista. Dê a sua opinião lá.',
        id: 3,
      }),
      'GET /api/indicacoes/3': json(200, prestador({ id: 3 })),
    })
    abrir('/indicacoes/nova')
    await formulario()
    preencher()
    fireEvent.click(screen.getByRole('button', { name: 'Publicar indicação' }))
    await screen.findByRole('heading', { level: 2, name: 'Marcenaria Exemplo' }, ESPERA)
    expect(screen.getByRole('radio', { name: /Não recomendo/ })).toBeTruthy()
    expect(screen.queryByRole('alertdialog')).toBeNull()
    await waitFor(() =>
      expect(screen.getByRole('status').textContent).toBe(
        'Esse telefone já está na lista. Dê a sua opinião aqui.',
      ),
    )
  })

  it('409 prestador_indisponivel mostra a mensagem e nenhum link', async () => {
    apiIndicacoes(MORADOR, {
      'POST /api/indicacoes': json(409, {
        codigo: 'prestador_indisponivel',
        mensagem: 'Esse prestador não está disponível no Portal.',
      }),
    })
    abrir('/indicacoes/nova')
    await formulario()
    preencher()
    fireEvent.click(screen.getByRole('button', { name: 'Publicar indicação' }))
    const erro = await screen.findByText('Esse prestador não está disponível no Portal.')
    expect(erro.closest('[role="alert"]')?.querySelector('a')).toBeNull()
  })

  it('sair com algo escrito pergunta "Sair sem publicar?"', async () => {
    apiIndicacoes(MORADOR, { 'GET /api/indicacoes': json(200, { itens: [], com_aviso: null }) })
    abrir('/indicacoes/nova')
    await formulario()
    fireEvent.change(screen.getByLabelText('Nome do prestador ou da empresa'), {
      target: { value: 'Fu' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Voltar' }))
    const pergunta = await screen.findByRole('alertdialog', { name: 'Sair sem publicar?' })
    fireEvent.click(screen.getByRole('button', { name: 'Continuar escrevendo' }))
    expect(screen.queryByRole('alertdialog')).toBeNull()
    expect(pergunta).toBeTruthy()
    expect((screen.getByLabelText('Nome do prestador ou da empresa') as HTMLInputElement).value).toBe('Fu')
  })

  // Foco 4: a unidade cuja opinião foi escondida tenta indicar de novo e cai no 409.
  it('após o 409, a unidade com opinião escondida vê "A gestão escondeu a sua opinião" e não o formulário', async () => {
    apiIndicacoes(MORADOR, {
      'POST /api/indicacoes': json(409, {
        codigo: 'prestador_ja_existe',
        mensagem: 'Esse telefone já está na lista. Dê a sua opinião lá.',
        id: 3,
      }),
      'GET /api/indicacoes/3': json(
        200,
        prestador({ id: 3, minha_opiniao: { recomenda: true, comentario: 'X', escondida: true } }),
      ),
    })
    abrir('/indicacoes/nova')
    await formulario()
    preencher()
    fireEvent.click(screen.getByRole('button', { name: 'Publicar indicação' }))
    expect(await screen.findByText(/A gestão escondeu a sua opinião/, {}, ESPERA)).toBeTruthy()
    expect(screen.queryByRole('radio')).toBeNull()
    expect(screen.queryByRole('button', { name: /minha opinião/ })).toBeNull()
  })
})
