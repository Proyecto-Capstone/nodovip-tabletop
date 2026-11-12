import { describe, expect, it } from 'vitest'
import type { Acceso } from '../api/accesos'
import { aCsv, actividadPorHora, esIpInterna, leerAgente } from './accesos'

const acceso = (cambios: Partial<Acceso>): Acceso => ({
  id: 1,
  fecha_hora: '2026-11-11T20:30:00Z',
  correo: 'ana@demo.nodovip.test',
  usuario_id: 'u1',
  ip: '172.18.0.1',
  user_agent: null,
  resultado: 'exitoso',
  ...cambios,
})

describe('utilidades del historial de accesos', () => {
  it('reconoce navegador, sistema y scripts en el user-agent', () => {
    expect(
      leerAgente(
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36',
      ),
    ).toEqual({ navegador: 'Chrome 157', sistema: 'Windows 10/11', automatizado: false })
    expect(leerAgente('Python-urllib/3.14')).toMatchObject({
      navegador: 'Python 3.14',
      automatizado: true,
    })
    expect(leerAgente(null).navegador).toBe('Desconocido')
  })

  it('distingue IP internas de externas', () => {
    for (const ip of ['10.0.0.5', '172.18.0.1', '192.168.1.20', '127.0.0.1', '::1']) {
      expect(esIpInterna(ip)).toBe(true)
    }
    for (const ip of ['172.32.0.1', '8.8.8.8', '200.25.1.4']) {
      expect(esIpInterna(ip)).toBe(false)
    }
  })

  it('cuenta los eventos por hora y por grupo en las últimas 24 h', () => {
    const ahora = new Date('2026-11-11T21:10:00Z')
    const horas = actividadPorHora(
      [
        acceso({ fecha_hora: '2026-11-11T21:05:00Z' }),
        acceso({ fecha_hora: '2026-11-11T21:06:00Z', resultado: 'credenciales_invalidas' }),
        acceso({ fecha_hora: '2026-11-10T10:00:00Z' }), // fuera de las 24 h
      ],
      ahora,
    )
    expect(horas).toHaveLength(24)
    expect(horas[23]).toMatchObject({ exitoso: 1, fallido: 1, bloqueado: 0 })
    expect(horas.reduce((s, h) => s + h.exitoso + h.fallido, 0)).toBe(2)
  })

  it('el CSV neutraliza fórmulas (inyección CSV) y escapa comillas', () => {
    const csv = aCsv([acceso({ correo: '=HYPERLINK("http://x")', user_agent: '+cmd' })])
    expect(csv.startsWith('﻿id,fecha_hora')).toBe(true)
    expect(csv).toContain(`"'=HYPERLINK(""http://x"")"`)
    expect(csv).toContain(`"'+cmd"`)
  })
})
