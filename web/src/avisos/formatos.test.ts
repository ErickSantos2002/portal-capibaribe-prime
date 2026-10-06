import { describe, expect, it } from 'vitest'
import {
  assinatura,
  blocosEmTexto,
  destinoEmTexto,
  listaParaCopiar,
  paragrafos,
  partesDaLinha,
} from './formatos'

describe('assinatura (H-12: "Publicado pela Comissão")', () => {
  it.each([
    ['Comissão', 'pela Comissão'],
    ['Administração do Portal', 'pela Administração do Portal'],
    ['Síndico', 'pelo Síndico'],
    ['Conselho', 'pelo Conselho'],
  ])('%s → %s', (quem, esperado) => {
    expect(assinatura(quem)).toBe(esperado)
  })
})

describe('destino', () => {
  it('para todos', () => {
    expect(destinoEmTexto({ para_todos: true, blocos: [] })).toBe('todos os blocos')
  })
  it('um bloco', () => {
    expect(destinoEmTexto({ para_todos: false, blocos: [4] })).toBe('o Bloco 4')
    expect(blocosEmTexto([4])).toBe('Bloco 4')
  })
  it('vários blocos', () => {
    expect(destinoEmTexto({ para_todos: false, blocos: [1, 2] })).toBe('os Blocos 1 e 2')
    expect(blocosEmTexto([1, 3, 5])).toBe('Blocos 1, 3 e 5')
  })
})

describe('texto puro', () => {
  it('parágrafo é linha em branco; quebra simples continua dentro do parágrafo', () => {
    expect(paragrafos('Linha 1\nLinha 2\n\nParte 2\n  \nParte 3')).toEqual([
      'Linha 1\nLinha 2',
      'Parte 2',
      'Parte 3',
    ])
  })

  it('acha endereços http e https e deixa a pontuação do fim de fora', () => {
    expect(partesDaLinha('Veja https://exemplo.com.br/a?b=1. E http://x.org/')).toEqual([
      { texto: 'Veja ' },
      { texto: 'https://exemplo.com.br/a?b=1', link: 'https://exemplo.com.br/a?b=1' },
      { texto: '. E ' },
      { texto: 'http://x.org/', link: 'http://x.org/' },
    ])
  })

  it('não vira link o que não é http ou https', () => {
    expect(partesDaLinha('javascript:alert(1) e www.exemplo.com')).toEqual([
      { texto: 'javascript:alert(1) e www.exemplo.com' },
    ])
  })

  it('link entre parênteses não leva o parêntese', () => {
    expect(partesDaLinha('(https://exemplo.com)')).toEqual([
      { texto: '(' },
      { texto: 'https://exemplo.com', link: 'https://exemplo.com' },
      { texto: ')' },
    ])
  })
})

describe('lista de quem não leu, para colar no grupo', () => {
  it('agrupa por bloco', () => {
    const texto = listaParaCopiar(
      'Vistoria',
      [{ login: '3001', bloco: 3, apartamento: '001' }],
      [
        { login: '1101', bloco: 1, apartamento: '101' },
        { login: '1102', bloco: 1, apartamento: '102' },
      ],
    )
    expect(texto).toBe(
      'Ainda não leram o aviso “Vistoria”:\n\n' +
        'Entraram no Portal, mas não leram:\nBloco 1: 101, 102\n\n' +
        'Ainda não entraram no Portal:\nBloco 3: 001',
    )
  })
})
