// A barra Título · Negrito · Lista · Destaque do formulário: insere a marca no texto.
import { describe, expect, it } from 'vitest'
import { aplicarMarca, continuarLista } from './marcas'

/** `|` marca o cursor; `[` e `]` marcam a seleção. */
function com(modelo: string) {
  const inicio = modelo.search(/[|[]/)
  const semInicio = modelo.replace(/[|[]/, '')
  const fimMarcado = semInicio.indexOf(']')
  const fim = fimMarcado === -1 ? inicio : fimMarcado
  return { texto: semInicio.replace(']', ''), inicio, fim }
}

function aplicar(modelo: string, marca: Parameters<typeof aplicarMarca>[3]) {
  const { texto, inicio, fim } = com(modelo)
  const r = aplicarMarca(texto, inicio, fim, marca)
  return r.inicio === r.fim
    ? r.texto.slice(0, r.inicio) + '|' + r.texto.slice(r.inicio)
    : r.texto.slice(0, r.inicio) + '[' + r.texto.slice(r.inicio, r.fim) + ']' + r.texto.slice(r.fim)
}

describe('Enter dentro de lista (revisão UX 3)', () => {
  function enter(modelo: string) {
    const { texto, inicio } = com(modelo)
    const r = continuarLista(texto, inicio)
    return r && r.texto.slice(0, r.inicio) + '|' + r.texto.slice(r.inicio)
  }

  it('continua a lista, a numerada (com o próximo número) e o destaque', () => {
    expect(enter('- Luvas|')).toBe('- Luvas\n- |')
    expect(enter('1. Eleição|\nFim')).toBe('1. Eleição\n2. |\nFim')
    expect(enter('> Atenção|')).toBe('> Atenção\n> |')
  })

  it('Enter num item vazio encerra a lista', () => {
    expect(enter('- Luvas\n- |')).toBe('- Luvas\n|')
  })

  it('revisão de código 7: depois do 999 não continua (1000. já não é marca)', () => {
    expect(enter('999. x|')).toBeNull()
  })

  it('fora de lista, ou no meio do item, o Enter é o normal', () => {
    expect(enter('Texto|')).toBeNull()
    expect(enter('## Título|')).toBeNull()
    expect(enter('- Lu|vas')).toBeNull()
  })
})

describe('negrito', () => {
  it('põe ** em volta da seleção e mantém a palavra selecionada', () => {
    expect(aplicar('Não se [perde] mais', 'negrito')).toBe('Não se **[perde]** mais')
  })

  it('sem seleção, insere um exemplo selecionado para a pessoa digitar por cima', () => {
    expect(aplicar('Texto |', 'negrito')).toBe('Texto **[negrito]**')
  })

  it('espaço nas pontas da seleção fica fora das marcas', () => {
    expect(aplicar('a[ palavra ]b', 'negrito')).toBe('a **[palavra]** b')
  })

  it('revisão de código 4: seleção de várias linhas ganha negrito em cada linha', () => {
    expect(aplicar('[a\nb]', 'negrito')).toBe('[**a**\n**b**]')
    expect(aplicar('[a\n\nb]', 'negrito')).toBe('[**a**\n\n**b**]')
  })

  it('de novo na mesma seleção, tira o negrito', () => {
    expect(aplicar('a **[b]** c', 'negrito')).toBe('a [b] c')
  })
})

describe('marcas de linha', () => {
  it('título: põe "## " no começo da linha do cursor', () => {
    expect(aplicar('Intro\nComo en|trar\nFim', 'titulo')).toBe('Intro\n## Como entrar|\nFim')
  })

  it('lista: cada linha da seleção vira item; linha em branco fica como está', () => {
    expect(aplicar('[Documento\n\nSapato]', 'lista')).toBe('[- Documento\n\n- Sapato]')
  })

  it('destaque: põe "> " na linha', () => {
    expect(aplicar('|Vagas limitadas.', 'destaque')).toBe('> Vagas limitadas.|')
  })

  it('aplicar de novo tira a marca (liga e desliga)', () => {
    expect(aplicar('## Como |entrar', 'titulo')).toBe('Como entrar|')
    expect(aplicar('[- a\n- b]', 'lista')).toBe('[a\nb]')
  })

  it('troca uma marca de linha por outra, sem empilhar', () => {
    expect(aplicar('- Item|', 'destaque')).toBe('> Item|')
    expect(aplicar('1. Passo|', 'titulo')).toBe('## Passo|')
  })

  it('linha vazia ganha a marca e o cursor fica depois dela', () => {
    expect(aplicar('Texto\n|', 'lista')).toBe('Texto\n- |')
  })

  it('seleção que termina no começo da linha seguinte não marca essa linha', () => {
    expect(aplicar('[a\n]b', 'lista')).toBe('[- a]\nb')
  })
})
