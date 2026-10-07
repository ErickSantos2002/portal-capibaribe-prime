import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, ErroDaApi } from '../api/cliente'
import type { Eu } from '../api/tipos'
import { esquecerEsteAparelho } from '../notificacoes/inscricao'
import { ContextoSessao, type EstadoSessao, type ValorSessao } from './contextoSessao'

async function buscarEu(): Promise<EstadoSessao> {
  try {
    return { situacao: 'pronta', eu: await api.get<Eu>('/api/acesso/eu') }
  } catch (erro) {
    if (erro instanceof ErroDaApi && erro.status === 401) return { situacao: 'pronta', eu: null }
    const mensagem = erro instanceof ErroDaApi ? erro.mensagem : 'Não foi possível abrir o Portal.'
    return { situacao: 'sem_conexao', mensagem }
  }
}

export function SessaoProvider({ children }: { children: ReactNode }) {
  const [estado, setEstado] = useState<EstadoSessao>({ situacao: 'carregando' })

  useEffect(() => {
    let ativo = true
    buscarEu().then((novo) => {
      if (ativo) setEstado(novo)
    })
    return () => {
      ativo = false
    }
  }, [])

  const recarregar = useCallback(async () => setEstado(await buscarEu()), [])
  const definir = useCallback((eu: Eu | null) => setEstado({ situacao: 'pronta', eu }), [])
  // Só esquece a sessão quando a API confirmou (204) ou ela já não existia (401). Qualquer outra
  // falha (sem internet, erro do servidor) mantém a pessoa logada e repassa o erro para a tela
  // mostrar: dizer "saiu" com o cookie ainda válido no aparelho seria mentir.
  const sair = useCallback(async () => {
    try {
      await api.post<void>('/api/acesso/sair')
    } catch (erro) {
      if (!(erro instanceof ErroDaApi && erro.status === 401)) throw erro
    }
    // M2 (épico A): a inscrição de push do navegador sai junto, senão a próxima unidade a
    // entrar neste navegador herdaria as notificações.
    void esquecerEsteAparelho()
    setEstado({ situacao: 'pronta', eu: null })
  }, [])

  const valor = useMemo<ValorSessao>(
    () => ({
      estado,
      eu: estado.situacao === 'pronta' ? estado.eu : null,
      definir,
      recarregar,
      sair,
    }),
    [estado, definir, recarregar, sair],
  )
  return <ContextoSessao.Provider value={valor}>{children}</ContextoSessao.Provider>
}
