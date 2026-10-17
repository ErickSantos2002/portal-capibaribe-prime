// M5 · letra que cresce (spec m5-letra, seção 3.4): o ícone ao lado do texto cresce com a letra.
// O `tamanho` continua em px de desenho (24 = o tamanho com a letra de fábrica) e vira rem.
import { cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { Icone } from './Icone'

afterEach(cleanup)

describe('ícone', () => {
  // Revisões do M5 (R3): os atributos ficam em número (o WebKit antigo não lê rem num atributo
  // de SVG e desenhava o ícone com 300 × 150); o tamanho em rem vem do CSS (`.icone`), pela
  // variável `--icone`, que perde para qualquer regra de CSS mais específica.
  it('mede em rem: 24 vira 1.5rem, com o atributo em número', () => {
    const { container } = render(<Icone nome="avisos" />)
    const svg = container.querySelector('svg')!
    expect(svg.getAttribute('width')).toBe('24')
    expect(svg.getAttribute('height')).toBe('24')
    expect(svg.classList.contains('icone')).toBe(true)
    expect(svg.style.getPropertyValue('--icone')).toBe('1.5rem')
  })

  it('o tamanho pedido também: 18 vira 1.125rem', () => {
    const { container } = render(<Icone nome="busca" tamanho={18} />)
    const svg = container.querySelector('svg')!
    expect(svg.getAttribute('width')).toBe('18')
    expect(svg.style.getPropertyValue('--icone')).toBe('1.125rem')
  })
})
