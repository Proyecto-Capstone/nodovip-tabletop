// PB-01 / RF-01: inicio de sesión con correo y contraseña.

import { ArrowRight, Eye, EyeOff, LockKeyhole, Mail, MapPin } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { useSesion } from '../auth/sesionContext'
import logoNodovip from '../assets/marca/nodovip-horizontal-claro.webp'
import { Errores } from '../components/Etiquetas'
import { RedGlobal } from '../components/RedGlobal'

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
      <section className="login-portada">
        <RedGlobal className="login-red-global" />
        <img
          className="login-logo"
          src={logoNodovip}
          alt="NODOVIP — Conectamos tu mundo digital"
          width={720}
          height={206}
        />
        <h1 className="login-titulo">Plataforma de ejercicios tabletop de ciberseguridad</h1>
        <p className="login-lugar">
          <MapPin aria-hidden="true" />
          Quito, Ecuador
        </p>
      </section>

      <section className="login-lado-formulario">
        <form className="tarjeta-login" onSubmit={enviar}>
          <h2>Iniciar sesión</h2>
          <p className="login-subtitulo">Ingresa con tu cuenta para continuar.</p>

          <Errores errores={errores} />

          <label className="campo">
            Correo electrónico
            <span className="login-entrada">
              <Mail aria-hidden="true" />
              <input
                type="email"
                name="correo"
                autoComplete="username"
                inputMode="email"
                placeholder="usuario@empresa.com"
                required
                autoFocus
                value={correo}
                onChange={(e) => setCorreo(e.target.value)}
              />
            </span>
          </label>

          <label className="campo">
            Contraseña
            <span className="login-entrada">
              <LockKeyhole aria-hidden="true" />
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
                className="login-ver"
                aria-pressed={verContrasena}
                onClick={() => setVerContrasena((v) => !v)}
              >
                {verContrasena ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
                {verContrasena ? 'Ocultar' : 'Mostrar'}
              </button>
            </span>
          </label>

          <button
            type="submit"
            className="boton boton-primario boton-bloque login-ingresar"
            disabled={enviando || !correo.trim() || !contrasena}
          >
            {enviando ? 'Ingresando…' : 'Ingresar'}
            {!enviando && <ArrowRight aria-hidden="true" />}
          </button>

          <p className="login-ayuda">
            ¿Olvidaste tu contraseña o no tienes cuenta? Pide al administrador de la plataforma que
            la restablezca o te registre.
          </p>
        </form>
      </section>
    </main>
  )
}
