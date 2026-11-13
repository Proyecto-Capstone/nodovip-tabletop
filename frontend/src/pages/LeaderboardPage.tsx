// PB-12: sesiones con leaderboard visibles para el usuario. Observador y
// Administrador ven cualquier sesión en curso o finalizada; el Moderador,
// solo las suyas. Las sesiones en vivo van primero y destacadas.

import { ArrowRight, CalendarCheck, Circle, Flag, Radio, Search, Trophy } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { rutaSesionesLeaderboard, type SesionLeaderboard } from '../api/leaderboard'
import { useSesion } from '../auth/sesionContext'
import { Cargando, Errores, EstadoSesionBadge, SinPermiso } from '../components/Etiquetas'
import { Indicador } from '../components/Indicador'
import { useGet } from '../lib/useGet'

type Filtro = 'todas' | 'en_curso' | 'finalizada'

const FILTROS: { valor: Filtro; texto: string }[] = [
  { valor: 'todas', texto: 'Todas' },
  { valor: 'en_curso', texto: 'En vivo' },
  { valor: 'finalizada', texto: 'Finalizadas' },
]

const formatoFecha = (iso: string | null) =>
  iso
    ? new Date(iso).toLocaleDateString('es-EC', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      })
    : null

const normalizar = (texto: string) => texto.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

function AvanceInjects({ sesion }: { sesion: SesionLeaderboard }) {
  const porcentaje = sesion.total_injects
    ? Math.round((sesion.inject_actual / sesion.total_injects) * 100)
    : 0
  return (
    <div className="avance-injects">
      <span className="texto-suave">
        Inject {sesion.inject_actual}/{sesion.total_injects}
      </span>
      <span className="avance-injects-barra" aria-hidden="true">
        <span style={{ width: `${porcentaje}%` }} />
      </span>
    </div>
  )
}

