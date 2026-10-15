import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api/client'
import { ADMINISTRADOR, renderConSesion, sesionDePrueba } from '../test/utilidades'
import { LoginPage } from './LoginPage'

function rutas() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<p>Inicio</p>} />
      <Route path="/usuarios" element={<p>Gestión de usuarios</p>} />
    </Routes>
  )
}

const campoCorreo = () => screen.getByLabelText('Correo')
const campoClave = () => screen.getByLabelText('Contraseña')
const botonIngresar = () => screen.getByRole('button', { name: 'Ingresar' })

describe('LoginPage', () => {
  it('no deja enviar con campos vacíos', async () => {
    renderConSesion(rutas(), { sesion: sesionDePrueba(null), ruta: '/login' })
    expect(botonIngresar()).toBeDisabled()
    await userEvent.type(campoCorreo(), 'ana@example.com')
    expect(botonIngresar()).toBeDisabled()
    await userEvent.type(campoClave(), 'x')
    expect(botonIngresar()).toBeEnabled()
  })

  it('inicia sesión y vuelve a la ruta que se pidió', async () => {
    const iniciarSesion = vi.fn(async () => ADMINISTRADOR)
    renderConSesion(rutas(), {
      sesion: sesionDePrueba(null, { iniciarSesion }),
      ruta: { pathname: '/login', state: { desde: '/usuarios' } },
    })

    await userEvent.type(campoCorreo(), 'ana@example.com')
    await userEvent.type(campoClave(), 'Nodovip2026seguro')
    await userEvent.click(botonIngresar())

    expect(iniciarSesion).toHaveBeenCalledWith('ana@example.com', 'Nodovip2026seguro')
    expect(await screen.findByText('Gestión de usuarios')).toBeInTheDocument()
  })

  it('muestra el error del backend y borra la contraseña', async () => {
    const iniciarSesion = vi.fn(async () => {
      throw new ApiError(401, ['Correo o contraseña incorrectos'])
    })
    renderConSesion(rutas(), {
      sesion: sesionDePrueba(null, { iniciarSesion }),
      ruta: '/login',
    })

    await userEvent.type(campoCorreo(), 'ana@example.com')
    await userEvent.type(campoClave(), 'incorrecta')
    await userEvent.click(botonIngresar())

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Correo o contraseña incorrectos',
    )
    expect(campoClave()).toHaveValue('')
    expect(campoCorreo()).toHaveValue('ana@example.com')
  })

  it('sin conexión muestra un mensaje claro', async () => {
    const iniciarSesion = vi.fn(async () => {
      throw new TypeError('Failed to fetch')
    })
    renderConSesion(rutas(), {
      sesion: sesionDePrueba(null, { iniciarSesion }),
      ruta: '/login',
    })
    await userEvent.type(campoCorreo(), 'ana@example.com')
    await userEvent.type(campoClave(), 'x')
    await userEvent.click(botonIngresar())
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo conectar')
  })

  it('permite ver la contraseña que se escribe', async () => {
    renderConSesion(rutas(), { sesion: sesionDePrueba(null), ruta: '/login' })
    expect(campoClave()).toHaveAttribute('type', 'password')
    await userEvent.click(screen.getByRole('button', { name: 'Mostrar' }))
    expect(campoClave()).toHaveAttribute('type', 'text')
  })

  it('no permite volver a una ruta externa', async () => {
    const iniciarSesion = vi.fn(async () => ADMINISTRADOR)
    renderConSesion(rutas(), {
      sesion: sesionDePrueba(null, { iniciarSesion }),
      ruta: { pathname: '/login', state: { desde: 'https://malicioso.example' } },
    })
    await userEvent.type(campoCorreo(), 'ana@example.com')
    await userEvent.type(campoClave(), 'x')
    await userEvent.click(botonIngresar())
    expect(await screen.findByText('Inicio')).toBeInTheDocument()
  })

  it('con sesión abierta no muestra el formulario', () => {
    renderConSesion(rutas(), { sesion: sesionDePrueba(ADMINISTRADOR), ruta: '/login' })
    expect(screen.getByText('Inicio')).toBeInTheDocument()
  })
})
