// PB-05, paso 1: elegir el escenario publicado que sirve de base (CU-03.1).

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { rutas, type EscenarioResumen, type TipoEscenario } from '../api/escenarios'
import { crearSesion } from '../api/sesiones'
import { useSesion } from '../auth/sesionContext'
import { Cargando, Errores, NivelBadge, SinPermiso } from '../components/Etiquetas'
import { nombreTipo } from '../lib/etiquetas'
import { useGet } from '../lib/useGet'
import { PasosDiseno } from './disenador/PasosDiseno'

export function NuevaSesionPage() {
  const { rol, puede } = useSesion()
  const permitido = puede('sesiones:disenar')
  const navegar = useNavigate()
  const escenarios = useGet<EscenarioResumen[]>(
    permitido ? rutas.escenarios({}) : null,
    rol,
  )
  const tipos = useGet<TipoEscenario[]>(permitido ? rutas.tipos : null, rol)
  const [creando, setCreando] = useState<string>()
  const [errores, setErrores] = useState<string[]>()

  if (!permitido) return <SinPermiso />

  const usar = async (escenarioId: string) => {
    setCreando(escenarioId)
    setErrores(undefined)
    try {
      const sesion = await crearSesion(escenarioId)
      navegar(`/sesiones/${sesion.id}/disenar?paso=2`)
    } catch (error) {
      setErrores(error instanceof ApiError ? error.errores : ['Error de conexión'])
      setCreando(undefined)
    }
  }

  return (
    <div className="disenador">
      <PasosDiseno actual={1} completos={[]} />
      <div className="disenador-contenido">
        <div className="encabezado">
          <div>
            <h1>Paso 1 — Seleccionar escenario</h1>
            <p className="texto-suave">
              Elige un escenario publicado. La sesión copia sus roles, injects y
              tareas para que puedas ajustarlos.
            </p>
          </div>
        </div>
        <Errores errores={errores ?? escenarios.errores} />
        {escenarios.cargando && <Cargando />}
        {escenarios.datos?.length === 0 && (
          <p className="tarjeta vacio">No hay escenarios publicados todavía.</p>
        )}
        <div className="grilla-escenarios">
          {escenarios.datos?.map((e) => (
            <article key={e.id} className="tarjeta tarjeta-escenario">
              <div className="fila-badges">
                <span className="tipo">{nombreTipo(tipos.datos, e.tipo_codigo)}</span>
                <NivelBadge nivel={e.nivel} />
              </div>
              <h2>{e.nombre}</h2>
              <p className="conteos">
                {e.roles.length} roles · {e.total_injects} injects · {e.total_tareas}{' '}
                tareas
              </p>
              <button
                type="button"
                className="boton boton-primario"
                disabled={creando !== undefined}
                onClick={() => usar(e.id)}
              >
                {creando === e.id ? 'Creando…' : 'Usar este escenario'}
              </button>
            </article>
          ))}
        </div>
      </div>
    </div>
  )
}
