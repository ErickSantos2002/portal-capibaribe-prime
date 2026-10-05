// A moldura de toda tela: topo (título, placa ou seta de voltar, botão de tema), conteúdo e
// navegação. Celular e computador pelo mesmo HTML; o CSS (≥ 900 px) troca o layout.
import { useEffect, useRef, type ReactNode } from 'react'
import { useNavigate } from 'react-router'
import { BotaoTema } from './BotaoTema'
import { useSessao } from './contextoSessao'
import { Icone } from './Icone'
import { Navegacao } from './Navegacao'
import { Placa } from './Placa'

const NOME_DO_PORTAL = 'Portal Capibaribe Prime'

// A primeira tela aberta não rouba o foco; as seguintes levam o foco ao título, para o leitor de
// tela anunciar onde a pessoa chegou (como no protótipo).
let jaAbriuUmaTela = false

interface Props {
  /** Título do topo e da aba do navegador. */
  titulo: string
  /** Tela de detalhe: seta de voltar para este caminho (se não houver histórico) e, no
   *  celular, sem as abas de baixo. */
  voltar?: string
  /** Tela de entrada (sem topo): o botão de tema fica solto e o título vai no conteúdo. */
  entrada?: boolean
  /** Fora do conteúdo, ex.: o botão flutuante "Novo aviso". */
  extra?: ReactNode
  children: ReactNode
}

export function Tela({ titulo, voltar, entrada, extra, children }: Props) {
  const { eu } = useSessao()
  const navegar = useNavigate()
  const titulo1 = useRef<HTMLHeadingElement>(null)
  const comNav = !!eu && !eu.precisa_trocar_senha && !entrada

  useEffect(() => {
    document.title = entrada ? NOME_DO_PORTAL : `${titulo} · ${NOME_DO_PORTAL}`
  }, [titulo, entrada])

  useEffect(() => {
    if (jaAbriuUmaTela) titulo1.current?.focus({ preventScroll: true })
    jaAbriuUmaTela = true
  }, [titulo])

  function aoVoltar() {
    // Link aberto direto do WhatsApp não tem histórico: vai para a tela de cima, sem sair.
    const indice = (window.history.state as { idx?: number } | null)?.idx ?? 0
    if (indice > 0) navegar(-1)
    else navegar(voltar ?? '/avisos')
  }

  const classes = ['app', voltar && 'detalhe', !comNav && 'sem-nav'].filter(Boolean).join(' ')
  return (
    <div className={classes}>
      <a className="pular" href="#conteudo">
        Pular para o conteúdo
      </a>
      {entrada ? (
        <BotaoTema solto />
      ) : (
        <header className="topo">
          {voltar && (
            <button type="button" className="voltar" onClick={aoVoltar}>
              <Icone nome="voltar" tamanho={28} rotulo="Voltar" />
            </button>
          )}
          <h1 ref={titulo1} tabIndex={-1}>
            {titulo}
          </h1>
          {!voltar && eu && <Placa unidade={eu.unidade} gestao={eu.gestao} />}
          <BotaoTema />
        </header>
      )}
      <main className="conteudo" id="conteudo" tabIndex={-1}>
        {children}
      </main>
      {extra}
      {comNav && <Navegacao eu={eu} />}
    </div>
  )
}
