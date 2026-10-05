// Épico C · Avisos: carregar dados da API numa tela. Pertence ao épico C.
import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router'
import { ErroDaApi } from '../api/cliente'

export type Carga<T> =
  | { situacao: 'carregando'; dados?: T }
  | { situacao: 'pronta'; dados: T }
  | { situacao: 'erro'; erro: ErroDaApi; dados?: T }

function comoErroDaApi(erro: unknown): ErroDaApi {
  if (erro instanceof ErroDaApi) return erro
  return new ErroDaApi(0, {
    codigo: 'erro_inesperado',
    mensagem: 'Algo deu errado no Portal. Tente de novo daqui a pouco.',
  })
}

interface Resultado<T> {
  chave: string
  dados?: T
  erro?: ErroDaApi
}

/**
 * `const [carga, recarregar, trocar] = useCarga(() => abrirAviso(id), [id])`
 *
 * Cada pedido é marcado pelas `chaves`: resposta de um pedido antigo (a busca, uma letra de
 * cada vez) é descartada. Enquanto carrega, os dados de antes continuam lá, para a lista não
 * piscar.
 */
export function useCarga<T>(
  buscar: () => Promise<T>,
  chaves: readonly unknown[],
): [Carga<T>, () => void, (dados: T) => void] {
  const [vez, setVez] = useState(0)
  const chave = JSON.stringify([vez, ...chaves])
  const [resultado, setResultado] = useState<Resultado<T> | null>(null)

  useEffect(() => {
    let ativo = true
    buscar()
      .then((dados) => {
        if (ativo) setResultado({ chave, dados })
      })
      .catch((erro: unknown) => {
        if (ativo) {
          setResultado((antes) => ({ chave, erro: comoErroDaApi(erro), dados: antes?.dados }))
        }
      })
    return () => {
      ativo = false
    }
    // `buscar` muda a cada render; quem decide quando buscar de novo são as chaves.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chave])

  const recarregar = useCallback(() => setVez((v) => v + 1), [])
  const trocar = useCallback((dados: T) => setResultado({ chave, dados }), [chave])

  let carga: Carga<T>
  if (resultado?.chave !== chave) carga = { situacao: 'carregando', dados: resultado?.dados }
  else if (resultado.erro)
    carga = { situacao: 'erro', erro: resultado.erro, dados: resultado.dados }
  else carga = { situacao: 'pronta', dados: resultado.dados as T }
  return [carga, recarregar, trocar]
}

export { comoErroDaApi }

/** O `:id` do endereço, ou nulo se não for um número (link quebrado). */
export function useIdDoAviso(): number | null {
  const { id } = useParams()
  return id && /^\d{1,15}$/.test(id) ? Number(id) : null
}
