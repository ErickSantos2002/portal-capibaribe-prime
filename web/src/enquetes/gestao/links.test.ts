// Revisão do épico A do M4, ponto 5: aspas curvas e "»" fecham a frase, não entram no link
// (o mesmo que `_FIM_DE_FRASE` da API; o aviso da enquete põe a pergunta entre “aspas”).
import { describe, expect, it } from 'vitest'
import { partesDaLinha } from '../../avisos/formatos'

describe('link no fim da frase', () => {
  it.each(['”', '’', '»'])('"%s" fica fora do link', (fecha) => {
    const links = partesDaLinha(`Viram “https://exemplo.com/planta${fecha}.`).flatMap((p) =>
      p.link ? [p.link] : [],
    )
    expect(links).toEqual(['https://exemplo.com/planta'])
  })
})
