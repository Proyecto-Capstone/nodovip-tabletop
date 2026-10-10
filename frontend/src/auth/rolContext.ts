import { createContext, useContext } from 'react'
import type { RolSistema } from '../api/client'

export interface RolContextValor {
  rol: RolSistema
  cambiarRol: (rol: RolSistema) => void
  esAdministrador: boolean
  puedeLeerEscenarios: boolean
}

export const RolContext = createContext<RolContextValor | null>(null)

export function useRol(): RolContextValor {
  const valor = useContext(RolContext)
  if (!valor) throw new Error('useRol debe usarse dentro de RolProvider')
  return valor
}

export const ROLES_SISTEMA: { codigo: RolSistema; nombre: string }[] = [
  { codigo: 'administrador', nombre: 'Administrador' },
  { codigo: 'moderador', nombre: 'Moderador' },
  { codigo: 'participante', nombre: 'Participante' },
  { codigo: 'observador', nombre: 'Observador' },
  { codigo: 'analista', nombre: 'Analista' },
]
