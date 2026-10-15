// H-21 · Enquetes: "Abertas" (a que termina antes no topo) e "Terminadas", com o selo "Seu
// apartamento ainda não votou". A ordem vem da API.
import { Link } from 'react-router'
import type { Eu } from '../../api/tipos'
import { useCarga } from '../../avisos/carregar'
import { Carregando, FalhaAoCarregar } from '../../avisos/componentes'
import { destinoEmTexto } from '../../avisos/formatos'
import { useSessao } from '../../casca/contextoSessao'
import { Icone } from '../../casca/Icone'
import { Tela } from '../../casca/Tela'
import { listarEnquetes } from '../api'
import { CAMINHO_NOVA_ENQUETE, caminhoEnquete } from '../caminhos'
import type { EnqueteResumo } from '../tipos'
import { noDestino, quandoTermina } from './formatos'
import './enquetes.css'

export function ListaEnquetes() {
  const { eu } = useSessao()
  const [carga, recarregar] = useCarga(() => listarEnquetes(), [])
  const itens = carga.dados?.itens

  const nova = eu?.gestao && (
    <Link className="flutuante" to={CAMINHO_NOVA_ENQUETE}>
      <Icone nome="mais" /> Nova enquete
    </Link>
  )

  return (
    <Tela titulo="Enquetes" extra={nova}>
      {carga.situacao === 'erro' && !itens ? (
        <FalhaAoCarregar mensagem={carga.erro.mensagem} tentar={recarregar} />
      ) : !itens || !eu ? (
        <Carregando />
      ) : (
        <>
          <Grupo
            id="enq-abertas"
            titulo="Abertas"
            vazio="Nenhuma enquete aberta agora."
            itens={itens.filter((e) => !e.encerrada)}
            eu={eu}
          />
          <Grupo
            id="enq-terminadas"
            titulo="Terminadas"
            vazio="Nenhuma enquete terminou ainda."
            itens={itens.filter((e) => e.encerrada)}
            eu={eu}
          />
        </>
      )}
    </Tela>
  )
}

interface PropsGrupo {
  id: string
  titulo: string
  vazio: string
  itens: EnqueteResumo[]
  eu: Eu
}

function Grupo({ id, titulo, vazio, itens, eu }: PropsGrupo) {
  return (
    <section className="enq-grupo" aria-labelledby={id}>
      <h2 className="secao" id={id}>
        {titulo}
      </h2>
      {itens.length === 0 ? (
        <p className="vazio">{vazio}</p>
      ) : (
        <div className="folha">
          {itens.map((e) => (
            <ItemEnquete key={e.id} enquete={e} eu={eu} />
          ))}
        </div>
      )}
    </section>
  )
}

function ItemEnquete({ enquete, eu }: { enquete: EnqueteResumo; eu: Eu }) {
  const vota = noDestino(enquete, eu.unidade.bloco)
  const falta = !enquete.encerrada && vota && !enquete.ja_votou
  return (
    <Link className={falta ? 'item novo' : 'item'} to={caminhoEnquete(enquete.id)}>
      <h3>{enquete.pergunta}</h3>
      <span className="seta">
        <Icone nome="seta" />
      </span>
      <span className="linha-meta">
        {falta && <span className="selo enq-falta">Seu apartamento ainda não votou</span>}
        {!enquete.encerrada && vota && enquete.ja_votou && (
          <span className="com-icone enq-votou">
            <Icone nome="certo" tamanho={18} /> Seu apartamento já votou
          </span>
        )}
        <span>
          {enquete.encerrada ? 'Terminou em' : 'Vai até'} {quandoTermina(enquete.encerra_em)}
        </span>
        {eu.gestao && !enquete.para_todos && <span>Para {destinoEmTexto(enquete)}</span>}
      </span>
    </Link>
  )
}
