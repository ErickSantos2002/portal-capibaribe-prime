// Épico A do M4 · as contas do formulário de enquete, sem tela.
import { describe, expect, it } from 'vitest'
import {
  conferir,
  deIso,
  opcoesLimpas,
  paraIso,
  RASCUNHO_VAZIO,
  textoDoAviso,
  tituloDoAviso,
  type Rascunho,
} from './formatos'

const AGORA = new Date('2026-10-14T12:00:00-03:00')

function rascunho(troca: Partial<Rascunho> = {}): Rascunho {
  return {
    ...RASCUNHO_VAZIO,
    pergunta: 'Qual o melhor dia para a reunião?',
    opcoes: ['Terça à noite', 'Quinta à noite'],
    dia: '2026-10-24',
    hora: '20:00',
    ...troca,
  }
}

describe('término no horário de Recife', () => {
  it('dia e hora viram data com o fuso de Recife', () => {
    expect(paraIso('2026-10-24', '20:00')).toBe('2026-10-24T20:00:00-03:00')
  })

  it('e voltam, de qualquer fuso', () => {
    expect(deIso('2026-10-24T23:05:00Z')).toEqual({ dia: '2026-10-24', hora: '20:05' })
    expect(deIso('2026-10-25T01:30:00Z')).toEqual({ dia: '2026-10-24', hora: '22:30' })
  })
})

describe('o aviso automático (a mesma frase da API)', () => {
  it('título com o começo de sempre, cortado em 120 letras', () => {
    expect(tituloDoAviso('Qual dia?')).toBe('Enquete nova: Qual dia?')
    const longo = tituloDoAviso('Vocês ' + 'x'.repeat(190) + '?')
    expect(longo).toHaveLength(120)
    expect(longo.endsWith('…')).toBe(true)
  })

  it('texto com as opções, o prazo, a escolha, o resultado e a frase da consulta', () => {
    expect(textoDoAviso(rascunho({ opcoes: ['Terça à noite', ' ', 'Quinta à noite'] }), AGORA)).toBe(
      'Uma enquete nova está aberta no Portal: “Qual o melhor dia para a reunião?”.\n\n' +
        'As opções são:\n\n- Terça à noite\n- Quinta à noite\n\n' +
        'Dá para votar até 24 de outubro, às 20h (horário de Recife). Marque uma opção. Vale um' +
        ' voto por apartamento, e dá para trocar o voto até o fim. O resultado aparece durante' +
        ' a votação.\n\n' +
        '> Enquete é consulta. Não tem valor legal de votação em assembleia.\n\n' +
        'O botão “Ir para a enquete”, neste aviso, leva direto a ela.',
    )
  })

  it('múltipla escolha, só no fim e hora da manhã', () => {
    const texto = textoDoAviso(
      rascunho({ multipla: true, mostrar: 'so_no_fim', hora: '08:05' }),
      AGORA,
    )
    expect(texto).toContain('às 8h05 (horário de Recife). Pode marcar mais de uma opção.')
    expect(texto).toContain('O resultado só aparece quando a enquete terminar.')
  })
})

describe('conferir antes de enviar (as frases da API)', () => {
  it('tudo certo', () => {
    expect(conferir(rascunho(), AGORA)).toEqual({})
  })

  it('opções em branco não contam', () => {
    expect(opcoesLimpas([' Sim ', '', 'Não', '  '])).toEqual(['Sim', 'Não'])
  })

  const casos: [Partial<Rascunho>, string, string][] = [
    [{ pergunta: '   ' }, 'pergunta', 'Escreva a pergunta.'],
    [{ opcoes: ['Sim', ' '] }, 'opcoes', 'Escreva pelo menos 2 opções de resposta.'],
    [{ opcoes: ['Sábado de manhã', 'sábado  de MANHÃ'] }, 'opcoes', 'Duas opções estão iguais.'],
    [{ dia: '' }, 'termino', 'Escolha o dia do término.'],
    [{ hora: '' }, 'termino', 'Escolha a hora do término.'],
    [
      { dia: '2026-10-14', hora: '11:00' },
      'termino',
      'A data de término já passou. Escolha uma data no futuro.',
    ],
    [{ dia: '2026-10-14', hora: '12:30' }, 'termino', 'Escolha um término daqui a pelo menos 1 hora.'],
    [{ dia: '2027-10-15' }, 'termino', 'A enquete pode durar até 1 ano.'],
  ]
  it.each(casos)('%o → %s', (troca, campo, mensagem) => {
    expect(conferir(rascunho(troca), AGORA)).toEqual({ [campo]: mensagem })
  })

  it('opção comprida demais', () => {
    expect(conferir(rascunho({ opcoes: ['Sim', 'x'.repeat(101)] }), AGORA)).toEqual({
      opcoes: 'Cada opção pode ter até 100 letras.',
    })
  })
})

// --- revisão independente do épico A ------------------------------------------------------------

describe('revisão: Unicode como a API', () => {
  it('ponto 6: "é" e "e + acento" são a mesma opção', () => {
    expect(conferir(rascunho({ opcoes: ['Café', 'Café'] }), AGORA)).toEqual({
      opcoes: 'Duas opções estão iguais.',
    })
    expect(opcoesLimpas(['Café ', 'Chá'])).toEqual(['Café', 'Chá'])
  })

  it('ponto 6: opção ou pergunta sem letra nem número', () => {
    expect(conferir(rascunho({ opcoes: ['Sim', '́́'] }), AGORA)).toEqual({
      opcoes: 'Cada opção precisa ter letras ou números.',
    })
    expect(conferir(rascunho({ opcoes: ['Sim', '?!'] }), AGORA)).toEqual({
      opcoes: 'Cada opção precisa ter letras ou números.',
    })
    expect(conferir(rascunho({ pergunta: '́?' }), AGORA)).toEqual({
      pergunta: 'Escreva a pergunta com letras ou números.',
    })
  })

  it('ponto 7: o título corta por letra, sem partir o emoji', () => {
    const titulo = tituloDoAviso('x'.repeat(104) + '🎉🎉🎉 resto da pergunta')
    expect(Array.from(titulo)).toHaveLength(120)
    expect(/[\uD800-\uDBFF](?![\uDC00-\uDFFF])/.test(titulo)).toBe(false)
    expect(titulo.endsWith('🎉…')).toBe(true)
  })

  it('ponto 7: a pergunta conta emoji como uma letra, até 200', () => {
    expect(conferir(rascunho({ pergunta: 'Qual ' + '🎉'.repeat(195) }), AGORA)).toEqual({})
    expect(conferir(rascunho({ pergunta: 'Qual? ' + '🎉'.repeat(195) }), AGORA)).toEqual({
      pergunta: 'A pergunta pode ter até 200 letras.',
    })
  })

  it('ponto 8: "Straße" e "STRASSE" são a mesma opção, como no casefold', () => {
    expect(conferir(rascunho({ opcoes: ['Straße', 'STRASSE'] }), AGORA)).toEqual({
      opcoes: 'Duas opções estão iguais.',
    })
  })
})

describe('revisão, ponto 4: na edição, o término igual não pede 1 hora', () => {
  const perto = { dia: '2026-10-14', hora: '12:30' }

  it('término igual ao gravado passa, mesmo a 30 minutos do fim', () => {
    expect(conferir(rascunho(perto), AGORA, perto)).toEqual({})
  })

  it('término mudado continua pedindo 1 hora', () => {
    expect(conferir(rascunho({ ...perto, hora: '12:40' }), AGORA, perto)).toEqual({
      termino: 'Escolha um término daqui a pelo menos 1 hora.',
    })
  })
})
