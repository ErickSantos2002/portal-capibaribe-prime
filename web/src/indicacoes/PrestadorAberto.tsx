// Indicações · o prestador aberto (spec, seção 3.2): categoria, nome, contagens, contatos
// (WhatsApp sempre; "Ligar" quando o número é fixo; Instagram), a minha opinião, o que os
// vizinhos disseram (com a placa, nunca o nome), avisar a gestão e corrigir os dados.
import { useState, type ReactNode } from 'react'
import { Link, useLocation, useParams, useSearchParams } from 'react-router'
import { useCarga } from '../avisos/carregar'
import { Carregando, FalhaAoCarregar } from '../avisos/componentes'
import { formatarData } from '../casca/formatar'
import { Icone } from '../casca/Icone'
import { Placa } from '../casca/Placa'
import { Tela } from '../casca/Tela'
import { abrirIndicacao } from './api'
import { AvisarGestao } from './AvisarGestao'
import { CAMINHO_INDICACOES } from './caminhos'
import { CorrigirPrestador } from './CorrigirPrestador'
import { Contagens } from './Contagens'
import { FormOpiniao } from './FormOpiniao'
import { rascunhoDoEstado } from './formulario'
import { EsconderOpiniao, ParaAGestao } from './ParaAGestao'
import { linkInstagram, linkTelefone, linkWhatsApp, partesDoTelefone } from './formatos'
import type { Opiniao, Prestador } from './tipos'
import { useDevolverFoco } from './useDevolverFoco'
import './indicacoes.css'

function useIdDaIndicacao(): number | null {
  const { id } = useParams()
  return id && /^\d{1,15}$/.test(id) ? Number(id) : null
}

export function PaginaIndicacao() {
  const id = useIdDaIndicacao()
  const [carga, recarregar, trocar] = useCarga(
    () =>
      id === null
        ? Promise.reject(new Error('link quebrado'))
        : abrirIndicacao(id),
    [id],
  )
  const prestador = carga.dados
  return (
    <Tela titulo="Indicação" tituloDaAba={prestador?.nome} voltar={CAMINHO_INDICACOES}>
      {carga.situacao === 'erro' && !prestador ? (
        <>
          <FalhaAoCarregar mensagem={carga.erro.mensagem} tentar={recarregar} />
          <p>
            <Link className="texto-link" to={CAMINHO_INDICACOES}>
              Ver todas as indicações
            </Link>
          </p>
        </>
      ) : !prestador ? (
        <Carregando />
      ) : (
        <Conteudo prestador={prestador} recarregar={recarregar} trocar={trocar} />
      )}
    </Tela>
  )
}

interface PropsConteudo {
  prestador: Prestador
  recarregar: () => void
  trocar: (p: Prestador) => void
}

