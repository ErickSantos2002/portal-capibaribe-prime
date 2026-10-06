// Ícones do protótipo: SVG de traço único (2 px), um estilo só, sempre ao lado de texto.
// O desenho de cada um é constante do código (nunca dado de fora), por isso o innerHTML é seguro.

const DESENHOS = {
  avisos:
    '<path d="M4 10v4a1 1 0 0 0 1 1h2l6 4V5L7 9H5a1 1 0 0 0-1 1z"/><path d="M16.5 8.5a5 5 0 0 1 0 7"/><path d="M19 6a8.5 8.5 0 0 1 0 12"/>',
  enquetes: '<rect x="3.5" y="3.5" width="17" height="17" rx="3"/><path d="M8 12.5l3 3 5.5-6.5"/>',
  documentos:
    '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h4"/>',
  casa: '<path d="M3.5 11 12 4l8.5 7"/><path d="M5.5 9.5V20h13V9.5"/><path d="M10 20v-5.5h4V20"/>',
  painel:
    '<rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/>',
  voltar: '<path d="M15 18l-6-6 6-6"/>',
  sol: '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M4.6 4.6l1.4 1.4M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4 6 18M18 6l1.4-1.4"/>',
  lua: '<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/>',
  seta: '<path d="M9 6l6 6-6 6"/>',
  pino: '<path d="M12 16v5"/><path d="M8.5 3.5h7l-1 5.5 3 3.5h-11l3-3.5z"/>',
  olho: '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="3"/>',
  busca: '<circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4.2-4.2"/>',
  sino: '<path d="M6 9.5a6 6 0 0 1 12 0c0 6.5 2.5 8 2.5 8h-17S6 16 6 9.5"/><path d="M10 20.5a2 2 0 0 0 4 0"/>',
  celular: '<rect x="7" y="2.5" width="10" height="19" rx="2"/><path d="M11 18h2"/>',
  monitor: '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
  cadeado: '<rect x="5" y="11" width="14" height="9.5" rx="2"/><path d="M8 11V7.5a4 4 0 0 1 8 0V11"/>',
  sair: '<path d="M14.5 4H19v16h-4.5"/><path d="M10 8l-4 4 4 4M6 12h9.5"/>',
  relogio: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
  mais: '<path d="M12 5v14M5 12h14"/>',
  certo: '<path d="M5 12.5l4.5 4.5L19 7"/>',
  alerta: '<path d="M12 3.5 21 19.5H3z"/><path d="M12 10v4.5M12 17.2v.1"/>',
  info: '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.5M12 7.8v.1"/>',
  editar: '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/>',
  arquivar:
    '<rect x="3.5" y="4" width="17" height="4.5" rx="1"/><path d="M5 8.5V19a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8.5M10 12.5h4"/>',
  // Categorias e evento dos avisos (spec dos avisos com formatação, seção 3.4).
  obra: '<path d="M2.5 20h19"/><path d="M5 20V9.5l7-5 7 5V20"/><path d="M10 20v-6h4v6"/>',
  reuniao:
    '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7"/><path d="M18 14a6.5 6.5 0 0 1 3.5 6"/>',
  financeiro:
    '<rect x="2.5" y="6" width="19" height="13" rx="2"/><path d="M2.5 10h19M16 15h2"/>',
  calendario: '<rect x="3.5" y="5" width="17" height="15.5" rx="2"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
  local:
    '<path d="M12 21s7-6.2 7-11a7 7 0 0 0-14 0c0 4.8 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/>',
  // Barra de formatação do texto do aviso.
  titulo: '<path d="M6 4.5v15M18 4.5v15M6 12h12"/>',
  negrito: '<path d="M7 4.5h6a3.75 3.75 0 0 1 0 7.5H7zM7 12h7a3.75 3.75 0 0 1 0 7.5H7z"/>',
  lista: '<path d="M9.5 6.5H20M9.5 12H20M9.5 17.5H20"/><path d="M4.5 6.5v.1M4.5 12v.1M4.5 17.5v.1"/>',
} as const

export type NomeDoIcone = keyof typeof DESENHOS

interface Props {
  nome: NomeDoIcone
  tamanho?: number
  /** Texto para leitor de tela. Sem rótulo, o ícone é decorativo (aria-hidden). */
  rotulo?: string
}

export function Icone({ nome, tamanho = 24, rotulo }: Props) {
  return (
    <svg
      width={tamanho}
      height={tamanho}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...(rotulo ? { role: 'img', 'aria-label': rotulo } : { 'aria-hidden': true })}
      dangerouslySetInnerHTML={{ __html: DESENHOS[nome] }}
    />
  )
}
