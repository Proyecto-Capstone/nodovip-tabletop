// PC-44: avisa al participante cuando el moderador lanza un inject nuevo.
// - Devuelve el inject recién lanzado durante unos segundos (banner animado).
// - Toca un sonido corto (Web Audio, sin archivos) salvo que esté silenciado.
// - Si la pestaña está en segundo plano, el título parpadea hasta que vuelva.
// La primera vista que llega (al entrar o reconectar) no avisa: solo los cambios.

import { useCallback, useEffect, useRef, useState } from 'react'
import type { InjectEnVivo, VistaEnVivo } from '../api/enVivo'

const CLAVE_SONIDO = 'nodovip_sonido_injects'
export const DURACION_AVISO_MS = 8000

function leerSonido(): boolean {
  try {
    return localStorage.getItem(CLAVE_SONIDO) !== 'no'
  } catch {
    return true
  }
}

function guardarSonido(activo: boolean) {
  try {
    localStorage.setItem(CLAVE_SONIDO, activo ? 'si' : 'no')
  } catch {
    // Sin almacenamiento (modo privado): la preferencia dura solo esta visita.
  }
}

/** Dos tonos cortos ascendentes, como una notificación. Falla en silencio. */
function tocarSonido() {
  try {
    const Contexto =
      window.AudioContext ??
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
    if (!Contexto) return
    const ctx = new Contexto()
    const inicio = ctx.currentTime
    ;[660, 880].forEach((frecuencia, n) => {
      const osc = ctx.createOscillator()
      const volumen = ctx.createGain()
      osc.type = 'sine'
      osc.frequency.value = frecuencia
      const t = inicio + n * 0.18
      volumen.gain.setValueAtTime(0.0001, t)
      volumen.gain.exponentialRampToValueAtTime(0.18, t + 0.02)
      volumen.gain.exponentialRampToValueAtTime(0.0001, t + 0.16)
      osc.connect(volumen).connect(ctx.destination)
      osc.start(t)
      osc.stop(t + 0.17)
    })
    window.setTimeout(() => void ctx.close(), 600)
  } catch {
    // El navegador bloqueó el audio (sin interacción previa): no pasa nada.
  }
}

export function useAvisoInject(vista: VistaEnVivo | undefined) {
  const [aviso, setAviso] = useState<InjectEnVivo | null>(null)
  const [sonido, setSonido] = useState(leerSonido)
  // Título del inject que llegó con la pestaña oculta (hace parpadear el título).
  const [parpadeo, setParpadeo] = useState<string | null>(null)
  const [previo, setPrevio] = useState<number | undefined>(undefined)
  const sonidoRef = useRef(sonido)
  useEffect(() => {
    sonidoRef.current = sonido
  }, [sonido])

  // Se detecta el cambio durante el render (patrón recomendado por React para
  // ajustar el estado cuando cambia una prop). La primera vista no avisa.
  const actual = vista?.inject_actual
  if (actual !== previo) {
    setPrevio(actual)
    if (previo !== undefined && actual !== undefined && actual > previo && vista?.inject) {
      setAviso(vista.inject)
      if (document.hidden) setParpadeo(vista.inject.titulo)
    }
  }

  // El sonido es un efecto externo: se toca cuando aparece un aviso nuevo.
  useEffect(() => {
    if (aviso && sonidoRef.current) tocarSonido()
  }, [aviso])

  // El banner se oculta solo.
  useEffect(() => {
    if (!aviso) return
    const t = window.setTimeout(() => setAviso(null), DURACION_AVISO_MS)
    return () => window.clearTimeout(t)
  }, [aviso])

  // Título parpadeante hasta que el participante vuelva a la pestaña.
  useEffect(() => {
    if (!parpadeo) return
    const original = document.title
    const alterno = `● Nuevo inject: ${parpadeo}`
    let encendido = false
    const intervalo = window.setInterval(() => {
      encendido = !encendido
      document.title = encendido ? alterno : original
    }, 1000)
    const alVolver = () => {
      if (!document.hidden) setParpadeo(null)
    }
    document.addEventListener('visibilitychange', alVolver)
    return () => {
      window.clearInterval(intervalo)
      document.removeEventListener('visibilitychange', alVolver)
      document.title = original
    }
  }, [parpadeo])

  const alternarSonido = useCallback(() => {
    setSonido((activo) => {
      guardarSonido(!activo)
      return !activo
    })
  }, [])

  const cerrarAviso = useCallback(() => setAviso(null), [])

  return { aviso, cerrarAviso, sonido, alternarSonido }
}
