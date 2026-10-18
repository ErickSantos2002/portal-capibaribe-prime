// Navegação (spec docs/superpowers/specs/2026-10-18-navegacao-bola-design.md). No celular, a barra
// de baixo com o arco: 4 lugares fixos e a bola "Menu" no meio, que abre a folha com todos os
// lugares. No computador, o menu lateral verde, agrupado. Os dois saem da lista única de lugares
// (casca/menu.ts) e estão sempre no DOM; o CSS mostra um ou outro pelo `@container raiz`.
import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router'
import type { Eu } from '../api/tipos'
import { contarNaoLidos } from '../avisos/api'
import { nomeDoPapel } from './formatar'
import { Icone } from './Icone'
import { agrupados, daBarra, lugarAtual, lugaresDo, type Lugar } from './menu'
import { Logo } from '../marca/Logo'
import { BotaoVersao } from '../sobre/BotaoVersao'
import { Placa } from './Placa'

/** Número de avisos não lidos na aba. Falhou (ou a rota ainda não existe): sem número. */
function useNaoLidos(): number {
  const [quantidade, setQuantidade] = useState(0)
  const { pathname } = useLocation()
  useEffect(() => {
    let ativo = true
    contarNaoLidos()
      .then((r) => {
        if (ativo) setQuantidade(r.quantidade)
      })
      .catch(() => {
        if (ativo) setQuantidade(0)
      })
    return () => {
      ativo = false
    }
  }, [pathname])
  return quantidade
}

/** A plaquinha com o número de não lidos (na aba, no menu lateral e na folha). */
export function Conta({ lugar, naoLidos }: { lugar: Lugar; naoLidos: number }) {
  if (lugar.contador !== 'nao-lidos' || naoLidos <= 0) return null
  return (
    <span className="conta" aria-label={`${naoLidos} não lidos`}>
      {naoLidos}
    </span>
  )
}

function Aba({ lugar, atual, naoLidos }: { lugar: Lugar; atual?: Lugar; naoLidos: number }) {
  return (
    <Link to={lugar.para} aria-current={lugar === atual ? 'page' : undefined}>
      <Icone nome={lugar.icone} />
      {lugar.curto ? (
        // Na tela estreita (< 340 px), o CSS troca o nome inteiro pelo curto ("Docs"). O inteiro
        // continua para o leitor de tela, que nunca ouve o curto.
        <span className="nav-rotulo">
          <span className="rot-longo">{lugar.texto}</span>
          <span className="rot-curto" aria-hidden="true">
            {lugar.curto}
          </span>
        </span>
      ) : (
        <span className="nav-rotulo">{lugar.texto}</span>
      )}
      <Conta lugar={lugar} naoLidos={naoLidos} />
    </Link>
  )
}

export function Navegacao({ eu }: { eu: Eu }) {
  const naoLidos = useNaoLidos()
  const { pathname } = useLocation()
  const [aberta, setAberta] = useState(false)
  const papel = eu.papeis.includes('admin') ? 'admin' : eu.papeis[0]
  const lugares = lugaresDo(eu)
  const atual = lugarAtual(lugares, pathname)
  const barra = daBarra(lugares)
  // Fora dos 4 da barra (Unidades, o histórico da administração…): nenhuma aba acende, e a bola
  // ganha o tracinho, mostrando que você está num lugar do Menu (spec, seção 3).
  const naBola = !atual?.naBarra
  // Um lugar que mora só na folha e tem número (ex.: Encomendas, na E2) acende um pontinho na bola.
  const avisoNaBola = naoLidos > 0 && lugares.some((l) => !l.naBarra && l.contador === 'nao-lidos')

  const aba = (lugar: Lugar | null, posicao: number) =>
    lugar ? (
      <Aba key={lugar.para} lugar={lugar} atual={atual} naoLidos={naoLidos} />
    ) : (
      // A vaga de um lugar que não vale para esta pessoa: ninguém sobe para ela (spec, seção 5).
      <span key={`vaga-${posicao}`} className="nav-vaga" />
    )

  return (
    <nav className="nav" aria-label="Seções do Portal">
      <div className="nav-barra">
        {/* O arco da borda de cima: desenho só, os cantos transparentes não pegam o toque. */}
        <svg className="nav-arco" viewBox="0 0 100 10" preserveAspectRatio="none" aria-hidden="true">
          <path d="M0 10Q50-10 100 10Z" />
          <path className="nav-arco-linha" d="M0 10Q50-10 100 10" />
        </svg>
        {barra.slice(0, 2).map(aba)}
        <button
          type="button"
          className="nav-bola"
          aria-haspopup="dialog"
          aria-expanded={aberta}
          data-aqui={naBola ? '' : undefined}
          onClick={() => setAberta((antes) => !antes)}
        >
          <span className="nav-bola-circulo">
            <Icone nome="grade" />
            {avisoNaBola && <span className="nav-bola-ponto" role="img" aria-label="Há novidades no Menu" />}
          </span>
          <span className="nav-bola-rotulo">Menu</span>
        </button>
        {barra.slice(2).map((lugar, i) => aba(lugar, i + 2))}
      </div>

      <div className="nav-lateral">
        <span className="nav-marca">
          <Logo cartao />
        </span>
        {agrupados(lugares).map((grupo) => (
          <div key={grupo.grupo} className="nav-grupo-lugares">
            <h2 className="nav-grupo">{grupo.nome}</h2>
            {grupo.lugares.map((lugar) => (
              <Link key={lugar.para} to={lugar.para} aria-current={lugar === atual ? 'page' : undefined}>
                <Icone nome={lugar.icone} />
                <span>{lugar.texto}</span>
                <Conta lugar={lugar} naoLidos={naoLidos} />
              </Link>
            ))}
          </div>
        ))}
        <span className="nav-placa">
          <Placa unidade={eu.unidade} gestao={eu.gestao} />
          {papel && <span>{nomeDoPapel(papel)}</span>}
        </span>
        {/* Só no computador (no celular, a versão fica no fim de Minha unidade). */}
        <BotaoVersao />
      </div>
    </nav>
  )
}
