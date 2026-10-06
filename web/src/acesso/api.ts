// Épico A · Acesso: uma função por rota do contrato (spec do M1, seção 4.2). Pertence ao épico A.
import { api } from '../api/cliente'
import type { Eu } from '../api/tipos'
import type {
  ApagarDados,
  DadosDaUnidade,
  Entrar,
  MinhaUnidade,
  PrimeiroAcesso,
  TrocarSenha,
} from './tipos'

export const entrar = (dados: Entrar) => api.post<Eu>('/api/acesso/entrar', dados)

export const concluirPrimeiroAcesso = (dados: PrimeiroAcesso) =>
  api.post<Eu>('/api/acesso/primeiro-acesso', dados)

export const buscarMinhaUnidade = () => api.get<MinhaUnidade>('/api/minha-unidade')

export const salvarDados = (dados: DadosDaUnidade) =>
  api.put<MinhaUnidade>('/api/minha-unidade/dados', dados)

export const trocarSenha = (dados: TrocarSenha) => api.put<void>('/api/minha-unidade/senha', dados)

export const desconectarAparelho = (id: number) =>
  api.delete<void>(`/api/minha-unidade/aparelhos/${id}`)

export const apagarDados = (senha: string) =>
  api.post<void>('/api/minha-unidade/apagar-dados', { confirmo: true, senha } satisfies ApagarDados)
