// A moldura de toda tela: topo (título, placa ou seta de voltar, botão de tema), conteúdo e
// navegação. Celular e computador pelo mesmo HTML; o CSS (≥ 900 px) troca o layout.
import { useContext, useEffect, useLayoutEffect, useRef, type ReactNode } from 'react'
import { useNavigate } from 'react-router'
import { BotaoTema } from './BotaoTema'
import { ContextoLugarDoRecado } from './contextoRecado'
import { useSessao } from './contextoSessao'
import { Icone } from './Icone'
import { useLetraGrande } from './letra'
import { Navegacao } from './Navegacao'
import { Placa } from './Placa'

const NOME_DO_PORTAL = 'Portal Capibaribe Prime'

// A primeira tela aberta não rouba o foco; as seguintes levam o foco ao título, para o leitor de
// tela anunciar onde a pessoa chegou (como no protótipo).
let jaAbriuUmaTela = false

interface Props {
  /** Título do topo e da aba do navegador. */
  titulo: string
  /** Na aba do navegador, quando o título do topo é o nome da tela e o do item é outro (o
   *  documento aberto: "Documento" no topo, o título dele na aba e na folha). */
  tituloDaAba?: string
  /** Tela de detalhe: seta de voltar para este caminho (se não houver histórico) e, no
   *  celular, sem as abas de baixo. */
  voltar?: string
  /** Tela de entrada (sem topo): o botão de tema fica solto e o título vai no conteúdo. */
  entrada?: boolean
  /** Fora do conteúdo, ex.: o botão flutuante "Novo aviso". */
  extra?: ReactNode
  children: ReactNode
}

export function Tela({ titulo, tituloDaAba, voltar, entrada, extra, children }: Props) {
  const { eu } = useSessao()
  const navegar = useNavigate()
  const titulo1 = useRef<HTMLHeadingElement>(null)
  // O lugar do recado: dentro do topo (que fica preso no alto), numa linha só dele. O recado
  // ocupa espaço ali e nunca cobre o conteúdo (ajustes do M4, ponto 8).
  const registrarLugarDoRecado = useContext(ContextoLugarDoRecado)
  const comNav = !!eu && !eu.precisa_trocar_senha && !entrada
  // Letra grande (M5, revisões, A): o topo fixo vira uma faixa fina, só com voltar (ou a placa)
  // e o tema numa linha, e o título desce para o começo do conteúdo, rolando com a página. A
  // 200 % num celular, o topo com o título chegava a ocupar mais da metade da tela, e o recado de
  // confirmação, que mora no topo, precisa continuar à vista. Com a letra de fábrica, o de sempre.
  const faixa = useLetraGrande()
  // O h1 muda de lugar (topo ↔ conteúdo) quando a letra muda com a tela aberta, e o elemento é
  // outro: se o foco estava nele, volta para o novo, senão cairia no body (2ª revisão do M5).
  const tituloTinhaFoco = useRef(false)
  useLayoutEffect(() => {
    if (tituloTinhaFoco.current) titulo1.current?.focus({ preventScroll: true })
  }, [faixa])

  useEffect(() => {
    document.title = entrada ? NOME_DO_PORTAL : `${tituloDaAba ?? titulo} · ${NOME_DO_PORTAL}`
  }, [titulo, tituloDaAba, entrada])

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

  const h1 = (
    <h1
      ref={titulo1}
      tabIndex={-1}
      className={faixa ? 'titulo-tela' : undefined}
      onFocus={() => (tituloTinhaFoco.current = true)}
      // Saiu da página (a troca de lugar): o Chrome avisa blur do elemento já removido, e aí o
      // foco tem de ir para o h1 novo; só um blur de verdade (outro elemento) zera a marca.
      onBlur={(e) => {
        if (e.currentTarget.isConnected) tituloTinhaFoco.current = false
      }}
    >
      {titulo}
    </h1>
  )
  const classes = ['app', voltar && 'detalhe', !comNav && 'sem-nav'].filter(Boolean).join(' ')
  return (
    <div className={classes}>
      <a className="pular" href="#conteudo">
        Pular para o conteúdo
      </a>
      {entrada ? (
        <>
          <BotaoTema solto />
          <div className="recado-lugar solto" ref={registrarLugarDoRecado} />
        </>
      ) : (
        <header className={faixa ? 'topo faixa' : 'topo'}>
          {voltar && (
            <button type="button" className="voltar" onClick={aoVoltar}>
              <Icone nome="voltar" tamanho={28} rotulo="Voltar" />
            </button>
          )}
          {!faixa && h1}
          {!voltar && eu && <Placa unidade={eu.unidade} gestao={eu.gestao} />}
          <BotaoTema />
          <div className="recado-lugar" ref={registrarLugarDoRecado} />
        </header>
      )}
      <main className="conteudo" id="conteudo" tabIndex={-1}>
        {faixa && !entrada && h1}
        {children}
      </main>
      {extra}
      {comNav && <Navegacao eu={eu} />}
    </div>
  )
}
