// Classificados · "Meus anúncios" (spec, seção 3.1): todos os da unidade enquanto existem (os
// abertos, os vencidos, que dá para renovar, e os encerrados dos últimos 7 dias), na ordem da API.
import { Link } from 'react-router'
import { useCarga } from '../avisos/carregar'
import { Carregando, FalhaAoCarregar } from '../avisos/componentes'
import { Icone } from '../casca/Icone'
import { Tela } from '../casca/Tela'
import { meusAnuncios } from './api'
import { CAMINHO_CLASSIFICADOS, CAMINHO_NOVO_ANUNCIO } from './caminhos'
import { Cartao } from './Cartao'
import '../indicacoes/indicacoes.css'
import './classificados.css'

export function PaginaMeusAnuncios() {
  const [carga, recarregar] = useCarga(() => meusAnuncios(), [])
  const itens = carga.dados?.itens
  return (
    <Tela titulo="Meus anúncios" voltar={CAMINHO_CLASSIFICADOS}>
      <p className="ajuda">
        O anúncio vence em 30 dias e sai da lista sozinho; dá para renovar. O encerrado fica aqui
        por 7 dias e depois é apagado, com as fotos.
      </p>
      {carga.situacao === 'erro' && !itens ? (
        <FalhaAoCarregar mensagem={carga.erro.mensagem} tentar={recarregar} />
      ) : !itens ? (
        <Carregando />
      ) : itens.length === 0 ? (
        <div className="ind-vazio">
          <p className="vazio">Você ainda não anunciou nada.</p>
          <Link className="botao" to={CAMINHO_NOVO_ANUNCIO}>
            <Icone nome="mais" /> Anunciar
          </Link>
        </div>
      ) : (
        <div className="folha cla-lista">
          {itens.map((a) => (
            <Cartao key={a.id} anuncio={a} mostrarPlaca={false} />
          ))}
        </div>
      )}
    </Tela>
  )
}
