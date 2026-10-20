// Classificados · a moderação no anúncio aberto (spec, seções 3.2 e 9): a seção "Para a gestão"
// com os avisos recebidos (o motivo e a data, nunca quem avisou), "Resolver" em cada um e
// "Esconder este anúncio", que pergunta antes (o mesmo `Confirmar` das indicações).
import { useState } from 'react'
import { comoErroDaApi } from '../avisos/carregar'
import { useRecado } from '../casca/contextoRecado'
import { formatarDataEHora } from '../casca/formatar'
import { Icone } from '../casca/Icone'
import { Confirmar } from '../indicacoes/ParaAGestao'
import { esconderAnuncio, resolverAviso } from './api'
import type { Anuncio } from './tipos'

export function ParaAGestao({ anuncio, recarregar }: { anuncio: Anuncio; recarregar: () => void }) {
  const recado = useRecado()
  const [resolvendo, setResolvendo] = useState<number | null>(null)
  const [erro, setErro] = useState('')
  const avisos = anuncio.avisos ?? []

  async function resolver(id: number) {
    setResolvendo(id)
    setErro('')
    try {
      await resolverAviso(id)
      recado('Aviso resolvido.')
      recarregar()
    } catch (e) {
      setErro(comoErroDaApi(e).mensagem)
    } finally {
      setResolvendo(null)
    }
  }

  return (
    <section className="ind-gestao" aria-labelledby="cla-para-a-gestao">
      <h2 id="cla-para-a-gestao" className="secao">
        Para a gestão
      </h2>
      <h3 className="ind-gestao-titulo">Avisos da vizinhança</h3>
      {erro && (
        <div className="aviso-caixa erro" role="alert">
          <Icone nome="alerta" />
          <p>{erro}</p>
        </div>
      )}
      {avisos.length === 0 ? (
        <p className="vazio">Nenhum aviso aberto.</p>
      ) : (
        <ul className="folha ind-avisos">
          {avisos.map((a) => (
            <li key={a.id} className="ind-aviso">
              <div>
                <p className="ind-aviso-motivo">{a.motivo ?? 'Sem motivo escrito.'}</p>
                <p className="ind-data">{formatarDataEHora(a.em)}</p>
              </div>
              <button
                type="button"
                className="botao leve"
                disabled={resolvendo !== null}
                onClick={() => resolver(a.id)}
              >
                Resolver
              </button>
            </li>
          ))}
        </ul>
      )}
      {anuncio.escondido ? (
        <p className="ajuda">Este anúncio saiu da lista. O apartamento que anunciou só pode encerrá-lo.</p>
      ) : (
        <Confirmar
          id="cla-esconder"
          acao="Esconder este anúncio"
          explicacao="Ele sai da lista e não volta. O apartamento que anunciou vê o aviso e só pode encerrá-lo."
          executar={async () => {
            await esconderAnuncio(anuncio.id)
            recado('Anúncio escondido da lista.')
            recarregar()
          }}
        />
      )}
    </section>
  )
}
