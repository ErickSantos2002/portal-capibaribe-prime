// Indicações · as regras do formulário do prestador (indicar e corrigir), fora dos componentes.
import type { comoErroDaApi } from '../avisos/carregar'

export interface DadosDoPrestador {
  categoria: string
  nome: string
  telefone: string
  instagram: string
}

export type ErrosDoPrestador = Partial<Record<keyof DadosDoPrestador, string>>

const MIN_NOME = 2
export const LIMITE_NOME = 80

/** Os dígitos que a API guarda (a mesma regra de `validar_telefone`), ou `null` se não é um
 *  telefone brasileiro com DDD. Sem o 55 do país; celular escrito sem o nono dígito (10 dígitos,
 *  o terceiro de 6 a 9) ganha o 9; fixo começa de 2 a 5. */
export function digitosDoTelefone(texto: string): string | null {
  let digitos = texto.replace(/\D/g, '').replace(/^55(?=\d{10,11}$)/, '')
  if (/^\d{2}[6-9]\d{7}$/.test(digitos)) digitos = `${digitos.slice(0, 2)}9${digitos.slice(2)}`
  return /^[1-9]{2}(9\d{8}|[2-5]\d{7})$/.test(digitos) ? digitos : null
}

/** O que a tela confere antes de mandar (a API confere tudo de novo). */
export function conferirPrestador(dados: DadosDoPrestador): ErrosDoPrestador {
  const erros: ErrosDoPrestador = {}
  if (!dados.categoria) erros.categoria = 'Escolha o serviço.'
  const nome = dados.nome.trim()
  if (!nome) erros.nome = 'Escreva o nome do prestador ou da empresa.'
  else if (nome.length < MIN_NOME) erros.nome = `Escreva pelo menos ${MIN_NOME} letras.`
  if (!dados.telefone.trim()) erros.telefone = 'Escreva o WhatsApp ou o telefone, com DDD.'
  else if (digitosDoTelefone(dados.telefone) === null) {
    erros.telefone = 'Escreva o WhatsApp ou o telefone com DDD, por exemplo (81) 9 9999-0001.'
  }
  return erros
}

/** Os erros que a API apontou nos campos (422). */
export function errosDaApi(erro: ReturnType<typeof comoErroDaApi>): ErrosDoPrestador {
  return {
    categoria: erro.doCampo('categoria_id'),
    nome: erro.doCampo('nome'),
    telefone: erro.doCampo('telefone'),
    instagram: erro.doCampo('instagram'),
  }
}
