/** Medida de desenho em px (com a letra de fábrica, 16 px) para rem: o ícone e o que mais for
 *  medido no código crescem com a letra escolhida no aparelho (M5, spec m5-letra, seção 3.4). */
export const emRem = (px: number) => `${px / 16}rem`
