// Classificados · o anúncio aberto (spec, seção 3.2): as fotos, o tipo e o preço, o título, a
// categoria, a descrição, a placa e a data; "Chamar no WhatsApp" com a mensagem pronta (o fixo
// ganha "Ligar", como nas indicações); o que o dono faz; "Tem algo errado aqui?"; e a seção da
// gestão.
import { Link, useParams } from 'react-router'
import { useCarga } from '../avisos/carregar'
import { Carregando, FalhaAoCarregar } from '../avisos/componentes'
import { formatarData } from '../casca/formatar'
import { Icone } from '../casca/Icone'
import { Placa } from '../casca/Placa'
import { Tela } from '../casca/Tela'
import { AvisarGestao } from '../indicacoes/AvisarGestao'
import { linkTelefone, partesDoTelefone } from '../indicacoes/formatos'
import { AcoesDoDono } from './AcoesDoDono'
import { abrirAnuncio, avisarGestao } from './api'
import { CAMINHO_CLASSIFICADOS } from './caminhos'
import { FotosDoAnuncio } from './Fotos'
import { haQuanto, linkWhatsAppDoAnuncio, seloDoTipo, textoDoMotivo } from './formatos'
import { ParaAGestao } from './ParaAGestao'
import type { Anuncio } from './tipos'
import '../indicacoes/indicacoes.css'
import './classificados.css'

function useIdDoAnuncio(): number | null {
  const { id } = useParams()
  return id && /^\d{1,15}$/.test(id) ? Number(id) : null
}

export function PaginaAnuncio() {
  const id = useIdDoAnuncio()
  const [carga, recarregar, trocar] = useCarga(
    () => (id === null ? Promise.reject(new Error('link quebrado')) : abrirAnuncio(id)),
    [id],
  )
  const anuncio = carga.dados
  return (
    <Tela titulo="Anúncio" tituloDaAba={anuncio?.titulo} voltar={CAMINHO_CLASSIFICADOS}>
      {carga.situacao === 'erro' && !anuncio ? (
        <>
          <FalhaAoCarregar mensagem={carga.erro.mensagem} tentar={recarregar} />
          <p>
            <Link className="texto-link" to={CAMINHO_CLASSIFICADOS}>
              Ver todos os anúncios
            </Link>
          </p>
        </>
      ) : !anuncio ? (
        <Carregando />
      ) : (
        <Conteudo anuncio={anuncio} recarregar={recarregar} trocar={trocar} />
      )}
    </Tela>
  )
}

function Numero({ digitos }: { digitos: string }) {
  const [ddd, resto] = partesDoTelefone(digitos)
  return (
    <>
      <span className="ind-numero">{ddd}</span> <span className="ind-numero">{resto}</span>
    </>
  )
}

/** O recado do topo para o dono e a gestão quando o anúncio saiu da lista. */
function Situacao({ anuncio }: { anuncio: Anuncio }) {
  let texto: string | null = null
  if (anuncio.escondido) {
    texto = anuncio.meu
      ? 'A gestão escondeu este anúncio. Ele não aparece para os vizinhos e só pode ser encerrado.'
      : 'Escondido da lista pela gestão.'
  } else if (anuncio.situacao === 'encerrado' && anuncio.motivo_encerramento) {
    texto = `Anúncio encerrado (${textoDoMotivo(anuncio.motivo_encerramento).toLowerCase()}). Ele é apagado em 7 dias, com as fotos.`
  } else if (anuncio.vencido) {
    texto = anuncio.meu
      ? `Este anúncio venceu em ${formatarData(anuncio.vence_em)} e saiu da lista. Renove para ele voltar por mais 30 dias.`
      : `Venceu em ${formatarData(anuncio.vence_em)} e saiu da lista.`
  } else if (anuncio.meu) {
    texto = `Fica na lista até ${formatarData(anuncio.vence_em)}.`
  }
  if (!texto) return null
  const fora = anuncio.escondido || anuncio.vencido || anuncio.situacao === 'encerrado'
  return (
    <div className={fora ? 'aviso-caixa atencao' : 'aviso-caixa info'}>
      <Icone nome={fora ? 'alerta' : 'relogio'} />
      <p>{texto}</p>
    </div>
  )
}

interface PropsConteudo {
  anuncio: Anuncio
  recarregar: () => void
  trocar: (a: Anuncio) => void
}

function Conteudo({ anuncio, recarregar, trocar }: PropsConteudo) {
  const visivel = !anuncio.escondido && !anuncio.vencido && anuncio.situacao !== 'encerrado'
  return (
    <>
      <Situacao anuncio={anuncio} />
      <FotosDoAnuncio fotos={anuncio.fotos} titulo={anuncio.titulo} />
      <section className="cla-cabeca" aria-labelledby="cla-titulo">
        <p className="cla-selos">
          <span className={`cla-tipo cla-tipo-${anuncio.tipo}`}>
            {seloDoTipo(anuncio.tipo, anuncio.preco_centavos)}
          </span>
          {anuncio.situacao === 'reservado' && <span className="selo cla-situacao cla-reservado">Reservado</span>}
        </p>
        <h2 id="cla-titulo" className="cla-titulo">
          {anuncio.titulo}
        </h2>
        <p className="cla-categoria">{anuncio.categoria.nome}</p>
        {anuncio.descricao && <p className="cla-descricao">{anuncio.descricao}</p>}
        <p className="cla-quem">
          <Placa unidade={anuncio.unidade} />
          <span>
            Anunciado {haQuanto(anuncio.renovado_em ?? anuncio.publicado_em)}
            {anuncio.renovado_em ? ' (renovado)' : ''}
          </span>
        </p>
      </section>

      {anuncio.meu ? (
        <p className="ajuda cla-seu-contato">
          Os vizinhos chamam você no <Numero digitos={anuncio.contato} />.
        </p>
      ) : (
        visivel && (
          <div className="ind-contatos">
            {!anuncio.celular && (
              <a className="botao ind-ligar" href={linkTelefone(anuncio.contato)}>
                Ligar: <Numero digitos={anuncio.contato} />
              </a>
            )}
            <a
              className={anuncio.celular ? 'botao ind-whatsapp' : 'botao leve ind-whatsapp'}
              href={linkWhatsAppDoAnuncio(anuncio.contato, anuncio.titulo)}
              target="_blank"
              rel="noopener noreferrer"
            >
              Chamar no WhatsApp
              <span className="cla-botao-numero">
                <Numero digitos={anuncio.contato} />
              </span>
            </a>
          </div>
        )
      )}

      {anuncio.meu && <AcoesDoDono anuncio={anuncio} trocar={trocar} />}

      {!anuncio.meu && visivel && (
        <div className="ind-rodape">
          <AvisarGestao
            prestadorId={anuncio.id}
            jaAvisei={anuncio.ja_avisei}
            aoAvisar={recarregar}
            oQue="este anúncio"
            enviar={(motivo) => avisarGestao(anuncio.id, { motivo })}
          />
        </div>
      )}

      {anuncio.avisos !== null && <ParaAGestao anuncio={anuncio} recarregar={recarregar} />}
    </>
  )
}
