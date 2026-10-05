// Épico A · Acesso: tipos do contrato (spec do M1, seção 4.2). Pertence ao épico A.
// Espelho de api/app/esquemas/acesso.py: o teste api/testes/test_contrato.py confere os campos.
import type { DataHora, ErroResposta, Papel, UnidadeRef } from '../api/tipos'

export interface Entrar {
  login: string
  senha: string
}

export interface Contato {
  responsavel_nome: string
  celular: string
  email?: string | null
}

export interface PrimeiroAcesso extends Contato {
  senha_nova: string
  senha_nova_repetida: string
}

export type DadosDaUnidade = Contato

export interface TrocarSenha {
  senha_atual: string
  senha_nova: string
  senha_nova_repetida: string
}

export interface ApagarDados {
  confirmo: true
}

export interface Aparelho {
  id: number
  descricao: string
  criada_em: DataHora
  ultimo_uso_em: DataHora
  este_aparelho: boolean
}

export interface MinhaUnidade {
  unidade: UnidadeRef
  responsavel_nome: string | null
  celular: string | null
  email: string | null
  papeis: Papel[]
  ativada_em: DataHora | null
  aparelhos: Aparelho[]
}

/** 423 `unidade_bloqueada` de POST /api/acesso/entrar (H-03). */
export interface ErroBloqueio extends ErroResposta {
  bloqueada_ate: DataHora
  minutos_restantes: number
}
