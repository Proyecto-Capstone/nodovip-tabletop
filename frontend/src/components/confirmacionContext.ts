import { createContext, useContext } from 'react'

export interface OpcionesConfirmacion {
  titulo: string
  cuerpo?: string
  textoConfirmar?: string
  textoCancelar?: string
  /** `peligro` (por defecto) para acciones destructivas; `primario` para el resto. */
  variante?: 'peligro' | 'primario'
}

export type Confirmar = (opciones: OpcionesConfirmacion) => Promise<boolean>

export const ConfirmacionContext = createContext<Confirmar | null>(null)

export function useConfirmar(): Confirmar {
  const confirmar = useContext(ConfirmacionContext)
  if (!confirmar) {
    throw new Error('useConfirmar debe usarse dentro de ProveedorConfirmacion')
  }
  return confirmar
}
