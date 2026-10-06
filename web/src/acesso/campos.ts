// Regras de campo do épico A, com as mesmas mensagens da API (api/app/esquemas/acesso.py).
// A tela confere antes de mandar, para a Dona Socorro ver o erro na hora; a API confere de novo.
import { ErroDaApi, MENSAGEM_SEM_CONEXAO } from '../api/cliente'

export const SENHA_INICIAL = 'mudar123'

export interface ErroDeCampo {
  campo: string
  mensagem: string
}

/** Bloco 1 + "101" → "1101"; Bloco 1 + "7" ou "07" → "1007". Sem os dois, nulo. */
export function montarLogin(bloco: string, apartamento: string): string | null {
  const digitos = apartamento.replace(/\D/g, '')
  if (!/^[1-9]$/.test(bloco) || !digitos) return null
  return bloco + digitos.slice(-3).padStart(3, '0')
}

/**
 * Só números, até 3 dígitos. Limpa antes de cortar ("Apto 502" colado vira 502). Quem COLAR o
 * login antigo inteiro (1203) ganha o bloco marcado; digitando, o 4º dígito só é ignorado.
 */
export function limparApartamento(
  texto: string,
  colado: boolean,
): { apartamento: string; bloco: string | null } {
  const digitos = texto.replace(/\D/g, '')
  if (colado && digitos.length === 4 && /[1-5]/.test(digitos[0])) {
    return { apartamento: digitos.slice(1), bloco: digitos[0] }
  }
  return { apartamento: digitos.slice(0, 3), bloco: null }
}

/** A regra real da senha (a mesma da API): 8 caracteres ou mais, qualquer um. */
export const AJUDA_DA_SENHA =
  'Pelo menos 8 caracteres. Pode ter letras, números, espaços e símbolos. Não pode ser mudar123.'

export function validarSenhaNova(
  senha: string,
  repetida: string,
  atual?: string,
): ErroDeCampo | null {
  if (atual !== undefined && senha === atual && senha !== '') {
    return {
      campo: 'senha_nova',
      mensagem: 'A senha nova é igual à atual. Escolha uma diferente.',
    }
  }
  if (senha.length < 8) {
    return {
      campo: 'senha_nova',
      mensagem: 'A senha nova precisa ter pelo menos 8 caracteres.',
    }
  }
  if (senha === SENHA_INICIAL) {
    return {
      campo: 'senha_nova',
      mensagem: 'Escolha uma senha diferente da inicial, que todo mundo conhece.',
    }
  }
  if (senha !== repetida) {
    return {
      campo: 'senha_nova_repetida',
      mensagem: 'As duas senhas estão diferentes. Escreva a mesma nas duas.',
    }
  }
  return null
}

export interface ContatoDigitado {
  responsavel_nome: string
  celular: string
  email: string
}

export function validarContato(contato: ContatoDigitado): ErroDeCampo | null {
  if (!contato.responsavel_nome.trim()) {
    return {
      campo: 'responsavel_nome',
      mensagem: 'Escreva o nome de quem responde pela unidade.',
    }
  }
  const celular = contato.celular.replace(/\D/g, '')
  if (celular.length < 10 || celular.length > 11 || celular[0] === '0') {
    return {
      campo: 'celular',
      mensagem: 'Confira o celular: DDD e número, como (81) 9 1234-5678.',
    }
  }
  const email = contato.email.trim()
  if (email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
    return { campo: 'email', mensagem: 'Confira o e-mail, ou deixe em branco.' }
  }
  return null
}

/** O que a API recebe: e-mail vazio vira nulo (a API faria o mesmo). */
export function contatoParaApi(contato: ContatoDigitado) {
  return {
    responsavel_nome: contato.responsavel_nome,
    celular: contato.celular,
    email: contato.email.trim() || null,
  }
}

/** Erro de formulário a mostrar: o campo (se a API apontou um) e a mensagem. */
export function erroDaFalha(falha: unknown): { campo: string | null; mensagem: string } {
  if (!(falha instanceof ErroDaApi)) return { campo: null, mensagem: MENSAGEM_SEM_CONEXAO }
  const apontado = falha.campos.find((c) => c.campo)?.campo
  if (apontado) return { campo: apontado, mensagem: falha.mensagem }
  if (falha.codigo === 'senha_atual_incorreta') {
    return { campo: 'senha_atual', mensagem: falha.mensagem }
  }
  return { campo: null, mensagem: falha.mensagem }
}
