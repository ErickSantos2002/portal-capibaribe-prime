// M3 · Épico B: a lista de anexos do formulário do aviso (spec `m3-anexos.md`, seção 3.2).
// Cada arquivo escolhido entra na hora e é enviado (`enviarArquivo`), um de cada vez, na ordem.
import { useCallback, useEffect, useRef, useState } from 'react'
import { enviarArquivo } from '../arquivos/enviar'
import type { ArquivoEnviado } from '../arquivos/tipos'
import { ehFoto, MAXIMO_DE_ANEXOS, type ItemAnexo } from './anexos'
import { comoErroDaApi } from './carregar'

export interface ListaDeAnexos {
  itens: ItemAnexo[]
  /** Põe na lista e manda enviar; devolve os nomes que ficaram de fora (passou de 5). */
  adicionar: (arquivos: readonly File[]) => string[]
  tirar: (chave: string) => void
  tentarDeNovo: (chave: string) => void
}

function miniatura(arquivo: File): string | null {
  if (!ehFoto(arquivo.type) || typeof URL.createObjectURL !== 'function') return null
  return URL.createObjectURL(arquivo)
}

function soltar(previa: string | null): void {
  if (previa && typeof URL.revokeObjectURL === 'function') URL.revokeObjectURL(previa)
}

/** `iniciais`: os anexos da versão em vigor, na correção (já prontos). */
export function useAnexos(iniciais: readonly ArquivoEnviado[] = []): ListaDeAnexos {
  const [itens, setItens] = useState<ItemAnexo[]>(() =>
    iniciais.map((a) => ({
      chave: `publicado-${a.id}`,
      nome: a.nome,
      tipo: a.tipo,
      previa: null,
      situacao: 'pronto',
      arquivo: a,
      jaPublicado: true,
    })),
  )
  // O que a tela precisa saber na hora, sem esperar o React redesenhar.
  const quantos = useRef(iniciais.length)
  const escolhidos = useRef(new Map<string, File>())
  const previas = useRef(new Map<string, string>())
  const fila = useRef<Promise<void>>(Promise.resolve())
  const proxima = useRef(0)

  const mudar = useCallback((chave: string, mudanca: Partial<ItemAnexo>) => {
    // Tirado no meio do envio: o item não está mais na lista e nada muda.
    setItens((atuais) => atuais.map((i) => (i.chave === chave ? { ...i, ...mudanca } : i)))
  }, [])

  const enviar = useCallback(
    (chave: string) => {
      fila.current = fila.current.then(async () => {
        const arquivo = escolhidos.current.get(chave)
        if (!arquivo) return
        try {
          const enviado = await enviarArquivo(arquivo, 'aviso')
          // O nome pode ter mudado (foto.jpg → foto.webp, na compressão).
          mudar(chave, {
            situacao: 'pronto',
            arquivo: enviado,
            nome: enviado.nome,
            tipo: enviado.tipo,
          })
        } catch (e) {
          const erro = comoErroDaApi(e)
          // 422: o arquivo em si foi recusado (tipo, tamanho); mandar o mesmo de novo não adianta.
          mudar(chave, { situacao: 'erro', erro: erro.mensagem, podeTentar: erro.status !== 422 })
        }
      })
    },
    [mudar],
  )

  const adicionar = useCallback(
    (arquivos: readonly File[]) => {
      const vagas = Math.max(0, MAXIMO_DE_ANEXOS - quantos.current)
      const entram = arquivos.slice(0, vagas)
      const novos: ItemAnexo[] = entram.map((arquivo) => {
        const chave = `escolhido-${proxima.current++}`
        const previa = miniatura(arquivo)
        escolhidos.current.set(chave, arquivo)
        if (previa) previas.current.set(chave, previa)
        return { chave, nome: arquivo.name, tipo: arquivo.type, previa, situacao: 'enviando' }
      })
      quantos.current += novos.length
      setItens((atuais) => [...atuais, ...novos])
      for (const item of novos) enviar(item.chave)
      return arquivos.slice(vagas).map((a) => a.name)
    },
    [enviar],
  )

  const tirar = useCallback((chave: string) => {
    escolhidos.current.delete(chave)
    soltar(previas.current.get(chave) ?? null)
    previas.current.delete(chave)
    setItens((atuais) => {
      const restantes = atuais.filter((i) => i.chave !== chave)
      quantos.current = restantes.length
      return restantes
    })
  }, [])

  const tentarDeNovo = useCallback(
    (chave: string) => {
      mudar(chave, { situacao: 'enviando', erro: undefined })
      enviar(chave)
    },
    [enviar, mudar],
  )

  // Saiu da tela: as miniaturas locais deixam de ocupar memória.
  useEffect(() => {
    const locais = previas.current
    return () => {
      for (const previa of locais.values()) soltar(previa)
      locais.clear()
    }
  }, [])

  return { itens, adicionar, tirar, tentarDeNovo }
}
