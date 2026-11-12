// Evidencia simulada de un inject (PC-44): el inject llega como llegaría en un
// incidente real — un correo, una alerta del SIEM, una noticia, una llamada…
// Todo el contenido es ficticio.

import type { Evidencia, NivelAlerta, TipoEvidencia } from '../api/escenarios'
import { NIVELES_ALERTA, TIPOS_EVIDENCIA } from '../lib/evidencias'

const evidenciaVacia = (): Evidencia => ({
  tipo: 'correo',
  origen: '',
  asunto: '',
  contenido: '',
  nivel: null,
})

interface EditorProps {
  valor: Evidencia | null
  onChange: (valor: Evidencia | null) => void
}

/** Campos para agregar o editar la evidencia de un inject. Es opcional. */
export function EditorEvidencia({ valor, onChange }: EditorProps) {
  if (!valor) {
    return (
      <button
        type="button"
        className="boton boton-texto boton-agregar-evidencia"
        onClick={() => onChange(evidenciaVacia())}
      >
        + Agregar evidencia simulada (correo, alerta, noticia…)
      </button>
    )
  }
  const textos = TIPOS_EVIDENCIA[valor.tipo]
  const cambiar = (cambios: Partial<Evidencia>) => onChange({ ...valor, ...cambios })

  return (
    <div className="editor-evidencia">
      <div className="editor-evidencia-cabecera">
        <strong>Evidencia simulada</strong>
        <button
          type="button"
          className="boton boton-texto texto-peligro"
          onClick={() => onChange(null)}
        >
          Quitar evidencia
        </button>
      </div>
      <div className="fila-campos">
        <label className="campo">
          <span>Tipo</span>
          <select
            value={valor.tipo}
            onChange={(e) => {
              const tipo = e.target.value as TipoEvidencia
              cambiar({ tipo, nivel: tipo === 'alerta' ? (valor.nivel ?? 'alta') : null })
            }}
          >
            {Object.entries(TIPOS_EVIDENCIA).map(([codigo, t]) => (
              <option key={codigo} value={codigo}>
                {t.nombre}
              </option>
            ))}
          </select>
        </label>
        {valor.tipo === 'alerta' && (
          <label className="campo campo-corto">
            <span>Severidad</span>
            <select
              value={valor.nivel ?? 'alta'}
              onChange={(e) => cambiar({ nivel: e.target.value as NivelAlerta })}
            >
              {Object.entries(NIVELES_ALERTA).map(([codigo, nombre]) => (
                <option key={codigo} value={codigo}>
                  {nombre}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>
      <div className="fila-campos">
        <label className="campo">
          <span>{textos.origen}</span>
          <input
            required
            minLength={2}
            maxLength={150}
            value={valor.origen}
            onChange={(e) => cambiar({ origen: e.target.value })}
          />
        </label>
        <label className="campo campo-ancho">
          <span>{textos.asunto}</span>
          <input
            required
            minLength={2}
            maxLength={200}
            value={valor.asunto}
            onChange={(e) => cambiar({ asunto: e.target.value })}
          />
        </label>
      </div>
      <label className="campo">
        <span>{textos.contenido}</span>
        <textarea
          required
          minLength={5}
          maxLength={5000}
          rows={3}
          value={valor.contenido}
          onChange={(e) => cambiar({ contenido: e.target.value })}
        />
      </label>
      <p className="texto-suave texto-chico">
        Usa solo datos ficticios: nada de nombres, correos o dominios reales.
      </p>
    </div>
  )
}

/** Muestra la evidencia con el aspecto de su tipo (bandeja de correo, consola…). */
export function EvidenciaSimulada({ evidencia }: { evidencia: Evidencia }) {
  const textos = TIPOS_EVIDENCIA[evidencia.tipo]
  const etiqueta = `${textos.nombre}: ${evidencia.asunto}`

  const Icono = textos.icono

  switch (evidencia.tipo) {
    case 'correo':
      return (
        <article className="evidencia evidencia-correo" aria-label={etiqueta}>
          <header className="evidencia-barra">
            <Icono size={14} aria-hidden="true" /> Bandeja de entrada
          </header>
          <dl className="evidencia-correo-datos">
            <dt>De</dt>
            <dd>{evidencia.origen}</dd>
            <dt>Asunto</dt>
            <dd>
              <strong>{evidencia.asunto}</strong>
            </dd>
          </dl>
          <p className="evidencia-cuerpo">{evidencia.contenido}</p>
        </article>
      )
    case 'alerta': {
      const nivel = evidencia.nivel ?? 'alta'
      return (
        <article className="evidencia evidencia-alerta" aria-label={etiqueta}>
          <header className="evidencia-alerta-cabecera">
            <span className={`evidencia-severidad severidad-${nivel}`}>
              {NIVELES_ALERTA[nivel]}
            </span>
            <span className="evidencia-alerta-origen">{evidencia.origen}</span>
          </header>
          <p className="evidencia-alerta-titulo">
            <Icono size={14} aria-hidden="true" /> {evidencia.asunto}
          </p>
          <pre className="evidencia-alerta-detalle">{evidencia.contenido}</pre>
        </article>
      )
    }
    case 'noticia':
      return (
        <article className="evidencia evidencia-noticia" aria-label={etiqueta}>
          <p className="evidencia-noticia-medio">{evidencia.origen}</p>
          <h4 className="evidencia-noticia-titular">{evidencia.asunto}</h4>
          <p className="evidencia-cuerpo">{evidencia.contenido}</p>
        </article>
      )
    case 'llamada':
      return (
        <article className="evidencia evidencia-llamada" aria-label={etiqueta}>
          <header className="evidencia-llamada-cabecera">
            <span className="evidencia-llamada-icono">
              <Icono size={18} aria-hidden="true" />
            </span>
            <span>
              <strong>Llamada entrante</strong>
              <span className="evidencia-llamada-origen">{evidencia.origen}</span>
            </span>
          </header>
          <p className="evidencia-llamada-motivo">{evidencia.asunto}</p>
          <blockquote className="evidencia-cuerpo">{evidencia.contenido}</blockquote>
        </article>
      )
    case 'mensaje':
      return (
        <article className="evidencia evidencia-mensaje" aria-label={etiqueta}>
          <p className="evidencia-mensaje-origen">
            <Icono size={14} aria-hidden="true" /> {evidencia.origen}
          </p>
          <p className="evidencia-mensaje-burbuja">{evidencia.contenido}</p>
        </article>
      )
    case 'documento':
      return (
        <article className="evidencia evidencia-documento" aria-label={etiqueta}>
          <header className="evidencia-documento-cabecera">
            <Icono size={16} aria-hidden="true" />
            <span>
              <strong>{evidencia.asunto}</strong>
              <span className="evidencia-documento-origen">{evidencia.origen}</span>
            </span>
          </header>
          <p className="evidencia-cuerpo">{evidencia.contenido}</p>
        </article>
      )
  }
}
