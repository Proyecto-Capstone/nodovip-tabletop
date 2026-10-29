// Conexión WebSocket a una sesión en vivo (PB-07), con reconexión automática.
// Al (re)conectarse, el servidor envía primero el estado completo: así quien
// pierde la conexión recupera la sesión donde va.

import { useEffect, useRef, useState } from 'react'
import { CIERRE_DEFINITIVO, urlWebSocket, type VistaEnVivo } from '../api/enVivo'

export type EstadoConexion = 'conectando' | 'conectado' | 'reconectando' | 'cerrado'

const ESPERA_MAXIMA_MS = 5000

export function useEnVivo(sesionId: string | undefined) {
  const [vista, setVista] = useState<VistaEnVivo>()
  const [conexion, setConexion] = useState<EstadoConexion>('conectando')
  const [error, setError] = useState<string>()
  // Momento en que llegó la vista: el cronómetro avanza a partir de ahí.
  const [recibidaEn, setRecibidaEn] = useState(() => Date.now())
  const ultimaVersion = useRef(-1)

  // Si se cambia de sesión, se reinicia el estado durante el render.
  const [sesionActual, setSesionActual] = useState(sesionId)
  if (sesionActual !== sesionId) {
    setSesionActual(sesionId)
    setVista(undefined)
    setConexion('conectando')
    setError(undefined)
  }

  useEffect(() => {
    if (!sesionId) return
    let socket: WebSocket | undefined
    let temporizador: ReturnType<typeof setTimeout> | undefined
    let intentos = 0
    let terminado = false
    ultimaVersion.current = -1

    const conectar = () => {
      socket = new WebSocket(urlWebSocket(sesionId))
      socket.onopen = () => {
        intentos = 0
        setConexion('conectado')
      }
      socket.onmessage = (mensaje) => {
        const datos = JSON.parse(String(mensaje.data)) as { tipo: string; vista: VistaEnVivo }
        if (datos.tipo !== 'estado') return
        // Los eventos de presencia repiten la versión; nunca se retrocede.
        if (datos.vista.version < ultimaVersion.current) return
        ultimaVersion.current = datos.vista.version
        setVista(datos.vista)
        setRecibidaEn(Date.now())
        if (datos.vista.estado === 'finalizada') terminado = true
      }
      socket.onclose = (evento) => {
        if (terminado) {
          setConexion('cerrado')
          return
        }
        const definitivo = CIERRE_DEFINITIVO[evento.code]
        if (definitivo) {
          terminado = true
          setError(definitivo)
          setConexion('cerrado')
          return
        }
        setConexion('reconectando')
        const espera = Math.min(ESPERA_MAXIMA_MS, 500 * 2 ** intentos)
        intentos += 1
        temporizador = setTimeout(conectar, espera)
      }
    }

    // Chrome guarda la página anterior en su caché de navegación (bfcache) con
    // el socket abierto: el servidor seguiría contando a la persona como
    // conectada. Se cierra al salir y se reconecta si vuelve con "atrás".
    const alOcultar = () => {
      clearTimeout(temporizador)
      if (socket) socket.onclose = null
      socket?.close()
    }
    const alMostrar = (evento: PageTransitionEvent) => {
      if (evento.persisted && !terminado) conectar()
    }
    window.addEventListener('pagehide', alOcultar)
    window.addEventListener('pageshow', alMostrar)

    conectar()
    return () => {
      terminado = true
      clearTimeout(temporizador)
      window.removeEventListener('pagehide', alOcultar)
      window.removeEventListener('pageshow', alMostrar)
      socket?.close()
    }
  }, [sesionId])

  return { vista, conexion, error, recibidaEn }
}

/** Segundos transcurridos que avanzan solos mientras la sesión corre. */
export function useCronometro(vista: VistaEnVivo | undefined, recibidaEn: number) {
  const [ahora, setAhora] = useState(() => Date.now())
  const corriendo = vista?.estado === 'en_curso' && !vista.pausada
  useEffect(() => {
    if (!corriendo) return
    const id = setInterval(() => setAhora(Date.now()), 1000)
    return () => clearInterval(id)
  }, [corriendo])
  if (!vista) return 0
  const extra = corriendo ? Math.max(0, Math.floor((ahora - recibidaEn) / 1000)) : 0
  return vista.segundos_transcurridos + extra
}

export function formatoReloj(segundos: number) {
  const h = Math.floor(segundos / 3600)
  const m = Math.floor((segundos % 3600) / 60)
  const s = segundos % 60
  const dos = (n: number) => String(n).padStart(2, '0')
  return `${dos(h)}:${dos(m)}:${dos(s)}`
}
