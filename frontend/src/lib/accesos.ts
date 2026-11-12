// Utilidades del historial de accesos: interpretan el user-agent y la IP que ya
// registra el backend (no consultan servicios externos ni geolocalizan).

import type { Acceso, ResultadoAcceso } from '../api/accesos'

export type GrupoResultado = 'exitoso' | 'fallido' | 'bloqueado'

export const GRUPO_DE: Record<ResultadoAcceso, GrupoResultado> = {
  exitoso: 'exitoso',
  credenciales_invalidas: 'fallido',
  usuario_inactivo: 'fallido',
  bloqueado: 'bloqueado',
}

/** Riesgo estimado según el resultado: orienta la revisión, no es un puntaje. */
export const RIESGO: Record<ResultadoAcceso, { nivel: 'bajo' | 'medio' | 'alto'; texto: string }> =
  {
    exitoso: { nivel: 'bajo', texto: 'Bajo' },
    credenciales_invalidas: { nivel: 'medio', texto: 'Medio' },
    usuario_inactivo: { nivel: 'medio', texto: 'Medio' },
    bloqueado: { nivel: 'alto', texto: 'Alto' },
  }

export interface AgenteLeido {
  navegador: string
  sistema: string
  automatizado: boolean
}

/** Lectura simple del user-agent: navegador, sistema y si parece un script. */
export function leerAgente(ua: string | null): AgenteLeido {
  if (!ua) return { navegador: 'Desconocido', sistema: 'Desconocido', automatizado: false }
  const buscar = (patrones: [RegExp, string][]) => {
    for (const [patron, nombre] of patrones) {
      const m = ua.match(patron)
      if (m) return nombre.replace('$1', m[1] ?? '').trim()
    }
    return null
  }
  const script = buscar([
    [/python-(?:urllib|requests)\/?([\d.]*)/i, 'Python $1'],
    [/curl\/([\d.]+)/i, 'curl $1'],
    [/(?:node-fetch|undici|axios)\/?([\d.]*)/i, 'Node.js $1'],
    [/(?:testclient|httpx)\/?([\d.]*)/i, 'Cliente de pruebas $1'],
  ])
  if (script) return { navegador: script, sistema: 'Script / API', automatizado: true }
  const navegador =
    buscar([
      [/Edg\/(\d+)/, 'Edge $1'],
      [/OPR\/(\d+)/, 'Opera $1'],
      [/Firefox\/(\d+)/, 'Firefox $1'],
      [/Chrome\/(\d+)/, 'Chrome $1'],
      [/Version\/(\d+).*Safari/, 'Safari $1'],
    ]) ?? 'Otro navegador'
  const sistema =
    buscar([
      [/Windows NT 10/, 'Windows 10/11'],
      [/Windows/, 'Windows'],
      [/Android (\d+)/, 'Android $1'],
      [/iPhone|iPad/, 'iOS'],
      [/Mac OS X/, 'macOS'],
      [/Linux/, 'Linux'],
    ]) ?? 'Otro sistema'
  return { navegador, sistema, automatizado: false }
}

/** IPv4 privada, de loopback o de la red de Docker: tráfico interno. */
export function esIpInterna(ip: string): boolean {
  if (ip === '::1' || ip === 'localhost' || ip.startsWith('127.')) return true
  const partes = ip.split('.').map(Number)
  if (partes.length !== 4 || partes.some(Number.isNaN)) return false
  const [a, b] = partes
  return a === 10 || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168)
}

/** Cantidad de eventos por hora en las últimas 24 h, separados por grupo. */
export function actividadPorHora(accesos: Acceso[], ahora = new Date()) {
  const fin = new Date(ahora)
  fin.setMinutes(0, 0, 0)
  const horas = Array.from({ length: 24 }, (_, i) => {
    const inicio = new Date(fin.getTime() - (23 - i) * 3600_000)
    return { inicio, exitoso: 0, fallido: 0, bloqueado: 0 }
  })
  const primera = horas[0].inicio.getTime()
  for (const a of accesos) {
    if (!a.fecha_hora) continue
    const indice = Math.floor((new Date(a.fecha_hora).getTime() - primera) / 3600_000)
    if (indice >= 0 && indice < 24) horas[indice][GRUPO_DE[a.resultado]] += 1
  }
  return horas
}

/** CSV (con BOM para que Excel respete las tildes) de los accesos dados.
 * El correo y el user-agent los escribe quien intenta ingresar: una celda que
 * empieza con = + - @ (o tabulador/retorno) se antepone con ' para que una
 * hoja de cálculo no la ejecute como fórmula (inyección CSV, OWASP). */
export function aCsv(accesos: Acceso[]): string {
  const celda = (v: string | number | null) => {
    let texto = String(v ?? '')
    if (/^[=+\-@\t\r]/.test(texto)) texto = `'${texto}`
    return `"${texto.replace(/"/g, '""')}"`
  }
  const filas = accesos.map((a) =>
    [a.id, a.fecha_hora, a.correo, a.usuario_id, a.resultado, a.ip, a.user_agent]
      .map(celda)
      .join(','),
  )
  return '﻿' + ['id,fecha_hora,correo,usuario_id,resultado,ip,user_agent', ...filas].join('\n')
}
