// Épico B do M4 · o `:id` das telas de enquete. Pertence ao épico B.
import { useParams } from 'react-router'

/** O `:id` do endereço, ou nulo se não for um número (link quebrado). */
export function useIdDaEnquete(): number | null {
  const { id } = useParams()
  return id && /^[1-9]\d{0,14}$/.test(id) ? Number(id) : null
}
