// Tipos comuns do contrato da API (docs/superpowers/specs/m1-contrato.md, seções 3.4 e 4.1).
// Espelho de api/app/esquemas/comum.py: o teste api/testes/test_contrato.py confere os campos.
// Datas chegam como texto ISO 8601 (UTC); a tela mostra no horário de Recife.

export type Papel = 'admin' | 'comissao' | 'sindico' | 'conselho'

/** Data e hora em ISO 8601, como a API manda. */
export type DataHora = string

export interface UnidadeRef {
  login: string
  bloco: number
  apartamento: string
}

export interface Eu {
  unidade: UnidadeRef
  papeis: Papel[]
  gestao: boolean
  admin: boolean
  precisa_trocar_senha: boolean
}

export interface CampoInvalido {
  campo: string | null
  mensagem: string
}

export interface ErroResposta {
  codigo: string
  mensagem: string
  campos?: CampoInvalido[] | null
}