function Conteudo({ prestador, recarregar, trocar }: PropsConteudo) {
  const [consulta] = useSearchParams()
  const { state } = useLocation()
  const minha = prestador.minha_opiniao
  const podeOpinar = !prestador.escondido && !minha?.escondida
  const [opinando, setOpinando] = useState(podeOpinar && consulta.get('opinar') === '1')
  const [corrigindo, setCorrigindo] = useState(false)
  // Aberto por um toque (e não junto com a página): o foco vai ao título do formulário.
  const [tocou, setTocou] = useState(false)
  // Fechou (Cancelar, salvou, apagou): o foco volta ao botão que abriu.
  const botaoOpinar = useDevolverFoco<HTMLButtonElement>(opinando)
  const botaoCorrigir = useDevolverFoco<HTMLButtonElement>(corrigindo)
  // O que a pessoa escreveu em "Indicar alguém" antes de descobrir que ele já estava na lista.
  const rascunho = minha ? null : rascunhoDoEstado(state)

  return (
    <>
      <section className="ind-cabeca" aria-labelledby="ind-nome">
        <p className="ind-categoria">{prestador.categoria.nome}</p>
        {prestador.escondido && <p className="selo ind-escondido">Escondido da lista</p>}
        <h2 id="ind-nome" className="ind-nome">
          {prestador.nome}
        </h2>
        <p className="ind-contagens">
          <Contagens
            recomendam={prestador.recomendam}
            naoRecomendam={prestador.nao_recomendam}
            comPolegarNoNao
          />
        </p>
      </section>

      {/* Celular: o WhatsApp é o principal. Fixo: "Ligar" é o principal e o WhatsApp fica leve
          (fixo pode ter WhatsApp Business, então não some). */}
      <div className="ind-contatos">
        {!prestador.celular && (
          <a className="botao ind-ligar" href={linkTelefone(prestador.telefone)}>
            Ligar: <Numero digitos={prestador.telefone} />
          </a>
        )}
        <a
          className={prestador.celular ? 'botao ind-whatsapp' : 'botao leve ind-whatsapp'}
          href={linkWhatsApp(prestador.telefone)}
          target="_blank"
          rel="noopener noreferrer"
        >
          WhatsApp: <Numero digitos={prestador.telefone} />
        </a>
        {prestador.instagram && (
          <a
            className="texto-link"
            href={linkInstagram(prestador.instagram)}
            target="_blank"
            rel="noopener noreferrer"
          >
            Instagram: @{prestador.instagram}
          </a>
        )}
      </div>

      {minha?.escondida ? (
        <div className="aviso-caixa info">
          <Icone nome="info" />
          <p>A gestão escondeu a sua opinião. Ela não aparece para os vizinhos e não pode ser mudada nem apagada.</p>
        </div>
      ) : (
        podeOpinar &&
        (opinando ? (
          <FormOpiniao
            prestadorId={prestador.id}
            inicial={minha}
            rascunho={rascunho}
            focarAoAbrir={tocou}
            aoSalvar={(novo) => {
              trocar(novo)
              setOpinando(false)
            }}
            aoApagar={() => {
              setOpinando(false)
              recarregar()
            }}
            aoCancelar={() => setOpinando(false)}
          />
        ) : (
          <button
            type="button"
            className="botao"
            ref={botaoOpinar}
            onClick={() => {
              setTocou(true)
              setOpinando(true)
            }}
          >
            <Icone nome="editar" /> {minha ? 'Mudar a minha opinião' : 'Dar a minha opinião'}
          </button>
        ))
      )}

      <section className="ind-opinioes" aria-labelledby="ind-disseram">
        <h2 id="ind-disseram" className="secao">
          O que os vizinhos disseram
        </h2>
        {prestador.opinioes.length === 0 ? (
          <p className="vazio">Ainda não tem opinião aqui.</p>
        ) : (
          <ul className="folha ind-lista-opinioes">
            {prestador.opinioes.map((o) => (
              <ItemOpiniao
                key={o.id}
                opiniao={o}
                esconder={
                  prestador.avisos !== null && !prestador.escondido ? (
                    <EsconderOpiniao opiniaoId={o.id} recarregar={recarregar} />
                  ) : null
                }
              />
            ))}
          </ul>
        )}
      </section>

      <div className="ind-rodape">
        {!prestador.escondido && (
          <AvisarGestao prestadorId={prestador.id} jaAvisei={prestador.ja_avisei} aoAvisar={recarregar} />
        )}
        {prestador.pode_corrigir &&
          !prestador.escondido &&
          (corrigindo ? (
            <CorrigirPrestador
              prestador={prestador}
              aoCorrigir={(novo) => {
                trocar(novo)
                setCorrigindo(false)
              }}
              aoCancelar={() => setCorrigindo(false)}
            />
          ) : (
            <button
              type="button"
              className="botao leve"
              ref={botaoCorrigir}
              onClick={() => setCorrigindo(true)}
            >
              <Icone nome="editar" /> Corrigir os dados
            </button>
          ))}
      </div>

      {/* Só a gestão recebe `avisos` (para o morador, vem nulo). */}
      {prestador.avisos !== null && <ParaAGestao prestador={prestador} recarregar={recarregar} />}
    </>
  )
}

/** O número com o DDD; cada parte não quebra no meio (no máximo, o DDD fica numa linha). */
function Numero({ digitos }: { digitos: string }) {
  const [ddd, resto] = partesDoTelefone(digitos)
  return (
    <>
      <span className="ind-numero">{ddd}</span> <span className="ind-numero">{resto}</span>
    </>
  )
}

function ItemOpiniao({ opiniao, esconder }: { opiniao: Opiniao; esconder: ReactNode }) {
  return (
    <li className="ind-opiniao">
      <Placa unidade={opiniao.unidade} />
      <div>
        <p className={opiniao.recomenda ? 'ind-recomendam' : 'ind-nao-recomendam'}>
          <span aria-hidden="true">{opiniao.recomenda ? '👍 ' : '👎 '}</span>
          {opiniao.recomenda ? 'Recomenda' : 'Não recomenda'}
          <span className="ind-data"> · {formatarData(opiniao.em)}</span>
        </p>
        {opiniao.minha && <p className="selo ind-sua">Sua opinião</p>}
        {opiniao.comentario && <p className="ind-comentario">{opiniao.comentario}</p>}
        {esconder}
      </div>
    </li>
  )
}
