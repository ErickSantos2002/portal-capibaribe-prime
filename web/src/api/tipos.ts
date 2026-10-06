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

// --- M2: como foi a notificação de um aviso (docs/superpowers/specs/m2-contrato.md, 4.4) ---

export type Canal = 'push' | 'email'

export type SituacaoEnvio = 'pendente' | 'enviando' | 'concluido' | 'desligado' | 'interrompido'

/** Só contagens: `destinos` são aparelhos (push) ou apartamentos (e-mail). */
export interface EnvioDoAviso {
  canal: Canal
  situacao: SituacaoEnvio
  destinos: number
  entregues: number
  falhas: number
  removidas: number
  pulados: number
  criado_em: DataHora
  concluido_em: DataHora | null
}

/** `GET /api/avisos/{id}/envios` (gestão). */
export interface EnviosDoAviso {
  itens: EnvioDoAviso[]
}
