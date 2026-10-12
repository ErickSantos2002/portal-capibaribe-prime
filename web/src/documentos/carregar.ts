// Épico A do M3 · carregar dados da API numa tela. Pertence ao épico A (o `useCarga` dos avisos
// é do épico B, que está mexendo nele; dúvidas do épico A, item 7).
import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router'
import { ErroDaApi } from '../api/cliente'

export type Carga<T> =
  | { situacao: 'carregando'; dados?: T }
  | { situacao: 'pronta'; dados: T }
  | { situacao: 'erro'; erro: ErroDaApi; dados?: T }

export function comoErroDaApi(erro: unknown): ErroDaApi {
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

/** `const [carga, recarregar, trocar] = useCarga(() => abrirDocumento(id), [id])`. Resposta de
 *  um pedido antigo é descartada; enquanto recarrega, os dados de antes continuam na tela. */
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
        if (ativo) setResultado((antes) => ({ chave, erro: comoErroDaApi(erro), dados: antes?.dados }))
      })
    return () => {
      ativo = false
    }
    // Quem decide quando buscar de novo são as chaves (`buscar` muda a cada render).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chave])

  const recarregar = useCallback(() => setVez((v) => v + 1), [])
  const trocar = useCallback((dados: T) => setResultado({ chave, dados }), [chave])

  if (resultado?.chave !== chave) return [{ situacao: 'carregando', dados: resultado?.dados }, recarregar, trocar]
  if (resultado.erro) {
    return [{ situacao: 'erro', erro: resultado.erro, dados: resultado.dados }, recarregar, trocar]
  }
  return [{ situacao: 'pronta', dados: resultado.dados as T }, recarregar, trocar]
}

/** O `:id` do endereço, ou nulo se não for um número (link quebrado). */
export function useIdDoDocumento(): number | null {
  const { id } = useParams()
  return id && /^\d{1,15}$/.test(id) ? Number(id) : null
}
