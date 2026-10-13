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
  /** A última novidade, para o leitor de tela (U4): pronto, recusado ou tirado. */
  anuncio: string
}

function miniatura(arquivo: File): string | null {
  if (!ehFoto(arquivo.type) || typeof URL.createObjectURL !== 'function') return null
  return URL.createObjectURL(arquivo)
}

function soltar(previa: string | null | undefined): void {
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
  const [anuncio, setAnuncio] = useState('')
  // C6: as chaves que estão na lista, atualizadas na hora (nunca dentro de um `setItens`): as
  // vagas valem já, mesmo antes de o React redesenhar.
  const naLista = useRef(new Set(iniciais.map((a) => `publicado-${a.id}`)))
  const escolhidos = useRef(new Map<string, File>())
  // O nome que a lista mostra, para o anúncio de "saiu da lista".
  const nomes = useRef(new Map(iniciais.map((a) => [`publicado-${a.id}`, a.nome])))
  const previas = useRef(new Map<string, string>())
  const fila = useRef<Promise<void>>(Promise.resolve())
  const proxima = useRef(0)
  // C3: saiu da tela, a fila para (nada novo é enviado, nenhum estado muda).
  const naTela = useRef(true)

  const mudar = useCallback((chave: string, mudanca: Partial<ItemAnexo>) => {
    if (!naTela.current) return
    // Tirado no meio do envio: o item não está mais na lista e nada muda.
    setItens((atuais) => atuais.map((i) => (i.chave === chave ? { ...i, ...mudanca } : i)))
  }, [])

  const enviar = useCallback(
    (chave: string) => {
      fila.current = fila.current.then(async () => {
        const arquivo = escolhidos.current.get(chave)
        if (!arquivo || !naTela.current) return
        try {
          const enviado = await enviarArquivo(arquivo, 'aviso')
          if (!naLista.current.has(chave)) return
          nomes.current.set(chave, enviado.nome)
          // O nome pode ter mudado (foto.jpg → foto.webp, na compressão).
          mudar(chave, {
            situacao: 'pronto',
            arquivo: enviado,
            nome: enviado.nome,
            tipo: enviado.tipo,
          })
          if (naTela.current) setAnuncio(`${enviado.nome} pronto para anexar.`)
        } catch (e) {
          if (!naLista.current.has(chave)) return
          const erro = comoErroDaApi(e)
          // 422: o arquivo em si foi recusado (tipo, tamanho); mandar o mesmo de novo não adianta.
          mudar(chave, { situacao: 'erro', erro: erro.mensagem, podeTentar: erro.status !== 422 })
          if (naTela.current) setAnuncio(`Não deu para anexar ${arquivo.name}: ${erro.mensagem}`)
        }
      })
    },
    [mudar],
  )

  const adicionar = useCallback(
    (arquivos: readonly File[]) => {
      const vagas = Math.max(0, MAXIMO_DE_ANEXOS - naLista.current.size)
      const entram = arquivos.slice(0, vagas)
      const novos: ItemAnexo[] = entram.map((arquivo) => {
        const chave = `escolhido-${proxima.current++}`
        const previa = miniatura(arquivo)
        naLista.current.add(chave)
        nomes.current.set(chave, arquivo.name)
        escolhidos.current.set(chave, arquivo)
        if (previa) previas.current.set(chave, previa)
        return { chave, nome: arquivo.name, tipo: arquivo.type, previa, situacao: 'enviando' }
      })
      setItens((atuais) => [...atuais, ...novos])
      for (const item of novos) enviar(item.chave)
      return arquivos.slice(vagas).map((a) => a.name)
    },
    [enviar],
  )

  const tirar = useCallback((chave: string) => {
    if (!naLista.current.delete(chave)) return
    escolhidos.current.delete(chave)
    soltar(previas.current.get(chave))
    previas.current.delete(chave)
    setAnuncio(`${nomes.current.get(chave) ?? 'O arquivo'} saiu da lista.`)
    nomes.current.delete(chave)
    setItens((atuais) => atuais.filter((i) => i.chave !== chave))
  }, [])

  const tentarDeNovo = useCallback(
    (chave: string) => {
      mudar(chave, { situacao: 'enviando', erro: undefined })
      enviar(chave)
    },
    [enviar, mudar],
  )

  useEffect(() => {
    naTela.current = true
    const locais = previas.current
    const arquivos = escolhidos.current
    return () => {
      // Saiu da tela: a fila não manda mais nada e as miniaturas locais saem da memória.
      naTela.current = false
      arquivos.clear()
      for (const previa of locais.values()) soltar(previa)
      locais.clear()
    }
  }, [])

  return { itens, adicionar, tirar, tentarDeNovo, anuncio }
}
