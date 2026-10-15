// PB-01 / RNF-01: historial de accesos (usuario, fecha/hora, IP, resultado).

import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { rutaAccesos, type Acceso } from '../api/accesos'
import { useSesion } from '../auth/sesionContext'
import { Cargando, Errores } from '../components/Etiquetas'
import { ETIQUETA_RESULTADO } from '../lib/etiquetas'
import { useDebounce, useGet } from '../lib/useGet'

const formatoFechaHora = (iso: string | null) =>
  iso
    ? new Date(iso).toLocaleString('es-EC', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
    : '—'

/** "2026-10-15" del input date → inicio o fin de ese día en hora local, en ISO. */
const limiteDelDia = (fecha: string, fin: boolean) =>
  fecha ? new Date(`${fecha}T${fin ? '23:59:59.999' : '00:00:00'}`).toISOString() : undefined

export function AccesosPage() {
  const { rol } = useSesion()
  const [parametros, setParametros] = useSearchParams()
  const usuarioId = parametros.get('usuario') ?? undefined
  const [texto, setTexto] = useState('')
  const [resultado, setResultado] = useState('')
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')
  const q = useDebounce(texto.trim())

  const accesos = useGet<Acceso[]>(
    rutaAccesos({
      usuario_id: usuarioId,
      q,
      resultado,
      desde: limiteDelDia(desde, false),
      hasta: limiteDelDia(hasta, true),
    }),
    rol,
  )

  const limpiar = () => {
    setTexto('')
    setResultado('')
    setDesde('')
    setHasta('')
    setParametros({})
  }

  return (
    <>
      <div className="encabezado">
        <div>
          <h1>Historial de accesos</h1>
          <p className="texto-suave">
            Cada intento de inicio de sesión, exitoso o no. Se muestran los 200 más
            recientes que cumplan los filtros.
          </p>
        </div>
      </div>

      {usuarioId && (
        <div className="alerta alerta-aviso">
          Mostrando solo los accesos de un usuario.{' '}
          <Link to="/accesos">
            Ver todos
          </Link>
        </div>
      )}

      <div className="tarjeta filtros">
        <label className="campo campo-busqueda">
          Correo
          <input
            type="search"
            placeholder="Buscar por correo ingresado"
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
          />
        </label>
        <label className="campo">
          Resultado
          <select value={resultado} onChange={(e) => setResultado(e.target.value)}>
            <option value="">Todos</option>
            {Object.entries(ETIQUETA_RESULTADO).map(([codigo, nombre]) => (
              <option key={codigo} value={codigo}>
                {nombre}
              </option>
            ))}
          </select>
        </label>
        <label className="campo">
          Desde
          <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
        </label>
        <label className="campo">
          Hasta
          <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} />
        </label>
        <button type="button" className="boton boton-texto" onClick={limpiar}>
          Limpiar filtros
        </button>
      </div>

      <Errores errores={accesos.errores} />
      {accesos.cargando && <Cargando />}

      {accesos.datos && accesos.datos.length === 0 && (
        <div className="tarjeta vacio">No hay accesos con esos filtros.</div>
      )}

      {accesos.datos && accesos.datos.length > 0 && (
        <div className="tarjeta tabla-contenedor">
          <table className="tabla">
            <thead>
              <tr>
                <th>Fecha y hora</th>
                <th>Correo ingresado</th>
                <th>Resultado</th>
                <th>IP</th>
                <th>Navegador</th>
              </tr>
            </thead>
            <tbody>
              {accesos.datos.map((a) => (
                <tr key={a.id}>
                  <td className="sin-salto">{formatoFechaHora(a.fecha_hora)}</td>
                  <td>
                    {a.correo}
                    {!a.usuario_id && <span className="texto-suave"> (no registrado)</span>}
                  </td>
                  <td>
                    <span className={`badge acceso-${a.resultado}`}>
                      {ETIQUETA_RESULTADO[a.resultado]}
                    </span>
                  </td>
                  <td className="sin-salto">{a.ip}</td>
                  <td className="celda-recortada" title={a.user_agent ?? undefined}>
                    {a.user_agent ?? '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
