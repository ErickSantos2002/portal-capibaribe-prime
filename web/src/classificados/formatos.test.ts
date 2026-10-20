// Classificados · formatos da tela: selo do tipo, preço, "há quanto tempo", WhatsApp.
import { describe, expect, it } from 'vitest'
import {
  centavosDoTexto,
  haQuanto,
  linkWhatsAppDoAnuncio,
  mensagemDoWhatsApp,
  precoEmReais,
  precoNoCampo,
  seloDoTipo,
  textoDoMotivo,
} from './formatos'

describe('selo do tipo', () => {
  it('venda com preço, a combinar, troca e doação', () => {
    expect(seloDoTipo('venda', 35000)).toBe('Vende R$ 350')
    expect(seloDoTipo('venda', 125050)).toBe('Vende R$ 1.250,50')
    expect(seloDoTipo('venda', null)).toBe('Vende · a combinar')
    expect(seloDoTipo('venda', 0)).toBe('Vende R$ 0')
    expect(seloDoTipo('troca', null)).toBe('Troca')
    expect(seloDoTipo('doacao', null)).toBe('Doa')
  })
})

describe('preço', () => {
  it('em reais, sem centavos quando é redondo', () => {
    expect(precoEmReais(10000000)).toBe('R$ 100.000')
    expect(precoEmReais(99)).toBe('R$ 0,99')
  })

  it('do campo para centavos, com vírgula, ponto de milhar e R$', () => {
    expect(centavosDoTexto('350')).toBe(35000)
    expect(centavosDoTexto('R$ 1.250,50')).toBe(125050)
    expect(centavosDoTexto('1250.5')).toBe(125050)
    expect(centavosDoTexto('0')).toBe(0)
    expect(centavosDoTexto('')).toBeNull()
    expect(centavosDoTexto('   ')).toBeNull()
    expect(centavosDoTexto('abc')).toBeNaN()
    expect(centavosDoTexto('12,345')).toBeNaN()
  })

  it('de centavos para o campo (editar)', () => {
    expect(precoNoCampo(35000)).toBe('350')
    expect(precoNoCampo(125050)).toBe('1250,50')
    expect(precoNoCampo(null)).toBe('')
  })
})

describe('há quanto tempo', () => {
  const agora = new Date('2026-10-20T15:00:00-03:00')
  it('hoje, ontem e dias', () => {
    expect(haQuanto('2026-10-20T08:00:00-03:00', agora)).toBe('hoje')
    expect(haQuanto('2026-10-19T23:00:00-03:00', agora)).toBe('ontem')
    expect(haQuanto('2026-10-17T10:00:00-03:00', agora)).toBe('há 3 dias')
    expect(haQuanto('2026-09-20T10:00:00-03:00', agora)).toBe('há 30 dias')
  })
})

describe('WhatsApp', () => {
  it('a mensagem pronta com o título, codificada no link', () => {
    expect(mensagemDoWhatsApp('Sofá de 3 lugares')).toBe(
      'Oi! Vi seu anúncio "Sofá de 3 lugares" no Portal Capibaribe Prime. Ainda está disponível?',
    )
    const link = linkWhatsAppDoAnuncio('81999990001', 'Sofá & cia')
    expect(link.startsWith('https://wa.me/5581999990001?text=')).toBe(true)
    expect(decodeURIComponent(link.split('?text=')[1])).toBe(mensagemDoWhatsApp('Sofá & cia'))
    expect(link).not.toContain('&cia')
  })
})

it('o motivo do encerramento na voz do morador', () => {
  expect(textoDoMotivo('vendi')).toBe('Vendido')
  expect(textoDoMotivo('troquei')).toBe('Trocado')
  expect(textoDoMotivo('doei')).toBe('Doado')
  expect(textoDoMotivo('desisti')).toBe('Desistiu')
})
