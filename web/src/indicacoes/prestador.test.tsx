// Indicações · o prestador aberto (spec, seção 3.2): contatos, a minha opinião, o que os
// vizinhos disseram, avisar a gestão e corrigir os dados.
import { cleanup, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { abrir, eu, json } from '../acesso/apoioDeTeste'
import { apiIndicacoes, prestador } from './apoioDeTeste'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

const MORADOR = eu()
const ESPERA = { timeout: 4000 }

async function aberto() {
  return screen.findByRole('heading', { level: 2, name: 'Marcenaria Exemplo' }, ESPERA)
}

describe('prestador aberto', () => {
  it('mostra o WhatsApp com o link wa.me e o Ligar só quando o número é fixo', async () => {
    apiIndicacoes(MORADOR, { 'GET /api/indicacoes/7': json(200, prestador({ instagram: 'marcenaria.x' })) })
    abrir('/indicacoes/7')
    await aberto()
    const whats = screen.getByRole('link', { name: /WhatsApp: \(81\) 9 9999-0001/ })
    expect(whats.getAttribute('href')).toBe('https://wa.me/5581999990001')
    expect(whats.getAttribute('target')).toBe('_blank')
    expect(whats.getAttribute('rel')).toBe('noopener noreferrer')
    expect(screen.queryByRole('link', { name: /Ligar/ })).toBeNull()
    expect(screen.getByRole('link', { name: /@marcenaria\.x/ }).getAttribute('href')).toBe(
      'https://www.instagram.com/marcenaria.x/',
    )
    expect(screen.getByText('Móveis planejados')).toBeTruthy()
    expect(screen.getByText(/2 vizinhos recomendam/)).toBeTruthy()
    expect(screen.getByText('1 não recomenda')).toBeTruthy()

    cleanup()
    apiIndicacoes(MORADOR, {
      'GET /api/indicacoes/7': json(200, prestador({ telefone: '8133334444', celular: false })),
    })
    abrir('/indicacoes/7')
    await aberto()
    expect(screen.getByRole('link', { name: /WhatsApp: \(81\) 3333-4444/ })).toBeTruthy()
    expect(screen.getByRole('link', { name: /Ligar/ }).getAttribute('href')).toBe('tel:+558133334444')
  })

  it('sem opinião: "Dar a minha opinião"; com opinião: "Mudar a minha opinião" com o que ela escreveu', async () => {
    apiIndicacoes(MORADOR, { 'GET /api/indicacoes/7': json(200, prestador()) })
    abrir('/indicacoes/7')
    await aberto()
    expect(screen.getByRole('button', { name: 'Dar a minha opinião' })).toBeTruthy()

    cleanup()
    apiIndicacoes(MORADOR, {
      'GET /api/indicacoes/7': json(
        200,
        prestador({ minha_opiniao: { recomenda: false, comentario: 'Atrasou.', escondida: false } }),
      ),
    })
    abrir('/indicacoes/7')
    await aberto()
    fireEvent.click(screen.getByRole('button', { name: 'Mudar a minha opinião' }))
    const naoRecomendo = screen.getByRole('radio', { name: /Não recomendo/ }) as HTMLInputElement
    expect(naoRecomendo.checked).toBe(true)
    expect((screen.getByLabelText(/Conte como foi/) as HTMLTextAreaElement).value).toBe('Atrasou.')
    expect(screen.getByRole('button', { name: 'Apagar a minha opinião' })).toBeTruthy()
  })

  it('o formulário não envia sem escolher recomendo ou não recomendo', async () => {
    const chamadas = apiIndicacoes(MORADOR, { 'GET /api/indicacoes/7': json(200, prestador()) })
    abrir('/indicacoes/7')
    await aberto()
    fireEvent.click(screen.getByRole('button', { name: 'Dar a minha opinião' }))
    const recomendo = screen.getByRole('radio', { name: /^👍 Recomendo|Recomendo$/ }) as HTMLInputElement
    expect(recomendo.checked).toBe(false)
    fireEvent.click(screen.getByRole('button', { name: 'Salvar a minha opinião' }))
    // Revisão: o erro de baixo não aparecia para quem tocou em Salvar. A caixa do topo diz e
    // leva o foco, e o grupo fica marcado como inválido.
    const alerta = await screen.findByRole('alert')
    expect(alerta.textContent).toBe('Escolha se você recomenda ou não.')
    expect(document.activeElement).toBe(alerta)
    expect(screen.getByRole('group', { name: 'Você recomenda?' }).getAttribute('aria-invalid')).toBe('true')
    expect(chamadas.some((c) => c.metodo === 'PUT')).toBe(false)
    // Escolheu: o erro some (do campo e do topo).
    fireEvent.click(recomendo)
    expect(screen.queryByRole('alert')).toBeNull()
    expect(screen.queryByText('Escolha se você recomenda ou não.')).toBeNull()
    expect(screen.getByRole('group', { name: 'Você recomenda?' }).getAttribute('aria-invalid')).toBeNull()
  })

  it('salvar chama PUT /api/indicacoes/7/opiniao com {recomenda, comentario} e atualiza a contagem', async () => {
    const chamadas = apiIndicacoes(MORADOR, {
      'GET /api/indicacoes/7': json(200, prestador()),
      'PUT /api/indicacoes/7/opiniao': json(
        200,
        prestador({
          recomendam: 3,
          minha_opiniao: { recomenda: true, comentario: 'Ótimo', escondida: false },
        }),
      ),
    })
    abrir('/indicacoes/7')
    await aberto()
    fireEvent.click(screen.getByRole('button', { name: 'Dar a minha opinião' }))
    fireEvent.click(screen.getByRole('radio', { name: /Recomendo$/ }))
    fireEvent.change(screen.getByLabelText(/Conte como foi/), { target: { value: 'Ótimo' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar a minha opinião' }))
    await waitFor(() => expect(screen.getByText(/3 vizinhos recomendam/)).toBeTruthy())
    const put = chamadas.find((c) => c.metodo === 'PUT')
    expect(put?.caminho).toBe('/api/indicacoes/7/opiniao')
    expect(put?.corpo).toEqual({ recomenda: true, comentario: 'Ótimo' })
    expect(screen.getByRole('button', { name: 'Mudar a minha opinião' })).toBeTruthy()
  })

  it('o contador do comentário vai até 500', async () => {
    apiIndicacoes(MORADOR, { 'GET /api/indicacoes/7': json(200, prestador()) })
    abrir('/indicacoes/7')
    await aberto()
    fireEvent.click(screen.getByRole('button', { name: 'Dar a minha opinião' }))
    const campo = screen.getByLabelText(/Conte como foi/) as HTMLTextAreaElement
    expect(campo.maxLength).toBe(500)
    fireEvent.change(campo, { target: { value: 'abc' } })
    expect(screen.getByText('3 de 500 letras')).toBeTruthy()
  })

  it('apagar pergunta antes e chama DELETE', async () => {
    const chamadas = apiIndicacoes(MORADOR, {
      'GET /api/indicacoes/7': json(
        200,
        prestador({ minha_opiniao: { recomenda: true, comentario: null, escondida: false } }),
      ),
      'DELETE /api/indicacoes/7/opiniao': json(204),
    })
    abrir('/indicacoes/7')
    await aberto()
    fireEvent.click(screen.getByRole('button', { name: 'Mudar a minha opinião' }))
    fireEvent.click(screen.getByRole('button', { name: 'Apagar a minha opinião' }))
    expect(chamadas.some((c) => c.metodo === 'DELETE')).toBe(false)
    const pergunta = screen.getByRole('group', { name: /Apagar a sua opinião\?/ })
    fireEvent.click(within(pergunta).getByRole('button', { name: 'Apagar de vez' }))
    await waitFor(() => expect(chamadas.some((c) => c.metodo === 'DELETE')).toBe(true))
    expect(chamadas.find((c) => c.metodo === 'DELETE')?.caminho).toBe('/api/indicacoes/7/opiniao')
  })

  it('?opinar=1 abre o formulário direto', async () => {
    apiIndicacoes(MORADOR, { 'GET /api/indicacoes/7': json(200, prestador()) })
    abrir('/indicacoes/7?opinar=1')
    await aberto()
    expect(await screen.findByRole('radio', { name: /Não recomendo/ })).toBeTruthy()
  })

  it('a opinião escondida: o recado, sem botão de opinião, nem com ?opinar=1', async () => {
    apiIndicacoes(MORADOR, {
      'GET /api/indicacoes/7': json(
        200,
        prestador({ minha_opiniao: { recomenda: true, comentario: 'X', escondida: true } }),
      ),
    })
    abrir('/indicacoes/7?opinar=1')
    await aberto()
    expect(screen.getByText(/A gestão escondeu a sua opinião/)).toBeTruthy()
    expect(screen.queryByRole('button', { name: /minha opinião/ })).toBeNull()
    expect(screen.queryByRole('radio')).toBeNull()
  })

  it('avisar a gestão manda o motivo e troca o link por "Você já avisou a gestão"', async () => {
    const chamadas = apiIndicacoes(MORADOR, {
      'GET /api/indicacoes/7': json(200, prestador()),
      'POST /api/indicacoes/7/aviso': json(204),
    })
    abrir('/indicacoes/7')
    await aberto()
    fireEvent.click(screen.getByRole('button', { name: 'Tem algo errado aqui? Avisar a gestão' }))
    const motivo = screen.getByLabelText(/O que está errado/) as HTMLTextAreaElement
    expect(motivo.maxLength).toBe(300)
    fireEvent.change(motivo, { target: { value: 'O número não atende.' } })
    fireEvent.click(screen.getByRole('button', { name: 'Avisar a gestão' }))
    expect(await screen.findByText('Você já avisou a gestão.')).toBeTruthy()
    const post = chamadas.find((c) => c.metodo === 'POST')
    expect(post?.caminho).toBe('/api/indicacoes/7/aviso')
    expect(post?.corpo).toEqual({ motivo: 'O número não atende.' })
    expect(screen.queryByRole('button', { name: 'Tem algo errado aqui? Avisar a gestão' })).toBeNull()
  })

  it('com ja_avisei, só o texto', async () => {
    apiIndicacoes(MORADOR, { 'GET /api/indicacoes/7': json(200, prestador({ ja_avisei: true })) })
    abrir('/indicacoes/7')
    await aberto()
    expect(screen.getByText('Você já avisou a gestão.')).toBeTruthy()
  })

  it('quem indicou vê "Corrigir"; outro morador não', async () => {
    apiIndicacoes(MORADOR, { 'GET /api/indicacoes/7': json(200, prestador()) })
    abrir('/indicacoes/7')
    await aberto()
    expect(screen.queryByRole('button', { name: /Corrigir/ })).toBeNull()

    cleanup()
    const chamadas = apiIndicacoes(MORADOR, {
      'GET /api/indicacoes/7': json(200, prestador({ pode_corrigir: true })),
      'PUT /api/indicacoes/7': json(200, prestador({ pode_corrigir: true, nome: 'Marcenaria Exemplo' })),
    })
    abrir('/indicacoes/7')
    await aberto()
    fireEvent.click(screen.getByRole('button', { name: /Corrigir os dados/ }))
    const nome = screen.getByLabelText('Nome do prestador ou da empresa') as HTMLInputElement
    expect(nome.value).toBe('Marcenaria Exemplo')
    expect((screen.getByLabelText('WhatsApp ou telefone') as HTMLInputElement).value).toBe(
      '(81) 9 9999-0001',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Salvar as correções' }))
    await waitFor(() => expect(chamadas.some((c) => c.metodo === 'PUT')).toBe(true))
    expect(chamadas.find((c) => c.metodo === 'PUT')?.corpo).toEqual({
      categoria_id: 1,
      nome: 'Marcenaria Exemplo',
      telefone: '(81) 9 9999-0001',
      instagram: null,
    })
  })

  it('corrigir para o telefone de outro mostra o erro com o link para ele', async () => {
    apiIndicacoes(MORADOR, {
      'GET /api/indicacoes/7': json(200, prestador({ pode_corrigir: true })),
      'PUT /api/indicacoes/7': json(409, {
        codigo: 'prestador_ja_existe',
        mensagem: 'Esse telefone já está na lista. Dê a sua opinião lá.',
        id: 3,
      }),
    })
    abrir('/indicacoes/7')
    await aberto()
    fireEvent.click(screen.getByRole('button', { name: /Corrigir os dados/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Salvar as correções' }))
    const link = await screen.findByRole('link', { name: /Abrir o prestador que já tem esse telefone/ })
    expect(link.getAttribute('href')).toBe('/indicacoes/3')
  })

  it('as opiniões mostram a placa e nunca nome de pessoa', async () => {
    apiIndicacoes(MORADOR, { 'GET /api/indicacoes/7': json(200, prestador()) })
    abrir('/indicacoes/7')
    await aberto()
    const secao = screen.getByRole('region', { name: 'O que os vizinhos disseram' })
    const itens = within(secao).getAllByRole('listitem')
    expect(itens).toHaveLength(2)
    expect(within(itens[0]).getByRole('img', { name: 'Bloco 1, apartamento 101' })).toBeTruthy()
    expect(itens[0].textContent).toContain('Recomenda')
    expect(itens[0].textContent).toContain('Fez a cozinha no prazo.')
    expect(itens[1].textContent).toContain('Não recomenda')
    expect(secao.textContent).not.toMatch(/Responsável|fictício/i)
  })

  it('indicação que não existe: a mensagem da API e o caminho de volta', async () => {
    apiIndicacoes(MORADOR, {
      'GET /api/indicacoes/7': json(404, {
        codigo: 'indicacao_nao_encontrada',
        mensagem: 'Indicação não encontrada.',
      }),
    })
    abrir('/indicacoes/7')
    expect(await screen.findByText('Indicação não encontrada.', {}, ESPERA)).toBeTruthy()
  })
})

describe('prestador aberto · revisão', () => {
  it('abrir o formulário leva o foco ao título; Cancelar devolve ao botão', async () => {
    apiIndicacoes(MORADOR, { 'GET /api/indicacoes/7': json(200, prestador()) })
    abrir('/indicacoes/7')
    await aberto()
    fireEvent.click(screen.getByRole('button', { name: 'Dar a minha opinião' }))
    expect(document.activeElement).toBe(screen.getByRole('heading', { level: 3, name: 'Dar a minha opinião' }))
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    await waitFor(() =>
      expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Dar a minha opinião' })),
    )
  })

  it('"Manter a minha opinião" devolve o foco ao "Apagar a minha opinião"', async () => {
    apiIndicacoes(MORADOR, {
      'GET /api/indicacoes/7': json(
        200,
        prestador({ minha_opiniao: { recomenda: true, comentario: null, escondida: false } }),
      ),
    })
    abrir('/indicacoes/7')
    await aberto()
    fireEvent.click(screen.getByRole('button', { name: 'Mudar a minha opinião' }))
    fireEvent.click(screen.getByRole('button', { name: 'Apagar a minha opinião' }))
    fireEvent.click(screen.getByRole('button', { name: 'Manter a minha opinião' }))
    await waitFor(() =>
      expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Apagar a minha opinião' })),
    )
  })

  it('Cancelar o aviso à gestão devolve o foco ao link que abriu', async () => {
    apiIndicacoes(MORADOR, { 'GET /api/indicacoes/7': json(200, prestador()) })
    abrir('/indicacoes/7')
    await aberto()
    fireEvent.click(screen.getByRole('button', { name: 'Tem algo errado aqui? Avisar a gestão' }))
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    await waitFor(() =>
      expect(document.activeElement).toBe(
        screen.getByRole('button', { name: 'Tem algo errado aqui? Avisar a gestão' }),
      ),
    )
  })

  it('número fixo: "Ligar" é o botão principal e o WhatsApp fica leve; o número não quebra', async () => {
    apiIndicacoes(MORADOR, {
      'GET /api/indicacoes/7': json(200, prestador({ telefone: '8133334444', celular: false })),
    })
    abrir('/indicacoes/7')
    await aberto()
    const ligar = screen.getByRole('link', { name: 'Ligar: (81) 3333-4444' })
    const whats = screen.getByRole('link', { name: 'WhatsApp: (81) 3333-4444' })
    expect(ligar.className).toBe('botao ind-ligar')
    expect(whats.classList.contains('leve')).toBe(true)
    // O Ligar vem primeiro.
    expect(ligar.compareDocumentPosition(whats) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect([...ligar.querySelectorAll('.ind-numero')].map((n) => n.textContent)).toEqual([
      '(81)',
      '3333-4444',
    ])
  })

  it('celular: o WhatsApp é o principal, sem Ligar', async () => {
    apiIndicacoes(MORADOR, { 'GET /api/indicacoes/7': json(200, prestador()) })
    abrir('/indicacoes/7')
    await aberto()
    const whats = screen.getByRole('link', { name: 'WhatsApp: (81) 9 9999-0001' })
    expect(whats.classList.contains('leve')).toBe(false)
    expect(screen.queryByRole('link', { name: /Ligar/ })).toBeNull()
  })

  it('zero recomendações: sem a linha verde; sem opinião nenhuma, o texto neutro', async () => {
    apiIndicacoes(MORADOR, {
      'GET /api/indicacoes/7': json(200, prestador({ recomendam: 0, nao_recomendam: 1 })),
    })
    abrir('/indicacoes/7')
    await aberto()
    const contagens = document.querySelector('.ind-contagens')!
    expect(contagens.querySelector('.ind-recomendam')).toBeNull()
    expect(contagens.textContent).toBe('👎 1 não recomenda')

    cleanup()
    apiIndicacoes(MORADOR, {
      'GET /api/indicacoes/7': json(200, prestador({ recomendam: 0, nao_recomendam: 0, opinioes: [] })),
    })
    abrir('/indicacoes/7')
    await aberto()
    expect(document.querySelector('.ind-contagens')?.textContent).toBe('Nenhum vizinho recomenda ainda')
    expect(document.querySelector('.ind-contagens .ind-recomendam')).toBeNull()
  })

  it('corrigir: mexer no campo com erro tira o erro dele', async () => {
    apiIndicacoes(MORADOR, { 'GET /api/indicacoes/7': json(200, prestador({ pode_corrigir: true })) })
    abrir('/indicacoes/7')
    await aberto()
    fireEvent.click(screen.getByRole('button', { name: /Corrigir os dados/ }))
    const nome = screen.getByLabelText('Nome do prestador ou da empresa')
    fireEvent.change(nome, { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar as correções' }))
    expect(await screen.findByText('Escreva o nome do prestador ou da empresa.')).toBeTruthy()
    fireEvent.change(nome, { target: { value: 'Marcenaria Nova' } })
    expect(screen.queryByText('Escreva o nome do prestador ou da empresa.')).toBeNull()
    expect(nome.getAttribute('aria-invalid')).toBeNull()
  })

  it('a própria opinião tem o selo "Sua opinião"', async () => {
    const base = prestador()
    apiIndicacoes(MORADOR, {
      'GET /api/indicacoes/7': json(
        200,
        prestador({ opinioes: [{ ...base.opinioes[0], minha: true }, base.opinioes[1]] }),
      ),
    })
    abrir('/indicacoes/7')
    await aberto()
    const itens = within(screen.getByRole('region', { name: 'O que os vizinhos disseram' })).getAllByRole(
      'listitem',
    )
    expect(itens[0].querySelector('.selo.ind-sua')?.textContent).toBe('Sua opinião')
    expect(itens[0].textContent).not.toContain('· a sua')
    expect(itens[1].querySelector('.ind-sua')).toBeNull()
  })
})
