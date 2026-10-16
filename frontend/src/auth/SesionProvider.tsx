import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import * as auth from '../api/auth'
import { avisarAlPerderSesion } from '../api/client'
import { SesionContext, valorSesion } from './sesionContext'

// PB-01: sesión real. Al abrir la app se pregunta al backend quién es el
// usuario (la cookie es httpOnly, así que el navegador no puede leerla).
export function SesionProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<auth.Sesion | null>(null)
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    let vigente = true
    auth
      .obtenerSesion()
      .then(
        (u) => vigente && setUsuario(u),
        () => vigente && setUsuario(null),
      )
      .finally(() => vigente && setCargando(false))
    const dejarDeAvisar = avisarAlPerderSesion(() => setUsuario(null))
    return () => {
      vigente = false
      dejarDeAvisar()
    }
  }, [])

  const iniciarSesion = useCallback(async (correo: string, contrasena: string) => {
    const u = await auth.iniciarSesion(correo, contrasena)
    setUsuario(u)
    return u
  }, [])

  const cerrarSesion = useCallback(async () => {
    try {
      await auth.cerrarSesion()
    } catch {
      // Sin red la cookie sigue en el navegador, pero se cierra igual en la
      // pantalla; vence sola (8 h) y el próximo logout la borra.
    }
    setUsuario(null)
  }, [])

  const valor = useMemo(
    () => valorSesion(usuario, { cargando, iniciarSesion, cerrarSesion }),
    [usuario, cargando, iniciarSesion, cerrarSesion],
  )

  return <SesionContext.Provider value={valor}>{children}</SesionContext.Provider>
}
