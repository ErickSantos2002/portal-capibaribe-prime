// Abas embaixo no celular; menu lateral verde no computador (protótipo, seção 3.3).
import { useEffect, useState } from 'react'
import { NavLink, useLocation } from 'react-router'
import type { Eu } from '../api/tipos'
import { contarNaoLidos } from '../avisos/api'
import { nomeDoPapel } from './formatar'
import { Icone } from './Icone'
import { itensDoMenu } from './menu'
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

export function Navegacao({ eu }: { eu: Eu }) {
  const naoLidos = useNaoLidos()
  const papel = eu.papeis.includes('admin') ? 'admin' : eu.papeis[0]
  return (
    <nav className="nav" aria-label="Seções do Portal">
      <span className="nav-marca">
        Portal
        <br />
        Capibaribe Prime
      </span>
      {itensDoMenu(eu).map((item) => (
        <NavLink key={item.para} to={item.para}>
          <Icone nome={item.icone} />
          <span>{item.texto}</span>
          {item.para === '/avisos' && naoLidos > 0 && (
            <span className="conta" aria-label={`${naoLidos} não lidos`}>
              {naoLidos}
            </span>
          )}
        </NavLink>
      ))}
      <span className="nav-placa">
        <Placa unidade={eu.unidade} gestao={eu.gestao} />
        {papel && <span>{nomeDoPapel(papel)}</span>}
      </span>
      {/* Só no computador (no celular, a versão fica no fim de Minha unidade). */}
      <BotaoVersao />
    </nav>
  )
}
