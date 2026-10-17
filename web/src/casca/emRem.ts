import type { CSSProperties } from 'react'

/** Medida de desenho em px (com a letra de fábrica, 16 px) para rem: o ícone e o que mais for
 *  medido no código crescem com a letra escolhida no aparelho (M5, spec m5-letra, seção 3.4). */
export const emRem = (px: number) => `${px / 16}rem`

/** Tamanho de um ícone SVG (M5, revisões, R3): `width`/`height` em NÚMERO, que todo navegador lê
 *  (o WebKit antigo não aceita rem num atributo de SVG e desenhava 300 × 150), e o tamanho que
 *  cresce com a letra pelo CSS: `.icone { width: var(--icone) }` no estilo.css. O atributo de SVG
 *  perde para qualquer regra de CSS, e a `.icone` perde para as regras mais específicas dos
 *  épicos (ex.: a seta menor das listas com letra grande). */
export function tamanhoDoIcone(px: number) {
  return {
    width: px,
    height: px,
    className: 'icone',
    style: { '--icone': emRem(px) } as CSSProperties,
  }
}
