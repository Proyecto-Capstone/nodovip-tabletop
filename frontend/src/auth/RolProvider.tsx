import { useState, type ReactNode } from 'react'
import { guardarRol, leerRolGuardado, type RolSistema } from '../api/client'
import { RolContext } from './rolContext'

// TEMPORAL hasta PB-01: el rol se elige en la barra superior en lugar de
// obtenerse del login.
export function RolProvider({ children }: { children: ReactNode }) {
  const [rol, setRol] = useState<RolSistema>(leerRolGuardado)

  const cambiarRol = (nuevo: RolSistema) => {
    guardarRol(nuevo)
    setRol(nuevo)
  }

  return (
    <RolContext.Provider
      value={{
        rol,
        cambiarRol,
        esAdministrador: rol === 'administrador',
        puedeLeerEscenarios: rol === 'administrador' || rol === 'moderador',
      }}
    >
      {children}
    </RolContext.Provider>
  )
}
