// O renderizador do Markdown restrito (spec dos avisos com formatação, seções 3.1 e 5).
import { describe, expect, it } from 'vitest'
import { analisar, trechos } from './formatacao'

describe('analisar: cada marca', () => {
  it('texto sem marca: parágrafos por linha em branco, linhas dentro do parágrafo', () => {
    expect(analisar('Linha 1\nLinha 2\n\n  \nParte 2')).toEqual([
      { tipo: 'paragrafo', linhas: ['Linha 1', 'Linha 2'] },
      { tipo: 'paragrafo', linhas: ['Parte 2'] },
    ])
  })

  it('"## " vira título de seção', () => {
    expect(analisar('## Como entrar\nCada apartamento tem uma conta.')).toEqual([
      { tipo: 'titulo', texto: 'Como entrar' },
      { tipo: 'paragrafo', linhas: ['Cada apartamento tem uma conta.'] },
    ])
  })

  it('linhas seguidas com "- " viram uma lista', () => {
    expect(analisar('Leve:\n- Documento\n- Sapato fechado\nAté lá.')).toEqual([
      { tipo: 'paragrafo', linhas: ['Leve:'] },
      { tipo: 'lista', itens: ['Documento', 'Sapato fechado'] },
      { tipo: 'paragrafo', linhas: ['Até lá.'] },
    ])
  })

  it('linhas seguidas com "1. ", "2. " viram lista numerada, começando do primeiro número', () => {
    expect(analisar('1. Entrar\n2. Trocar a senha')).toEqual([
      { tipo: 'numerada', inicio: 1, itens: ['Entrar', 'Trocar a senha'] },
    ])
    expect(analisar('3. Terceiro\n4. Quarto')).toEqual([
      { tipo: 'numerada', inicio: 3, itens: ['Terceiro', 'Quarto'] },
    ])
  })

  it('linhas seguidas com "> " viram uma caixa de destaque', () => {
    expect(analisar('> Vagas limitadas.\n> Confirme até quinta.\n\nFim.')).toEqual([
      { tipo: 'destaque', linhas: ['Vagas limitadas.', 'Confirme até quinta.'] },
      { tipo: 'paragrafo', linhas: ['Fim.'] },
    ])
  })

  it('linha em branco separa duas listas', () => {
    expect(analisar('- a\n\n- b')).toEqual([
      { tipo: 'lista', itens: ['a'] },
      { tipo: 'lista', itens: ['b'] },
    ])
  })

  it('\\r\\n e \\r contam como quebra de linha', () => {
    expect(analisar('a\r\nb\r\rc')).toEqual([
      { tipo: 'paragrafo', linhas: ['a', 'b'] },
      { tipo: 'paragrafo', linhas: ['c'] },
    ])
  })
})

describe('analisar: marcas malformadas ficam como texto', () => {
  it.each([
    ['#Título'],
    ['# Título'],
    ['### Título'],
    ['##Título'],
    ['## '],
    ['-item'],
    ['- '],
    ['* item'],
    ['1.item'],
    ['1) item'],
    ['1234. item'],
    ['>destaque'],
    ['> '],
    ['  - recuado'],
    ['| a | b |'],
    ['```código```'],
  ])('%j', (linha) => {
    expect(analisar(linha)).toEqual([{ tipo: 'paragrafo', linhas: [linha] }])
  })
})

describe('trechos: negrito e links', () => {
  it('**trecho** vira negrito, o resto é texto', () => {
    expect(trechos('Não se **perde mais** no grupo.')).toEqual([
      { texto: 'Não se ' },
      { texto: 'perde mais', negrito: true },
      { texto: ' no grupo.' },
    ])
  })

  it('dois negritos na mesma linha', () => {
    expect(trechos('**a** e **b**')).toEqual([
      { texto: 'a', negrito: true },
      { texto: ' e ' },
      { texto: 'b', negrito: true },
    ])
  })

  it.each([['**sem fim'], ['** espaço **'], ['****'], ['*itálico*'], ['__sublinhado__']])(
    'malformado fica literal: %j',
    (linha) => {
      expect(trechos(linha)).toEqual([{ texto: linha }])
    },
  )

  it('endereço http(s) vira link, também dentro do negrito', () => {
    expect(trechos('Veja https://exemplo.com.br/a. Ou **http://b.org**')).toEqual([
      { texto: 'Veja ' },
      { texto: 'https://exemplo.com.br/a', link: 'https://exemplo.com.br/a' },
      { texto: '. Ou ' },
      { texto: 'http://b.org', link: 'http://b.org', negrito: true },
    ])
  })
})

describe('segurança: nada vira elemento nem link perigoso', () => {
  const ataques = [
    '<script>alert(1)</script>',
    '<img src=x onerror=alert(1)>',
    '<b>negrito</b>',
    'javascript:alert(1)',
    '[clique](javascript:alert(1))',
    '![img](https://exemplo.com/x.png)',
    'data:text/html;base64,PHNjcmlwdD4=',
    '<a href="javascript:alert(1)">x</a>',
  ]

  it.each(ataques)('%j continua texto literal, sem link', (ataque) => {
    const blocos = analisar(ataque)
    expect(blocos).toEqual([{ tipo: 'paragrafo', linhas: [ataque] }])
    const partes = trechos(ataque)
    expect(partes.filter((p) => p.link && !p.link.startsWith('https://'))).toEqual([])
    expect(partes.map((p) => p.texto).join('')).toBe(ataque)
  })

  it('[x](https://…) vira só o endereço como link, sem o rótulo nem o parêntese', () => {
    expect(trechos('[x](https://exemplo.com)')).toEqual([
      { texto: '[x](' },
      { texto: 'https://exemplo.com', link: 'https://exemplo.com' },
      { texto: ')' },
    ])
  })

  it('link só http(s): esquema disfarçado não vira link', () => {
    for (const linha of ['JAVASCRIPT:alert(1)', 'ftp://x.org', 'httpx://x.org', 'https://']) {
      expect(trechos(linha).some((p) => p.link)).toBe(false)
    }
  })

  it('marca dentro de título e de lista também passa pelos trechos (nada de HTML)', () => {
    expect(analisar('## <script>x</script>\n- <img onerror=y>')).toEqual([
      { tipo: 'titulo', texto: '<script>x</script>' },
      { tipo: 'lista', itens: ['<img onerror=y>'] },
    ])
  })
})
