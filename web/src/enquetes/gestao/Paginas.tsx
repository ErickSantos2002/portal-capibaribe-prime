// Épico A do M4 · as telas "Nova enquete" e "Editar enquete" (H-20). Pertence ao épico A.
// Editar carrega a enquete pela rota do épico B (`abrirEnquete`): é a mesma `Enquete` que a
// tela dela mostra, com `pode_editar` (gestão, aberta e sem voto).
import { Link } from 'react-router'
import { Carregando, FalhaAoCarregar } from '../../avisos/componentes'
import { Icone } from '../../casca/Icone'
import { Tela } from '../../casca/Tela'
import { useCarga } from '../../documentos/carregar'
import { abrirEnquete } from '../api'
import { CAMINHO_ENQUETES, caminhoEnquete } from '../caminhos'
import type { Enquete } from '../tipos'
import { EnqueteNaoEncontrada } from '../votar/EnqueteAberta'
import { useIdDaEnquete } from '../votar/useIdDaEnquete'
import { FormularioEnquete } from './Formulario'
import { deIso, RASCUNHO_VAZIO, type Rascunho } from './formatos'

export function NovaEnquete() {
  return (
    <Tela titulo="Nova enquete" voltar={CAMINHO_ENQUETES}>
      <FormularioEnquete modo={{ tipo: 'nova' }} inicial={RASCUNHO_VAZIO} />
    </Tela>
  )
}

function rascunhoDe(enquete: Enquete): Rascunho {
  return {
    pergunta: enquete.pergunta,
    opcoes: enquete.opcoes.map((o) => o.texto),
    multipla: enquete.multipla_escolha,
    ...deIso(enquete.encerra_em),
    mostrar: enquete.mostrar_resultado,
  }
}

// Ajustes do M4, ponto 5: a mesma regra de id e a mesma tela de "não encontrada" da enquete
// (épico B): `/enquetes/0/editar` não chama a API, e 404 ou 422 dela também caem aqui.
export function PaginaEditarEnquete() {
  const id = useIdDaEnquete()
  return id === null ? <EnqueteNaoEncontrada /> : <EditarEnquete key={id} id={id} />
}

function EditarEnquete({ id }: { id: number }) {
  const [carga, recarregar] = useCarga(() => abrirEnquete(id), [id])
  if (carga.situacao === 'erro' && carga.erro.status === 404) {
    return <EnqueteNaoEncontrada mensagem={carga.erro.mensagem} />
  }
  // 422: id fora do que o banco guarda; para quem abriu o link, é a enquete que não existe.
  if (carga.situacao === 'erro' && carga.erro.status === 422) return <EnqueteNaoEncontrada />
  const enquete = carga.situacao === 'pronta' ? carga.dados : null
  return (
    <Tela titulo="Editar enquete" voltar={caminhoEnquete(id)}>
      {carga.situacao === 'erro' ? (
        <FalhaAoCarregar mensagem={carga.erro.mensagem} tentar={recarregar} />
      ) : !enquete ? (
        <Carregando />
      ) : enquete.pode_editar ? (
        <FormularioEnquete
          // Versão nova carregada (outra pessoa editou): o formulário começa de novo com ela.
          key={enquete.editada_em ?? 'nunca'}
          modo={{
            tipo: 'editar',
            id,
            paraTodos: enquete.para_todos,
            blocos: enquete.blocos,
            editadaEm: enquete.editada_em,
            recarregar,
          }}
          inicial={rascunhoDe(enquete)}
        />
      ) : (
        <>
          <div className="aviso-caixa atencao" role="alert">
            <Icone nome="cadeado" />
            <p>
              {enquete.encerrada
                ? 'Esta enquete já terminou. Nada nela muda mais.'
                : 'A enquete já recebeu votos: a pergunta e as opções não podem mais mudar. É assim para ninguém mexer depois de ver como está a votação.'}
            </p>
          </div>
          <Link className="botao" to={caminhoEnquete(id)}>
            Ver a enquete
          </Link>
        </>
      )}
    </Tela>
  )
}
