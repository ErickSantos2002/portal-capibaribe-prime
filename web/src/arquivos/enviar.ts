// Comum · `enviarArquivo` (spec do M3, seções 4 e 7): conferir na tela → comprimir (foto) →
// pedir a URL → PUT direto no bucket → confirmar. Devolve o `ArquivoEnviado` (o id vai no
// documento ou no aviso) ou lança `ErroDaApi` com a mensagem pronta para mostrar.
// Arquivo comum: os épicos usam, não editam.
import { ErroDaApi } from '../api/cliente'
import { confirmarEnvio, pedirEnvio } from './api'
import { comprimir, ferramentasDoNavegador, type Ferramentas } from './comprimir'
import { LIMITES, problemaNaTela } from './limites'
import type { ArquivoEnviado, Finalidade, TipoArquivo } from './tipos'

export const MENSAGEM_NAO_CHEGOU =
  'O arquivo não chegou ao Portal. Confira a internet e envie de novo.'

/** Quanto o PUT pode demorar antes de desistir: 2 minutos, mais o tempo de mandar o arquivo a
 *  50 KB/s (internet ruim de celular), até 10 minutos (a validade da URL assinada). Um arquivo de
 *  20 MB tem 9 minutos. Sem isso, um PUT parado prenderia a tela para sempre. */
export function prazoDoEnvio(tamanho: number): number {
  return Math.min(10 * 60_000, 2 * 60_000 + Math.ceil(tamanho / 50))
}

function recusadoNaTela(mensagem: string): ErroDaApi {
  return new ErroDaApi(422, {
    codigo: 'dados_invalidos',
    mensagem,
    campos: [{ campo: 'arquivo', mensagem }],
  })
}

export async function enviarArquivo(
  escolhido: File,
  finalidade: Finalidade,
  ferramentas: Ferramentas = ferramentasDoNavegador,
): Promise<ArquivoEnviado> {
  // O tipo antes de comprimir (não adianta reduzir um .exe); o tamanho depois (o que vai é o
  // comprimido, e é ele que a API confere).
  const tipoRecusado = problemaNaTela({ type: escolhido.type, size: 1 }, finalidade)
  if (tipoRecusado) throw recusadoNaTela(tipoRecusado)

  const arquivo = await comprimir(escolhido, ferramentas, LIMITES[finalidade])
  const problema = problemaNaTela(arquivo, finalidade)
  if (problema) throw recusadoNaTela(problema)

  const envio = await pedirEnvio({
    nome: arquivo.name,
    tipo: arquivo.type as TipoArquivo,
    finalidade,
    tamanho_bytes: arquivo.size,
  })

  // Direto para o bucket: sem `X-Portal` (o R2 recusaria o cabeçalho que não está na
  // assinatura), sem cookie e com o Content-Type exato que foi assinado. O tamanho também está
  // na assinatura: o corpo é o mesmo `arquivo` cujo `size` foi declarado no pedido.
  const resposta = await fetch(envio.url, {
    method: 'PUT',
    headers: { 'Content-Type': envio.content_type },
    body: arquivo,
    credentials: 'omit',
    cache: 'no-store',
    // Passou do prazo: o fetch falha com TimeoutError e vira `arquivo_nao_chegou`, como a rede.
    signal: AbortSignal.timeout(prazoDoEnvio(arquivo.size)),
  }).catch(() => null)
  if (!resposta?.ok) {
    throw new ErroDaApi(resposta?.status ?? 0, {
      codigo: 'arquivo_nao_chegou',
      mensagem: MENSAGEM_NAO_CHEGOU,
    })
  }

  return confirmarEnvio(envio.arquivo_id)
}
