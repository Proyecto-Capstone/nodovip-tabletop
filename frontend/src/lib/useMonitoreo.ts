// Monitoreo de sesiones activas (PC-24).
//
// useResumenMonitoreo: el panel con todas las sesiones EN_CURSO. Se
// refresca cada 5 s mientras la pestaña está visible; se detiene al
// ocultarla, para no gastar red ni CPU de fondo.
//
// useDetalleMonitoreo: el detalle de una sesión por WebSocket, con la
// misma estrategia de reconexión que useLeaderboard (espera creciente,
// pagehide/pageshow, sin reintentos ante un cierre definitivo del
// servidor).

import { useEffect, useState } from 'react'
import {
  CIERRE_DEFINITIVO,
  rutaSesionesMonitoreo,
  urlWebSocketMonitoreo,
  type DetalleMonitoreo,
  type ResumenMonitoreo,
} from '../api/monitoreo'
import { useGetVigente } from './useGet'

const INTERVALO_REFRESCO_MS = 5000
const ESPERA_MAXIMA_MS = 5000

export function useResumenMonitoreo(habilitado: boolean) {
  const [tick, setTick] = useState(0)

  useEffect(() => {
    if (!habilitado) return
    let id: ReturnType<typeof setInterval> | undefined
    const iniciar = () => {
      id ??= setInterval(() => setTick((t) => t + 1), INTERVALO_REFRESCO_MS)
    }
    const detener = () => {
      clearInterval(id)
      id = undefined
    }
    const alCambiarVisibilidad = () => {
      if (document.hidden) detener()
      else iniciar()
    }
    if (!document.hidden) iniciar()
    document.addEventListener('visibilitychange', alCambiarVisibilidad)
    return () => {
      detener()
      document.removeEventListener('visibilitychange', alCambiarVisibilidad)
    }
  }, [habilitado])

  return useGetVigente<ResumenMonitoreo>(
    habilitado ? rutaSesionesMonitoreo : null,
    String(tick),
  )
}

export type EstadoConexionMonitoreo = 'conectando' | 'conectado' | 'reconectando' | 'cerrado'

export function useDetalleMonitoreo(sesionId: string | undefined) {
  const [datos, setDatos] = useState<DetalleMonitoreo>()
  const [conexion, setConexion] = useState<EstadoConexionMonitoreo>('conectando')
  const [error, setError] = useState<string>()
  // Momento en que llegó el último detalle: el cronómetro avanza desde ahí.
  const [recibidaEn, setRecibidaEn] = useState(() => Date.now())

  useEffect(() => {
    if (!sesionId) return
    let socket: WebSocket | undefined
    let temporizador: ReturnType<typeof setTimeout> | undefined
    let intentos = 0
    let terminado = false

    const conectar = () => {
      socket = new WebSocket(urlWebSocketMonitoreo(sesionId))
      socket.onopen = () => {
        intentos = 0
        setConexion('conectado')
      }
      socket.onmessage = (mensaje) => {
        const mensajeDatos = JSON.parse(String(mensaje.data)) as {
          tipo: string
          datos: DetalleMonitoreo
        }
        if (mensajeDatos.tipo !== 'monitoreo') return
        setDatos(mensajeDatos.datos)
        setRecibidaEn(Date.now())
      }
      socket.onclose = (evento) => {
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

    // Igual que useEnVivo: Chrome puede guardar la página con el socket
    // abierto en la caché de navegación (bfcache).
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

  return { datos, conexion, error, recibidaEn }
}

/** Segundos transcurridos de una sesión EN_CURSO que avanzan solos. */
export function useTiempoTranscurrido(fila: { segundos_transcurridos: number; pausada: boolean } | undefined, recibidaEn: number) {
  const [ahora, setAhora] = useState(() => Date.now())
  const corriendo = fila !== undefined && !fila.pausada
  useEffect(() => {
    if (!corriendo) return
    const id = setInterval(() => setAhora(Date.now()), 1000)
    return () => clearInterval(id)
  }, [corriendo])
  if (!fila) return 0
  const extra = corriendo ? Math.max(0, Math.floor((ahora - recibidaEn) / 1000)) : 0
  return fila.segundos_transcurridos + extra
}
