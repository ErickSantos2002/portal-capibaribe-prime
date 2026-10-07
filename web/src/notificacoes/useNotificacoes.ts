// Estado das notificações neste aparelho e as ações de ativar e desativar (H-05; spec
// m2-push.md, seção 3.3). Usado pela tela "Receber os avisos" e por Minha unidade.
import { useCallback, useEffect, useState } from 'react'
import { ErroDaApi } from '../api/cliente'
import { useRecado } from '../casca/contextoRecado'
import { lerEstadoDasNotificacoes } from './api'
import { situacaoDoAparelho, type SituacaoDoAparelho } from './aparelho'
import { ativar, desativar, mostrarExemplo, sincronizar } from './inscricao'

export type SituacaoNotificacoes =
  | 'carregando'
  | 'erro'
  | 'desligado'
  | Exclude<SituacaoDoAparelho, 'pronta'>
  | 'inativa'
  | 'ativa'

interface Estado {
  situacao: SituacaoNotificacoes
  chave: string | null
}

export interface Problema {
  mensagem: string
  /** Muda a cada erro, para a caixa receber o foco de novo. */
  vez: number
}

const MSG_INESPERADA = 'Não deu para mudar as notificações agora. Tente de novo daqui a pouco.'

function mensagemDe(falha: unknown): string {
  return falha instanceof ErroDaApi ? falha.mensagem : MSG_INESPERADA
}

async function lerSituacao(): Promise<Estado> {
  const api = await lerEstadoDasNotificacoes()
  if (!api.disponivel || !api.chave_publica) return { situacao: 'desligado', chave: null }
  const aparelho = situacaoDoAparelho()
  if (aparelho !== 'pronta') return { situacao: aparelho, chave: api.chave_publica }
  // Quem já tinha ativado e entrou de novo volta a receber sem perguntar nada.
  const ativa = await sincronizar(api)
  return { situacao: ativa ? 'ativa' : 'inativa', chave: api.chave_publica }
}

export function useNotificacoes() {
  const recado = useRecado()
  const [estado, setEstado] = useState<Estado>({ situacao: 'carregando', chave: null })
  const [problema, setProblema] = useState<Problema | null>(null)
  const [dica, setDica] = useState<string | null>(null)
  const [ocupado, setOcupado] = useState(false)
  // Mensagem de quando a leitura falhou (sem conexão, sessão caiu).
  const [falhaAoLer, setFalhaAoLer] = useState<string | null>(null)

  const atualizar = useCallback(async () => {
    try {
      const lido = await lerSituacao()
      setEstado(lido)
      setFalhaAoLer(null)
    } catch (falha) {
      setEstado({ situacao: 'erro', chave: null })
      setFalhaAoLer(mensagemDe(falha))
    }
  }, [])

  useEffect(() => {
    let ativo = true
    lerSituacao().then(
      (lido) => ativo && setEstado(lido),
      (falha: unknown) => {
        if (!ativo) return
        setEstado({ situacao: 'erro', chave: null })
        setFalhaAoLer(mensagemDe(falha))
      },
    )
    // Voltou dos Ajustes depois de liberar a permissão: confere de novo.
    const aoVoltar = () => {
      if (document.visibilityState === 'visible') void atualizar()
    }
    document.addEventListener('visibilitychange', aoVoltar)
    return () => {
      ativo = false
      document.removeEventListener('visibilitychange', aoVoltar)
    }
  }, [atualizar])

  const falhar = (falha: unknown) =>
    setProblema((anterior) => ({ mensagem: mensagemDe(falha), vez: (anterior?.vez ?? 0) + 1 }))

  /** Ligar no `onClick` direto: o pedido de permissão sai antes de qualquer espera. */
  function aoAtivar() {
    if (!estado.chave) return
    const pedido = ativar(estado.chave)
    setOcupado(true)
    setProblema(null)
    setDica(null)
    pedido
      .then((resultado) => {
        if (resultado === 'ativa') {
          setEstado((atual) => ({ ...atual, situacao: 'ativa' }))
          recado('Notificações ativadas neste aparelho.')
          void mostrarExemplo()
        } else if (resultado === 'bloqueada') {
          setEstado((atual) => ({ ...atual, situacao: 'bloqueada' }))
        } else {
          setDica('Tudo bem. Dá para ativar depois, aqui mesmo.')
        }
      }, falhar)
      .finally(() => setOcupado(false))
  }

  function aoDesativar() {
    setOcupado(true)
    setProblema(null)
    setDica(null)
    desativar()
      .then(() => {
        setEstado((atual) => ({ ...atual, situacao: 'inativa' }))
        recado('Notificações desativadas neste aparelho.')
      }, falhar)
      .finally(() => setOcupado(false))
  }

  return { ...estado, problema, dica, ocupado, falhaAoLer, aoAtivar, aoDesativar, atualizar }
}

export type Notificacoes = ReturnType<typeof useNotificacoes>
