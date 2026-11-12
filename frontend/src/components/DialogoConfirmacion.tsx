// PC-15 (fix 2): diálogo de confirmación accesible que reemplaza confirm().
// confirm() bloquea el hilo, no se puede estilizar ni navegar con lector de
// pantalla como un diálogo real. useConfirmar() da la misma forma de uso
// (await) pero con foco atrapado, Escape para cancelar y foco devuelto al
// botón que abrió el diálogo.

import { useCallback, useEffect, useId, useRef, useState, type ReactNode } from 'react'
import { ConfirmacionContext, type OpcionesConfirmacion } from './confirmacionContext'

interface Pedido {
  opciones: OpcionesConfirmacion
  resolver: (valor: boolean) => void
}

export function ProveedorConfirmacion({ children }: { children: ReactNode }) {
  const [pedido, setPedido] = useState<Pedido | null>(null)
  const disparadorRef = useRef<HTMLElement | null>(null)

  const confirmar = useCallback((opciones: OpcionesConfirmacion) => {
    disparadorRef.current = document.activeElement as HTMLElement | null
    return new Promise<boolean>((resolver) => {
      setPedido({ opciones, resolver })
    })
  }, [])

  const cerrar = useCallback(
    (resultado: boolean) => {
      pedido?.resolver(resultado)
      setPedido(null)
      disparadorRef.current?.focus()
    },
    [pedido],
  )

  return (
    <ConfirmacionContext.Provider value={confirmar}>
      {children}
      {pedido && <DialogoConfirmacion opciones={pedido.opciones} onResolver={cerrar} />}
    </ConfirmacionContext.Provider>
  )
}

function DialogoConfirmacion({
  opciones,
  onResolver,
}: {
  opciones: OpcionesConfirmacion
  onResolver: (resultado: boolean) => void
}) {
  const tituloId = useId()
  const cuerpoId = useId()
  const cancelarRef = useRef<HTMLButtonElement>(null)
  const confirmarRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    confirmarRef.current?.focus()
  }, [])

  useEffect(() => {
    const alTeclado = (evento: KeyboardEvent) => {
      if (evento.key === 'Escape') {
        onResolver(false)
        return
      }
      if (evento.key !== 'Tab') return
      const primero = cancelarRef.current
      const ultimo = confirmarRef.current
      if (!primero || !ultimo) return
      if (evento.shiftKey && document.activeElement === primero) {
        evento.preventDefault()
        ultimo.focus()
      } else if (!evento.shiftKey && document.activeElement === ultimo) {
        evento.preventDefault()
        primero.focus()
      }
    }
    document.addEventListener('keydown', alTeclado)
    return () => document.removeEventListener('keydown', alTeclado)
  }, [onResolver])

  return (
    <div
      className="dialogo-fondo"
      onMouseDown={(evento) => {
        if (evento.target === evento.currentTarget) onResolver(false)
      }}
    >
      <div
        className="dialogo"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={tituloId}
        aria-describedby={opciones.cuerpo ? cuerpoId : undefined}
      >
        <h2 id={tituloId}>{opciones.titulo}</h2>
        {opciones.cuerpo && (
          <p id={cuerpoId} className="dialogo-cuerpo">
            {opciones.cuerpo}
          </p>
        )}
        <div className="dialogo-acciones">
          <button type="button" ref={cancelarRef} className="boton" onClick={() => onResolver(false)}>
            {opciones.textoCancelar ?? 'Cancelar'}
          </button>
          <button
            type="button"
            ref={confirmarRef}
            className={`boton ${opciones.variante === 'primario' ? 'boton-primario' : 'boton-peligro'}`}
            onClick={() => onResolver(true)}
          >
            {opciones.textoConfirmar ?? 'Confirmar'}
          </button>
        </div>
      </div>
    </div>
  )
}
