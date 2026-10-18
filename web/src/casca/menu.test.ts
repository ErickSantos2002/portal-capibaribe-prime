// Lista única de lugares (spec da navegação com bola, seção 5): a barra, a folha do Menu e o menu
// lateral do computador saem da mesma lista.
import { describe, expect, it } from 'vitest'
import { eu } from '../acesso/apoioDeTeste'
import { agrupados, daBarra, lugarAtual, lugaresDo } from './menu'

const MORADOR = eu()
const COMISSAO = eu(['comissao'])
const ADMIN = eu(['admin'])
const DIA_A_DIA = ['Avisos', 'Enquetes', 'Documentos', 'Indicações', 'Minha unidade']
// A barra do celular continua com 4 (Indicações mora só na folha e no menu lateral).
const BARRA = ['Avisos', 'Enquetes', 'Documentos', 'Minha unidade']

describe('lugaresDo', () => {
  it('o morador tem os 5 do dia a dia', () => {
    expect(lugaresDo(MORADOR).map((l) => l.texto)).toEqual(DIA_A_DIA)
  })

  it('a gestão tem Unidades no fim, no grupo Gestão e fora da barra', () => {
    for (const quem of [COMISSAO, ADMIN]) {
      const lugares = lugaresDo(quem)
      expect(lugares.map((l) => l.texto)).toEqual([...DIA_A_DIA, 'Unidades'])
      const unidades = lugares.at(-1)
      expect(unidades?.grupo).toBe('gestao')
      expect(unidades?.naBarra).toBeUndefined()
    }
  })

  it('todo lugar tem frase, e Documentos tem o rótulo curto "Docs"', () => {
    for (const lugar of lugaresDo(ADMIN)) expect(lugar.frase.trim()).not.toBe('')
    expect(lugaresDo(MORADOR).find((l) => l.texto === 'Documentos')?.curto).toBe('Docs')
  })

  it('Indicações fica fora da barra, com a frase', () => {
    const indicacoes = lugaresDo(MORADOR).find((l) => l.texto === 'Indicações')
    expect(indicacoes).toMatchObject({
      para: '/indicacoes',
      icone: 'indicacoes',
      frase: 'Serviços que os vizinhos recomendam',
      grupo: 'dia-a-dia',
    })
    expect(indicacoes?.naBarra).toBeUndefined()
  })

  it('nenhum lugar repete a posição da barra', () => {
    const posicoes = lugaresDo(ADMIN)
      .map((l) => l.naBarra)
      .filter((p) => p !== undefined)
    expect(new Set(posicoes).size).toBe(posicoes.length)
  })
})

describe('daBarra', () => {
  it('as 4 posições, iguais para todo papel', () => {
    for (const quem of [MORADOR, COMISSAO, ADMIN]) {
      expect(daBarra(lugaresDo(quem)).map((l) => l?.texto)).toEqual(BARRA)
    }
  })

  it('sem um lugar da barra, a vaga fica vazia e ninguém sobe', () => {
    const semEnquetes = lugaresDo(MORADOR).filter((l) => l.texto !== 'Enquetes')
    expect(daBarra(semEnquetes).map((l) => l?.texto ?? null)).toEqual([
      'Avisos',
      null,
      'Documentos',
      'Minha unidade',
    ])
  })
})

describe('agrupados', () => {
  it('o admin vê Dia a dia e Gestão', () => {
    const grupos = agrupados(lugaresDo(ADMIN))
    expect(grupos.map((g) => g.nome)).toEqual(['Dia a dia', 'Gestão'])
    expect(grupos[0].lugares.map((l) => l.texto)).toEqual(DIA_A_DIA)
    expect(grupos[1].lugares.map((l) => l.texto)).toEqual(['Unidades'])
  })

  it('o morador não tem o grupo Gestão (grupo vazio some)', () => {
    expect(agrupados(lugaresDo(MORADOR)).map((g) => g.nome)).toEqual(['Dia a dia'])
  })
})

describe('lugarAtual', () => {
  const lugares = lugaresDo(ADMIN)
  it('pega o lugar pelo começo do endereço', () => {
    expect(lugarAtual(lugares, '/unidades/1101')?.texto).toBe('Unidades')
    expect(lugarAtual(lugares, '/avisos/12')?.texto).toBe('Avisos')
    expect(lugarAtual(lugares, '/avisos')?.texto).toBe('Avisos')
  })

  it('fora da lista, nenhum', () => {
    expect(lugarAtual(lugares, '/historico')).toBeUndefined()
    expect(lugarAtual(lugares, '/avisosx')).toBeUndefined()
  })
})
