// Comum · Envio de arquivo: uma função por rota (spec do M3, seção 5.1). Arquivo comum: os épicos
// usam `enviarArquivo` (enviar.ts), que chama estas duas.
import { api } from '../api/cliente'
import type { ArquivoEnviado, EnvioAutorizado, PedirEnvio } from './tipos'

/** Cria o arquivo pendente e devolve a URL assinada (10 minutos) para o PUT. */
export const pedirEnvio = (dados: PedirEnvio) => api.post<EnvioAutorizado>('/api/arquivos', dados)

/** O servidor confere o conteúdo e publica; devolve o tipo e o tamanho de verdade. */
export const confirmarEnvio = (arquivoId: number) =>
  api.post<ArquivoEnviado>(`/api/arquivos/${arquivoId}/confirmar`)
