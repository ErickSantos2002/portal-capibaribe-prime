// Épico B do M4 · o cartão "Ir para a enquete" do aviso automático (H-13; spec do M4, seção 4).
// Pertence ao épico B. Encaixado em `avisos/AvisoAberto.tsx`, depois do botão do documento. A
// API só manda a `enquete` se a unidade pode vê-la (mesmo destino do aviso).
import { Link } from 'react-router'
import type { EnqueteDoAviso as Dados } from '../../avisos/tipos'
import { Icone } from '../../casca/Icone'
import { caminhoEnquete } from '../caminhos'
import { quandoTermina } from './formatos'
import './enquetes.css'

export function EnqueteDoAviso({ enquete }: { enquete: Dados | null }) {
  if (!enquete) return null
  return (
    <Link className="enq-do-aviso" to={caminhoEnquete(enquete.id)}>
      <Icone nome="enquetes" tamanho={32} />
      <span>
        <b>Ir para a enquete</b>
        <span className="enq-do-aviso-pergunta">{enquete.pergunta}</span>
        {/* Ajustes do M4, ponto 11: o aviso fica no mural depois do fim; o cartão diz o estado. */}
        <span className="enq-do-aviso-estado">
          {enquete.encerrada
            ? 'Terminou · ver o resultado'
            : `Aberta · vai até ${quandoTermina(enquete.encerra_em)}`}
        </span>
      </span>
      <Icone nome="seta" />
    </Link>
  )
}
