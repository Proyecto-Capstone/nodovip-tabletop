import { useEffect, useState } from 'react'
import { api, ApiError } from '../api/client'

interface Estado<T> {
  clave: string
  datos?: T
  errores?: string[]
  status?: number
}

/**
 * Carga datos con GET. `ruta` en null significa "todavía no cargar".
 * `recargar()` vuelve a pedir la misma ruta (por ejemplo, después de publicar).
 */
export function useGet<T>(ruta: string | null, dependencia = '') {
  const [version, setVersion] = useState(0)
  const [estado, setEstado] = useState<Estado<T>>({ clave: '' })
  const clave = ruta === null ? '' : `${ruta}|${dependencia}|${version}`

  useEffect(() => {
    if (ruta === null) return
    let vigente = true
    api<T>(ruta).then(
      (datos) => {
        if (vigente) setEstado({ clave, datos })
      },
      (error: unknown) => {
        if (!vigente) return
        if (error instanceof ApiError) {
          setEstado({ clave, errores: error.errores, status: error.status })
        } else {
          setEstado({ clave, errores: ['No se pudo conectar con el servidor'] })
        }
      },
    )
    return () => {
      vigente = false
    }
  }, [ruta, clave])

  const actual = estado.clave === clave
  return {
    datos: actual ? estado.datos : undefined,
    errores: actual ? estado.errores : undefined,
    status: actual ? estado.status : undefined,
    cargando: ruta !== null && !actual,
    recargar: () => setVersion((v) => v + 1),
  }
}

/** Espera `ms` antes de devolver el valor (para no consultar en cada tecla). */
export function useDebounce<T>(valor: T, ms = 300): T {
  const [demorado, setDemorado] = useState(valor)
  useEffect(() => {
    const id = setTimeout(() => setDemorado(valor), ms)
    return () => clearTimeout(id)
  }, [valor, ms])
  return demorado
}
