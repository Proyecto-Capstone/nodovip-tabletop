// PC-44: línea de tiempo del incidente en la sala del participante y el aviso
// cuando llega un inject nuevo.

import { X } from 'lucide-react'
import type { InjectEnVivo } from '../api/enVivo'
import type { TipoEvidencia } from '../api/escenarios'
import { EvidenciaSimulada } from '../components/Evidencia'
import { TIPOS_EVIDENCIA } from '../lib/evidencias'
import { formatoReloj } from '../lib/useEnVivo'

function TipoEvidenciaEtiqueta({ tipo }: { tipo: TipoEvidencia }) {
  const { icono: Icono, nombre } = TIPOS_EVIDENCIA[tipo]
  return (
    <span className="linea-incidente-tipo texto-suave">
      <Icono size={14} aria-hidden="true" /> {nombre}
    </span>
  )
}

/** Banner que aparece unos segundos al lanzarse un inject. */
export function AvisoInject({
  inject,
  onCerrar,
}: {
  inject: InjectEnVivo | null
  onCerrar: () => void
}) {
  return (
    // La región existe siempre para que el lector de pantalla anuncie el cambio.
    <div className="aviso-inject-region" role="status" aria-live="assertive">
      {inject && (
        <div className="aviso-inject" key={inject.orden}>
          <span className="aviso-inject-pulso" aria-hidden="true" />
          <div className="aviso-inject-texto">
            <strong>Nuevo inject {inject.orden}</strong>
            <span>{inject.titulo}</span>
          </div>
          <button
            type="button"
            className="aviso-inject-cerrar"
            aria-label="Cerrar aviso"
            onClick={onCerrar}
          >
            <X size={16} aria-hidden="true" />
          </button>
        </div>
      )}
    </div>
  )
}

/** Los injects ya lanzados, del más reciente al primero. Los anteriores se
 * pueden volver a abrir para releer la narrativa y su evidencia. */
export function LineaDeTiempo({ lanzados }: { lanzados: InjectEnVivo[] }) {
  if (lanzados.length < 2) return null
  const anteriores = [...lanzados].sort((a, b) => b.orden - a.orden).slice(1)
  return (
    <section className="tarjeta" aria-labelledby="titulo-linea-incidente">
      <h2 id="titulo-linea-incidente">Línea de tiempo del incidente</h2>
      <ol className="linea-incidente">
        {anteriores.map((i) => (
          <li key={i.orden} className="linea-incidente-item">
            <span className="linea-incidente-punto" aria-hidden="true" />
            <details>
              <summary>
                <span className="linea-incidente-hora">
                  {i.lanzado_segundo !== null ? formatoReloj(i.lanzado_segundo) : '—'}
                </span>
                <span className="linea-incidente-titulo">
                  Inject {i.orden} · {i.titulo}
                </span>
                {i.evidencia && <TipoEvidenciaEtiqueta tipo={i.evidencia.tipo} />}
              </summary>
              <p className="parrafo">{i.descripcion}</p>
              {i.evidencia && <EvidenciaSimulada evidencia={i.evidencia} />}
            </details>
          </li>
        ))}
      </ol>
    </section>
  )
}
