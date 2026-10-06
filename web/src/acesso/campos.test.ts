// Regras de campo do épico A (H-01: bloco em botões + apartamento só números).
import { describe, expect, it } from 'vitest'
import { limparApartamento, montarLogin, validarContato, validarSenhaNova } from './campos'

describe('montarLogin', () => {
  it('Bloco 1 + 101 vira 1101', () => expect(montarLogin('1', '101')).toBe('1101'))
  it('Bloco 1 + 7 vira 1007', () => expect(montarLogin('1', '7')).toBe('1007'))
  it('Bloco 1 + 07 vira 1007', () => expect(montarLogin('1', '07')).toBe('1007'))
  it('sem bloco ou sem apartamento não monta', () => {
    expect(montarLogin('', '101')).toBeNull()
    expect(montarLogin('1', '')).toBeNull()
  })
})

describe('limparApartamento', () => {
  it('letra e traço nem aparecem', () => {
    expect(limparApartamento('1-0a1', false)).toEqual({ apartamento: '101', bloco: null })
  })
  it('no máximo 3 dígitos', () => {
    expect(limparApartamento('10123', false)).toEqual({ apartamento: '101', bloco: null })
  })
  it('limpa antes de cortar: "Apto 502" colado vira 502', () => {
    expect(limparApartamento('Apto 502', true)).toEqual({ apartamento: '502', bloco: null })
  })
  it('o login antigo colado (1203) marca o bloco e deixa o apartamento', () => {
    expect(limparApartamento('1203', true)).toEqual({ apartamento: '203', bloco: '1' })
  })
  it('digitando, o 4º dígito só é ignorado', () => {
    expect(limparApartamento('1203', false)).toEqual({ apartamento: '120', bloco: null })
  })
})

describe('validarSenhaNova', () => {
  it('menos de 8', () =>
    expect(validarSenhaNova('curta', 'curta')).toEqual({
      campo: 'senha_nova',
      mensagem: 'A senha nova precisa ter pelo menos 8 caracteres.',
    }))
  it('mudar123', () =>
    expect(validarSenhaNova('mudar123', 'mudar123')?.mensagem).toBe(
      'Escolha uma senha diferente da inicial, que todo mundo conhece.',
    ))
  it('diferentes', () =>
    expect(validarSenhaNova('senha-boa-1', 'senha-boa-2')).toEqual({
      campo: 'senha_nova_repetida',
      mensagem: 'As duas senhas estão diferentes. Escreva a mesma nas duas.',
    }))
  it('boa', () => expect(validarSenhaNova('senha-boa-1', 'senha-boa-1')).toBeNull())
})

describe('validarContato', () => {
  const bom = { responsavel_nome: 'Ana', celular: '(81) 9 1234-5678', email: '' }
  it('nome em branco', () =>
    expect(validarContato({ ...bom, responsavel_nome: '  ' })?.mensagem).toBe(
      'Escreva o nome de quem responde pela unidade.',
    ))
  it('celular sem DDD', () =>
    expect(validarContato({ ...bom, celular: '91234-5678' })?.campo).toBe('celular'))
  it('e-mail sem arroba', () =>
    expect(validarContato({ ...bom, email: 'ana' })?.mensagem).toBe(
      'Confira o e-mail, ou deixe em branco.',
    ))
  it('e-mail vazio pode', () => expect(validarContato(bom)).toBeNull())
})
