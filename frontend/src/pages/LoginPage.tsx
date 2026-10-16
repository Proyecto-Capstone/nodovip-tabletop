// PB-01 / RF-01: inicio de sesión con correo y contraseña.

import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { useSesion } from '../auth/sesionContext'
import { Errores } from '../components/Etiquetas'

/** Ruta a la que volver después del login (solo rutas internas). */
function destino(estado: unknown): string {
  const desde = (estado as { desde?: unknown } | null)?.desde
  if (typeof desde === 'string' && desde.startsWith('/') && !desde.startsWith('/login')) {
    return desde
  }
  return '/'
}

export function LoginPage() {
  const { usuario, cargando, iniciarSesion } = useSesion()
  const navegar = useNavigate()
  const ubicacion = useLocation()
  const [correo, setCorreo] = useState('')
  const [contrasena, setContrasena] = useState('')
  const [verContrasena, setVerContrasena] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [errores, setErrores] = useState<string[]>()

  if (!cargando && usuario && !enviando) {
    return <Navigate to={destino(ubicacion.state)} replace />
  }

  const enviar = async (evento: FormEvent) => {
    evento.preventDefault()
    setErrores(undefined)
    setEnviando(true)
    try {
      await iniciarSesion(correo, contrasena)
      navegar(destino(ubicacion.state), { replace: true })
    } catch (error) {
      setContrasena('')
      setErrores(
        error instanceof ApiError
          ? error.errores
          : ['No se pudo conectar con el servidor. Intenta de nuevo.'],
      )
      setEnviando(false)
    }
  }

  return (
    <main className="pantalla-login">
      <form className="tarjeta tarjeta-login" onSubmit={enviar}>
        <div className="login-marca">NODOVIP</div>
        <h1>Iniciar sesión</h1>
        <p className="texto-suave">Plataforma de ejercicios tabletop de ciberseguridad</p>

        <Errores errores={errores} />

        <label className="campo">
          Correo
          <input
            type="email"
            name="correo"
            autoComplete="username"
            inputMode="email"
            required
            autoFocus
            value={correo}
            onChange={(e) => setCorreo(e.target.value)}
          />
        </label>

        <label className="campo">
          Contraseña
          <span className="campo-con-boton">
            <input
              type={verContrasena ? 'text' : 'password'}
              name="contrasena"
              autoComplete="current-password"
              required
              value={contrasena}
              onChange={(e) => setContrasena(e.target.value)}
            />
            <button
              type="button"
              className="boton boton-texto"
              aria-pressed={verContrasena}
              onClick={() => setVerContrasena((v) => !v)}
            >
              {verContrasena ? 'Ocultar' : 'Mostrar'}
            </button>
          </span>
        </label>

        <button
          type="submit"
          className="boton boton-primario boton-bloque"
          disabled={enviando || !correo.trim() || !contrasena}
        >
          {enviando ? 'Ingresando…' : 'Ingresar'}
        </button>

        <p className="texto-suave login-ayuda">
          ¿Olvidaste tu contraseña o no tienes cuenta? Pide al administrador de la
          plataforma que la restablezca o te registre.
        </p>
      </form>
    </main>
  )
}
