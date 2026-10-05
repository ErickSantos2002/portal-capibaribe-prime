// H-16 · Saber quem leu: "X leram, Y ainda não" e os apartamentos que não leram, por bloco.
import { Link } from 'react-router'
import { useRecado } from '../casca/contextoRecado'
import { useSessao } from '../casca/contextoSessao'
import { NaoEncontrado } from '../casca/guardas'
import { Tela } from '../casca/Tela'
import type { UnidadeRef } from '../api/tipos'
import { abrirAviso, buscarLeitura } from './api'
import { useCarga, useIdDoAviso } from './carregar'
import { Carregando, FalhaAoCarregar } from './componentes'
import { listaParaCopiar } from './formatos'
import './avisos.css'

export function PaginaQuemLeu() {
  const id = useIdDoAviso()
  return id === null ? <NaoEncontrado /> : <QuemLeu key={id} id={id} />
}

function QuemLeu({ id }: { id: number }) {
  const [carga, recarregar] = useCarga(() => Promise.all([abrirAviso(id), buscarLeitura(id)]), [id])
  if (carga.situacao === 'erro' && carga.erro.status === 404) return <NaoEncontrado />
  return (
    <Tela titulo="Quem leu" voltar={`/avisos/${id}`}>
      {carga.situacao === 'erro' ? (
        <FalhaAoCarregar mensagem={carga.erro.mensagem} tentar={recarregar} />
      ) : carga.situacao === 'carregando' ? (
        <Carregando />
      ) : (
        <Conteudo titulo={carga.dados[0].titulo} leitura={carga.dados[1]} />
      )}
    </Tela>
  )
}

function porBloco(unidades: UnidadeRef[]): [number, UnidadeRef[]][] {
  const grupos = new Map<number, UnidadeRef[]>()
  for (const u of unidades) grupos.set(u.bloco, [...(grupos.get(u.bloco) ?? []), u])
  return [...grupos]
}

interface PropsConteudo {
  titulo: string
  leitura: { lidos: number; total: number; nao_leram: UnidadeRef[] }
}

function Conteudo({ titulo, leitura }: PropsConteudo) {
  const recado = useRecado()
  const { eu } = useSessao()
  const faltam = leitura.total - leitura.lidos

  async function copiar() {
    try {
      await navigator.clipboard.writeText(listaParaCopiar(titulo, leitura.nao_leram))
      recado('Lista copiada. Dá para colar no grupo.')
    } catch {
      recado('Não deu para copiar. Selecione os apartamentos e copie à mão.')
    }
  }

  return (
    <>
      <h2>{titulo}</h2>
      <div className="resumo avisos-resumo">
        <div>
          <b>{leitura.lidos}</b>
          {leitura.lidos === 1 ? 'leu' : 'leram'}
        </div>
        <div>
          <b>{faltam}</b>
          ainda não
        </div>
      </div>
      <p className="ajuda">
        Contam todos os apartamentos do destino, inclusive os que ainda não entraram no Portal.
      </p>
      {leitura.nao_leram.length === 0 ? (
        <div className="aviso-caixa info">
          <p>Todos os apartamentos do destino já leram.</p>
        </div>
      ) : (
        <>
          <h3 className="secao">Apartamentos que ainda não leram</h3>
          {porBloco(leitura.nao_leram).map(([bloco, unidades]) => (
            <section key={bloco} aria-labelledby={`nao-leram-${bloco}`}>
              <h4 className="avisos-bloco" id={`nao-leram-${bloco}`}>
                Bloco {bloco}
              </h4>
              <ul className="grade avisos-grade">
                {unidades.map((u) => (
                  <li key={u.login}>
                    {eu?.admin ? (
                      <Link
                        to={`/unidades/${u.login}`}
                        aria-label={`Bloco ${u.bloco}, apartamento ${u.apartamento}`}
                      >
                        {u.apartamento}
                      </Link>
                    ) : (
                      <span aria-label={`Bloco ${u.bloco}, apartamento ${u.apartamento}`}>
                        {u.apartamento}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          ))}
          <button type="button" className="botao leve avisos-copiar" onClick={() => void copiar()}>
            Copiar a lista
          </button>
        </>
      )}
    </>
  )
}
