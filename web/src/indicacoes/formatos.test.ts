// Indicações · formatos da tela: telefone, links e as contagens em texto.
import { describe, expect, it } from 'vitest'
import {
  ehCelular,
  linkInstagram,
  linkTelefone,
  linkWhatsApp,
  naoRecomendamEmTexto,
  recomendamEmTexto,
  telefoneNaTela,
} from './formatos'

describe('telefone', () => {
  it('mostra com a máscara de celular e de fixo', () => {
    expect(telefoneNaTela('81999990001')).toBe('(81) 9 9999-0001')
    expect(telefoneNaTela('8133334444')).toBe('(81) 3333-4444')
  })

  it('outra coisa volta como veio', () => {
    expect(telefoneNaTela('123')).toBe('123')
  })

  it('celular é o de 11 dígitos', () => {
    expect(ehCelular('81999990001')).toBe(true)
    expect(ehCelular('8133334444')).toBe(false)
  })
})

describe('links', () => {
  it('WhatsApp, telefone e Instagram', () => {
    expect(linkWhatsApp('81999990001')).toBe('https://wa.me/5581999990001')
    expect(linkTelefone('8133334444')).toBe('tel:+558133334444')
    expect(linkInstagram('marcenaria.x')).toBe('https://www.instagram.com/marcenaria.x/')
  })
})

describe('contagens', () => {
  it('quem recomenda', () => {
    expect(recomendamEmTexto(1)).toBe('1 vizinho recomenda')
    expect(recomendamEmTexto(3)).toBe('3 vizinhos recomendam')
    expect(recomendamEmTexto(0)).toBe('Nenhum vizinho recomenda ainda')
  })

  it('quem não recomenda', () => {
    expect(naoRecomendamEmTexto(1)).toBe('1 não recomenda')
    expect(naoRecomendamEmTexto(2)).toBe('2 não recomendam')
  })
})
