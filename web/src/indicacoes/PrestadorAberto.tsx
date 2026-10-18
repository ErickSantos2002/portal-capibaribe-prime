// Indicações · o prestador aberto (spec, seção 3.2): categoria, nome, contagens, contatos
// (WhatsApp sempre; "Ligar" quando o número é fixo; Instagram), a minha opinião, o que os
// vizinhos disseram (com a placa, nunca o nome), avisar a gestão e corrigir os dados.
import { useState, type ReactNode } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'
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
import { FormOpiniao } from './FormOpiniao'
import { EsconderOpiniao, ParaAGestao } from './ParaAGestao'
import {
  linkInstagram,
  linkTelefone,
  linkWhatsApp,
  naoRecomendamEmTexto,
  recomendamEmTexto,
  telefoneNaTela,
} from './formatos'
import type { Opiniao, Prestador } from './tipos'
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
  const minha = prestador.minha_opiniao
  const podeOpinar = !prestador.escondido && !minha?.escondida
  const [opinando, setOpinando] = useState(podeOpinar && consulta.get('opinar') === '1')
  const [corrigindo, setCorrigindo] = useState(false)

  return (
    <>
      <section className="ind-cabeca" aria-labelledby="ind-nome">
        <p className="ind-categoria">{prestador.categoria.nome}</p>
        {prestador.escondido && <p className="selo ind-escondido">Escondido da lista</p>}
        <h2 id="ind-nome" className="ind-nome">
          {prestador.nome}
        </h2>
        <p className="ind-contagens">
          <span className="ind-recomendam">
            <span aria-hidden="true">👍 </span>
            {recomendamEmTexto(prestador.recomendam)}
          </span>
          {prestador.nao_recomendam > 0 && (
            <span className="ind-nao-recomendam">
              <span aria-hidden="true">👎 </span>
              {naoRecomendamEmTexto(prestador.nao_recomendam)}
            </span>
          )}
        </p>
      </section>

      <div className="ind-contatos">
        <a
          className="botao ind-whatsapp"
          href={linkWhatsApp(prestador.telefone)}
          target="_blank"
          rel="noopener noreferrer"
        >
          WhatsApp: {telefoneNaTela(prestador.telefone)}
        </a>
        {!prestador.celular && (
          <a className="botao leve" href={linkTelefone(prestador.telefone)}>
            Ligar
          </a>
        )}
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
          <button type="button" className="botao" onClick={() => setOpinando(true)}>
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
            <button type="button" className="botao leve" onClick={() => setCorrigindo(true)}>
              <Icone nome="editar" /> Corrigir os dados
            </button>
          ))}
      </div>

      {/* Só a gestão recebe `avisos` (para o morador, vem nulo). */}
      {prestador.avisos !== null && <ParaAGestao prestador={prestador} recarregar={recarregar} />}
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
          {opiniao.minha && <span className="ind-sua"> · a sua</span>}
          <span className="ind-data"> · {formatarData(opiniao.em)}</span>
        </p>
        {opiniao.comentario && <p className="ind-comentario">{opiniao.comentario}</p>}
        {esconder}
      </div>
    </li>
  )
}
