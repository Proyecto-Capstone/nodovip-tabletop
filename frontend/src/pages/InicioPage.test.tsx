import { screen } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import {
  ADMINISTRADOR,
  ANALISTA,
  MODERADOR,
  OBSERVADOR,
  PARTICIPANTE,
  renderConSesion,
  sesionDePrueba,
} from '../test/utilidades'
import { InicioPage } from './InicioPage'

function abrir(usuario: typeof ADMINISTRADOR) {
  renderConSesion(
    <Routes>
      <Route path="/" element={<InicioPage />} />
      <Route path="/escenarios" element={<p>Biblioteca de escenarios</p>} />
      <Route path="/mis-sesiones" element={<p>Mis sesiones</p>} />
      <Route path="/reportes" element={<p>Reportes</p>} />
      <Route path="/leaderboard" element={<p>Leaderboard</p>} />
    </Routes>,
    { sesion: sesionDePrueba(usuario), ruta: '/' },
  )
}

describe('InicioPage', () => {
  it('Administrador y Moderador van a la biblioteca de escenarios', () => {
    abrir(ADMINISTRADOR)
    expect(screen.getByText('Biblioteca de escenarios')).toBeInTheDocument()
  })

  it('el Moderador también va a la biblioteca de escenarios', () => {
    abrir(MODERADOR)
    expect(screen.getByText('Biblioteca de escenarios')).toBeInTheDocument()
  })

  it('el Participante va a sus sesiones', () => {
    abrir(PARTICIPANTE)
    expect(screen.getByText('Mis sesiones')).toBeInTheDocument()
  })

  it('el Analista va directo a los reportes, sin un aviso de espera', () => {
    abrir(ANALISTA)
    expect(screen.getByText('Reportes')).toBeInTheDocument()
  })

  it('el Observador va directo al leaderboard, sin un aviso de espera', () => {
    abrir(OBSERVADOR)
    expect(screen.getByText('Leaderboard')).toBeInTheDocument()
  })
})
