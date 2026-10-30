// Conexión WebSocket al leaderboard en vivo (PB-12), con la misma estrategia
// de reconexión que useEnVivo (espera creciente, pagehide/pageshow, sin
// reintentos ante un cierre definitivo del servidor).

import { useEffect, useState } from 'react'
import { CIERRE_DEFINITIVO, urlWebSocketLeaderboard, type Leaderboard } from '../api/leaderboard'

export type EstadoConexion = 'conectando' | 'conectado' | 'reconectando' | 'cerrado'

const ESPERA_MAXIMA_MS = 5000

export function useLeaderboard(sesionId: string | undefined) {
  const [datos, setDatos] = useState<Leaderboard>()
  const [conexion, setConexion] = useState<EstadoConexion>('conectando')
  const [error, setError] = useState<string>()
  // Momento en que llegó el último ranking: para "Actualizado hace X s".
  const [recibidaEn, setRecibidaEn] = useState(() => Date.now())

  const [sesionActual, setSesionActual] = useState(sesionId)
  if (sesionActual !== sesionId) {
    setSesionActual(sesionId)
    setDatos(undefined)
    setConexion('conectando')
    setError(undefined)
  }

  useEffect(() => {
    if (!sesionId) return
    let socket: WebSocket | undefined
    let temporizador: ReturnType<typeof setTimeout> | undefined
    let intentos = 0
    let terminado = false

    const conectar = () => {
      socket = new WebSocket(urlWebSocketLeaderboard(sesionId))
      socket.onopen = () => {
        intentos = 0
        setConexion('conectado')
      }
      socket.onmessage = (mensaje) => {
        const mensajeDatos = JSON.parse(String(mensaje.data)) as {
          tipo: string
          datos: Leaderboard
        }
        if (mensajeDatos.tipo !== 'leaderboard') return
        setDatos(mensajeDatos.datos)
        setRecibidaEn(Date.now())
        if (mensajeDatos.datos.sesion.estado === 'finalizada') terminado = true
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

/** Segundos desde que llegó el último ranking, para "Actualizado hace X s". */
export function useSegundosDesde(recibidaEn: number) {
  const [ahora, setAhora] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setAhora(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])
  return Math.max(0, Math.floor((ahora - recibidaEn) / 1000))
}