export function LeaderboardPage() {
  const { rol, puede } = useSesion()
  const permitido = puede('leaderboard:ver')
  const sesiones = useGet<SesionLeaderboard[]>(permitido ? rutaSesionesLeaderboard : null, rol)
  const [filtro, setFiltro] = useState<Filtro>('todas')
  const [texto, setTexto] = useState('')

  const lista = useMemo(() => sesiones.datos ?? [], [sesiones.datos])
  const visibles = useMemo(() => {
    const buscado = normalizar(texto.trim())
    return lista.filter(
      (s) =>
        (filtro === 'todas' || s.estado === filtro) &&
        (!buscado || normalizar(s.nombre).includes(buscado)),
    )
  }, [lista, filtro, texto])

  if (!permitido) return <SinPermiso />

  const enVivo = visibles.filter((s) => s.estado === 'en_curso')
  const finalizadas = visibles.filter((s) => s.estado !== 'en_curso')
  const totalEnVivo = lista.filter((s) => s.estado === 'en_curso').length
  const totalFinalizadas = lista.length - totalEnVivo
  const ultima = lista
    .map((s) => s.finalizada_en)
    .filter((f): f is string => Boolean(f))
    .sort()
    .at(-1)

  return (
    <div className="leaderboard-lista">
      <div className="encabezado">
        <div>
          <h1>Leaderboard</h1>
          <p className="texto-suave">
            Ranking en vivo por participante y por rol, de las sesiones en curso o finalizadas.
          </p>
        </div>
      </div>

      {sesiones.datos && lista.length > 0 && (
        <section className="indicadores" aria-label="Resumen del leaderboard">
          <Indicador
            tono="senal"
            icono={<Radio />}
            etiqueta="En vivo ahora"
            valor={totalEnVivo}
            detalle={totalEnVivo ? 'Ranking en tiempo real' : 'Ninguna sesión en curso'}
          />
          <Indicador
            tono="verde"
            icono={<Flag />}
            etiqueta="Finalizadas"
            valor={totalFinalizadas}
            detalle="Con resultado final"
          />
          <Indicador
            tono="azul"
            icono={<Trophy />}
            etiqueta="Sesiones con ranking"
            valor={lista.length}
            detalle="Visibles para tu rol"
          />
          <Indicador
            tono="gris"
            icono={<CalendarCheck />}
            etiqueta="Último cierre"
            valor={
              <span className="indicador-valor-texto">{formatoFecha(ultima ?? null) ?? '—'}</span>
            }
          />
        </section>
      )}

      {lista.length > 0 && (
        <div className="barra-herramientas">
          <div className="segmentos" role="group" aria-label="Filtrar por estado">
            {FILTROS.map((f) => (
              <button
                key={f.valor}
                type="button"
                className="segmento"
                aria-pressed={filtro === f.valor}
                onClick={() => setFiltro(f.valor)}
              >
                {f.texto}
                <span className="segmento-contador">
                  {f.valor === 'todas'
                    ? lista.length
                    : f.valor === 'en_curso'
                      ? totalEnVivo
                      : totalFinalizadas}
                </span>
              </button>
            ))}
          </div>
          <label className="campo campo-busqueda-compacta">
            <span className="solo-lector">Buscar sesión</span>
            <span className="campo-icono">
              <Search aria-hidden="true" />
              <input
                type="search"
                placeholder="Buscar sesión…"
                value={texto}
                maxLength={100}
                onChange={(e) => setTexto(e.target.value)}
              />
            </span>
          </label>
        </div>
      )}

      <Errores errores={sesiones.errores} />
      {sesiones.cargando && <Cargando />}
      {sesiones.datos?.length === 0 && (
        <p className="tarjeta vacio">
          No hay sesiones en curso ni finalizadas con leaderboard todavía.
        </p>
      )}
      {lista.length > 0 && visibles.length === 0 && (
        <p className="tarjeta vacio">Ninguna sesión coincide con la búsqueda.</p>
      )}

      {enVivo.length > 0 && (
        <section className="leaderboard-grupo" aria-labelledby="titulo-en-vivo">
          <h2 id="titulo-en-vivo" className="leaderboard-grupo-titulo">
            <span className="punto-vivo" aria-hidden="true" />
            En vivo ahora
          </h2>
          <div className="grilla-en-vivo">
            {enVivo.map((s) => (
              <Link key={s.id} to={`/leaderboard/${s.id}`} className="tarjeta-leaderboard en-vivo">
                <div className="fila-badges">
                  <EstadoSesionBadge estado={s.estado} />
                  <span className="badge badge-live">
                    <Circle size={10} fill="currentColor" aria-hidden="true" /> EN VIVO
                  </span>
                </div>
                <h3>{s.nombre}</h3>
                <AvanceInjects sesion={s} />
                <span className="tarjeta-leaderboard-accion">
                  Ver ranking en vivo <ArrowRight aria-hidden="true" />
                </span>
              </Link>
            ))}
          </div>
        </section>
      )}

      {finalizadas.length > 0 && (
        <section className="leaderboard-grupo" aria-labelledby="titulo-finalizadas">
          <h2 id="titulo-finalizadas" className="leaderboard-grupo-titulo">
            <Flag aria-hidden="true" />
            Finalizadas
            <span className="contador">{finalizadas.length}</span>
          </h2>
          <div className="grilla-leaderboard">
            {finalizadas.map((s) => (
              <Link key={s.id} to={`/leaderboard/${s.id}`} className="tarjeta-leaderboard">
                <div className="fila-badges">
                  <EstadoSesionBadge estado={s.estado} />
                  {s.finalizada_en && (
                    <span className="tarjeta-leaderboard-fecha">
                      {formatoFecha(s.finalizada_en)}
                    </span>
                  )}
                </div>
                <h3>{s.nombre}</h3>
                <AvanceInjects sesion={s} />
                <span className="tarjeta-leaderboard-accion">
                  Ver resultado <ArrowRight aria-hidden="true" />
                </span>
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
