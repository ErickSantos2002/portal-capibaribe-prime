// Classificados · o anúncio aberto (spec, seção 3.2): as fotos e o visor, o WhatsApp com a
// mensagem pronta, o fluxo do dono (reservar, renovar, encerrar), avisar a gestão e a seção da
// gestão.
import { cleanup, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { abrir, esperarRecado, eu, json } from '../acesso/apoioDeTeste'
import { anuncio, apiClassificados } from './apoioDeTeste'
import { mensagemDoWhatsApp } from './formatos'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

const MORADOR = eu()
const DONO = eu([], false, '2304')
const ADMIN = eu(['admin'], false, '1101')

describe('anúncio aberto', () => {
  it('mostra o tipo, o preço, a categoria, a descrição, a placa e as fotos', async () => {
    apiClassificados(MORADOR, { 'GET /api/classificados/7': json(200, anuncio()) })
    abrir('/classificados/7')
    expect(await screen.findByRole('heading', { level: 2, name: 'Sofá de 3 lugares' })).toBeTruthy()
    expect(screen.getByText('Vende R$ 350')).toBeTruthy()
    expect(screen.getByText('Móveis')).toBeTruthy()
    expect(screen.getByText(/Sofá cinza, sem manchas/)).toBeTruthy()
    expect(screen.getByRole('img', { name: 'Bloco 2, apartamento 304' })).toBeTruthy()
    expect(screen.getByRole('img', { name: 'Foto 1 de 2: Sofá de 3 lugares' })).toBeTruthy()
    expect(screen.getByRole('img', { name: 'Foto 2 de 2: Sofá de 3 lugares' })).toBeTruthy()
  })

  it('o WhatsApp leva a mensagem pronta com o título', async () => {
    apiClassificados(MORADOR, { 'GET /api/classificados/7': json(200, anuncio()) })
    abrir('/classificados/7')
    const whatsapp = await screen.findByRole('link', { name: /Chamar no WhatsApp/ })
    const href = whatsapp.getAttribute('href') ?? ''
    expect(href.startsWith('https://wa.me/5581999990001?text=')).toBe(true)
    expect(decodeURIComponent(href.split('?text=')[1])).toBe(mensagemDoWhatsApp('Sofá de 3 lugares'))
    expect(whatsapp.getAttribute('target')).toBe('_blank')
    expect(screen.queryByRole('link', { name: /Ligar/ })).toBeNull()
  })

  it('fixo ganha "Ligar" como botão principal', async () => {
    apiClassificados(MORADOR, {
      'GET /api/classificados/7': json(200, anuncio({ contato: '8133334444', celular: false })),
    })
    abrir('/classificados/7')
    const ligar = await screen.findByRole('link', { name: /Ligar/ })
    expect(ligar.getAttribute('href')).toBe('tel:+558133334444')
  })

  it('tocar na foto abre o visor, com próxima, anterior, Esc e o foco de volta', async () => {
    apiClassificados(MORADOR, { 'GET /api/classificados/7': json(200, anuncio()) })
    abrir('/classificados/7')
    const grande = (await screen.findByRole('img', { name: /Foto 1 de 2/ })).closest('button')!
    fireEvent.click(grande)
    const visor = screen.getByRole('dialog', { name: 'Foto 1 de 2' })
    // O visor comum dos anexos (revisão UX 1): no body, com o resto inerte e sem rolar por trás.
    expect(visor.parentElement).toBe(document.body)
    expect(visor.className).toContain('anexo-visualizador')
    const fundo = [...document.body.children].filter((e) => e !== visor && e.tagName === 'DIV')
    expect(fundo.length).toBeGreaterThan(0)
    expect(fundo.every((e) => e.hasAttribute('inert'))).toBe(true)
    expect(document.body.style.overflow).toBe('hidden')
    expect(document.activeElement).toBe(within(visor).getByRole('button', { name: /Fechar/ }))
    fireEvent.click(within(visor).getByRole('button', { name: 'Próxima foto' }))
    expect(screen.getByRole('dialog', { name: 'Foto 2 de 2' })).toBeTruthy()
    fireEvent.keyDown(document, { key: 'ArrowRight' })
    expect(screen.getByRole('dialog', { name: 'Foto 1 de 2' })).toBeTruthy()
    // O Esc vale em qualquer lugar (no document), não só com o foco na janela.
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(fundo.some((e) => e.hasAttribute('inert'))).toBe(false)
    expect(document.body.style.overflow).toBe('')
    await waitFor(() => expect(document.activeElement).toBe(grande))
  })

  it('o morador avisa a gestão com o motivo e o link vira "Você já avisou a gestão."', async () => {
    const chamadas = apiClassificados(MORADOR, {
      'GET /api/classificados/7': json(200, anuncio()),
      'POST /api/classificados/7/aviso': json(204),
    })
    abrir('/classificados/7')
    fireEvent.click(await screen.findByRole('button', { name: /Tem algo errado aqui/ }))
    expect(screen.getByText(/vão olhar este anúncio/)).toBeTruthy()
    fireEvent.change(screen.getByLabelText(/O que está errado/), { target: { value: 'Parece golpe' } })
    fireEvent.click(screen.getByRole('button', { name: 'Avisar a gestão' }))
    await esperarRecado('A gestão foi avisada. Obrigado!')
    expect(chamadas.find((c) => c.caminho === '/api/classificados/7/aviso')?.corpo).toEqual({
      motivo: 'Parece golpe',
    })
    expect(screen.getByText(/Você já avisou a gestão/)).toBeTruthy()
  })

  it('o dono não vê o WhatsApp nem o aviso; vê o contato e as ações', async () => {
    apiClassificados(DONO, { 'GET /api/classificados/7': json(200, anuncio({ meu: true })) })
    abrir('/classificados/7')
    expect(await screen.findByText(/Os vizinhos chamam você no/)).toBeTruthy()
    expect(screen.queryByRole('link', { name: /Chamar no WhatsApp/ })).toBeNull()
    expect(screen.queryByRole('button', { name: /Tem algo errado/ })).toBeNull()
    expect(screen.getByRole('link', { name: /Editar/ }).getAttribute('href')).toBe('/classificados/7/editar')
    expect(screen.getByRole('button', { name: 'Marcar como reservado' })).toBeTruthy()
    // Longe de vencer: sem "Renovar".
    expect(screen.queryByRole('button', { name: /Renovar/ })).toBeNull()
  })

  it('o dono reserva e tira a reserva', async () => {
    const chamadas = apiClassificados(DONO, {
      'GET /api/classificados/7': json(200, anuncio({ meu: true })),
      'POST /api/classificados/7/reservar': json(200, anuncio({ meu: true, situacao: 'reservado' })),
      'POST /api/classificados/7/liberar': json(200, anuncio({ meu: true })),
    })
    abrir('/classificados/7')
    fireEvent.click(await screen.findByRole('button', { name: 'Marcar como reservado' }))
    await esperarRecado('Anúncio marcado como reservado.')
    expect(screen.getByText('Reservado')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Tirar a reserva' }))
    await esperarRecado('A reserva foi tirada.')
    expect(chamadas.map((c) => c.caminho)).toContain('/api/classificados/7/liberar')
  })

  it('vencido: o dono vê o recado e só renova ou encerra', async () => {
    const vencido = anuncio({ meu: true, vencido: true, pode_renovar: true })
    const chamadas = apiClassificados(DONO, {
      'GET /api/classificados/7': json(200, vencido),
      'POST /api/classificados/7/renovar': json(200, anuncio({ meu: true })),
    })
    abrir('/classificados/7')
    expect(await screen.findByText(/O seu anúncio venceu em .* e saiu da lista/)).toBeTruthy()
    expect(screen.queryByRole('link', { name: /Editar/ })).toBeNull()
    expect(screen.queryByRole('button', { name: /reservado/ })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: /Renovar por mais 30 dias/ }))
    await esperarRecado('Anúncio renovado por mais 30 dias.')
    expect(chamadas.map((c) => c.caminho)).toContain('/api/classificados/7/renovar')
  })

  it('encerrar pede o motivo e manda {motivo}', async () => {
    const chamadas = apiClassificados(DONO, {
      'GET /api/classificados/7': json(200, anuncio({ meu: true })),
      'POST /api/classificados/7/encerrar': json(
        200,
        anuncio({ meu: true, situacao: 'encerrado', motivo_encerramento: 'doei' }),
      ),
    })
    abrir('/classificados/7')
    fireEvent.click(await screen.findByRole('button', { name: 'Encerrar' }))
    const caixa = screen.getByRole('group', { name: /Encerrar o anúncio/ })
    expect(within(caixa).getAllByRole('radio')).toHaveLength(4)
    fireEvent.click(within(caixa).getByRole('button', { name: 'Encerrar anúncio' }))
    expect(within(caixa).getByRole('alert').textContent).toBe('Escolha o que aconteceu.')
    fireEvent.click(within(caixa).getByLabelText('Doei'))
    fireEvent.click(within(caixa).getByRole('button', { name: 'Encerrar anúncio' }))
    await esperarRecado('Anúncio encerrado.')
    expect(chamadas.find((c) => c.caminho === '/api/classificados/7/encerrar')?.corpo).toEqual({
      motivo: 'doei',
    })
    expect(screen.getByText(/Você encerrou este anúncio \(doado\)/)).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Encerrar' })).toBeNull()
  })

  it('escondido: o dono vê o recado da gestão e só pode encerrar', async () => {
    apiClassificados(DONO, {
      'GET /api/classificados/7': json(200, anuncio({ meu: true, escondido: true })),
    })
    abrir('/classificados/7')
    expect(await screen.findByText(/A gestão escondeu o seu anúncio/)).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Encerrar' })).toBeTruthy()
    expect(screen.queryByRole('link', { name: /Editar/ })).toBeNull()
    expect(screen.queryByRole('button', { name: /reservado/ })).toBeNull()
  })

  it('o anúncio que não está mais disponível mostra a frase da API', async () => {
    apiClassificados(MORADOR, {
      'GET /api/classificados/7': json(404, {
        codigo: 'anuncio_indisponivel',
        mensagem: 'Este anúncio não está mais disponível.',
      }),
    })
    abrir('/classificados/7')
    expect(await screen.findByText('Este anúncio não está mais disponível.')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Ver outros anúncios' })).toBeTruthy()
  })
})

describe('revisão de UX', () => {
  it('5: a gestão no próprio anúncio vê a visão do dono, sem "Para a gestão"', async () => {
    apiClassificados(ADMIN, {
      'GET /api/classificados/7': json(200, anuncio({ meu: true, avisos: [] })),
    })
    abrir('/classificados/7')
    expect(await screen.findByRole('heading', { name: 'O seu anúncio' })).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Para a gestão' })).toBeNull()
    expect(screen.queryByRole('button', { name: /Esconder este anúncio/ })).toBeNull()
  })

  it('5: o escondido fala com o dono em 2ª pessoa', async () => {
    apiClassificados(DONO, {
      'GET /api/classificados/7': json(200, anuncio({ meu: true, escondido: true })),
    })
    abrir('/classificados/7')
    expect(await screen.findByText(/e você só pode encerrá-lo/)).toBeTruthy()
  })

  it('6: indisponível é estado neutro, sem "Tentar de novo", com "Ver outros anúncios"', async () => {
    apiClassificados(MORADOR, {
      'GET /api/classificados/7': json(404, {
        codigo: 'anuncio_indisponivel',
        mensagem: 'Este anúncio não está mais disponível.',
      }),
    })
    abrir('/classificados/7')
    const frase = await screen.findByText('Este anúncio não está mais disponível.')
    expect(frase.closest('.aviso-caixa')?.classList.contains('erro')).toBe(false)
    expect(screen.queryByRole('button', { name: /Tentar de novo/ })).toBeNull()
    expect(screen.getByRole('link', { name: 'Ver outros anúncios' }).getAttribute('href')).toBe(
      '/classificados',
    )
  })

  it('6: erro de rede continua com "Tentar de novo"', async () => {
    apiClassificados(MORADOR, {
      'GET /api/classificados/7': json(500, { codigo: 'erro_interno', mensagem: 'Algo deu errado.' }),
    })
    abrir('/classificados/7')
    expect(await screen.findByRole('button', { name: /Tentar de novo/ })).toBeTruthy()
  })

  it('7: depois de reservar, o foco fica no botão que ficou no lugar; depois de encerrar, no título', async () => {
    apiClassificados(DONO, {
      'GET /api/classificados/7': json(200, anuncio({ meu: true })),
      'POST /api/classificados/7/reservar': json(200, anuncio({ meu: true, situacao: 'reservado' })),
      'POST /api/classificados/7/encerrar': json(
        200,
        anuncio({ meu: true, situacao: 'encerrado', motivo_encerramento: 'vendi' }),
      ),
    })
    abrir('/classificados/7')
    fireEvent.click(await screen.findByRole('button', { name: 'Marcar como reservado' }))
    await waitFor(() =>
      expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Tirar a reserva' })),
    )
    fireEvent.click(screen.getByRole('button', { name: 'Encerrar' }))
    fireEvent.click(screen.getByLabelText('Vendi'))
    fireEvent.click(screen.getByRole('button', { name: 'Encerrar anúncio' }))
    await waitFor(() =>
      expect(document.activeElement).toBe(screen.getByRole('heading', { level: 2, name: 'Sofá de 3 lugares' })),
    )
  })

  it('9: o reservado diz ao visitante que ainda dá para chamar, e a mensagem muda', async () => {
    apiClassificados(MORADOR, {
      'GET /api/classificados/7': json(200, anuncio({ situacao: 'reservado' })),
    })
    abrir('/classificados/7')
    expect(
      await screen.findByText('Reservado: alguém já combinou com o dono. Você ainda pode chamar.'),
    ).toBeTruthy()
    const href = screen.getByRole('link', { name: /Chamar no WhatsApp/ }).getAttribute('href') ?? ''
    expect(decodeURIComponent(href.split('?text=')[1])).toBe(mensagemDoWhatsApp('Sofá de 3 lugares', true))
  })

  it('16: "Encerrar" não usa o ícone de certo', async () => {
    apiClassificados(DONO, { 'GET /api/classificados/7': json(200, anuncio({ meu: true })) })
    abrir('/classificados/7')
    const botao = await screen.findByRole('button', { name: 'Encerrar' })
    expect(botao.innerHTML).not.toContain('M5 12.5l4.5 4.5L19 7')
  })
})

describe('para a gestão', () => {
  it('o morador não vê a seção; a gestão vê os avisos, resolve e esconde', async () => {
    apiClassificados(MORADOR, { 'GET /api/classificados/7': json(200, anuncio()) })
    abrir('/classificados/7')
    await screen.findByRole('heading', { level: 2, name: 'Sofá de 3 lugares' })
    expect(screen.queryByRole('heading', { name: 'Para a gestão' })).toBeNull()
    cleanup()

    const comAvisos = anuncio({ avisos: [{ id: 5, motivo: 'Parece golpe', em: '2026-10-19T12:00:00Z' }] })
    const chamadas = apiClassificados(ADMIN, {
      'GET /api/classificados/7': json(200, comAvisos),
      'POST /api/classificados/avisos/5/resolver': json(204),
      'POST /api/classificados/7/esconder': json(204),
    })
    abrir('/classificados/7')
    const secao = (await screen.findByRole('heading', { name: 'Para a gestão' })).closest('section')!
    expect(within(secao).getByText('Parece golpe')).toBeTruthy()
    fireEvent.click(within(secao).getByRole('button', { name: 'Resolver' }))
    await esperarRecado('Aviso resolvido.')
    fireEvent.click(within(secao).getByRole('button', { name: /Esconder este anúncio/ }))
    fireEvent.click(within(secao).getByRole('button', { name: 'Esconder de vez' }))
    await esperarRecado('Anúncio escondido da lista.')
    await waitFor(() =>
      expect(chamadas.map((c) => c.caminho)).toEqual(
        expect.arrayContaining([
          '/api/classificados/avisos/5/resolver',
          '/api/classificados/7/esconder',
        ]),
      ),
    )
  })
})
