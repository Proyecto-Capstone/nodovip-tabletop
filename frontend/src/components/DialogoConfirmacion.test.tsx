import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'
import { useConfirmar } from './confirmacionContext'
import { ProveedorConfirmacion } from './DialogoConfirmacion'

function Probador() {
  const confirmar = useConfirmar()
  const [resultado, setResultado] = useState<string>()

  const pedir = async () => {
    const ok = await confirmar({ titulo: '¿Eliminar?', cuerpo: 'No se puede deshacer.' })
    setResultado(ok ? 'confirmado' : 'cancelado')
  }

  return (
    <>
      <button type="button" onClick={pedir}>
        Abrir
      </button>
      <p>{resultado}</p>
    </>
  )
}

function renderProbador() {
  return render(
    <ProveedorConfirmacion>
      <Probador />
    </ProveedorConfirmacion>,
  )
}

describe('DialogoConfirmacion', () => {
  it('muestra el título y el cuerpo, y resuelve true al confirmar', async () => {
    renderProbador()
    await userEvent.click(screen.getByRole('button', { name: 'Abrir' }))

    const dialogo = screen.getByRole('alertdialog', { name: '¿Eliminar?' })
    expect(dialogo).toHaveTextContent('No se puede deshacer.')

    await userEvent.click(screen.getByRole('button', { name: 'Confirmar' }))
    expect(await screen.findByText('confirmado')).toBeInTheDocument()
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
  })

  it('resuelve false al cancelar', async () => {
    renderProbador()
    await userEvent.click(screen.getByRole('button', { name: 'Abrir' }))
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(await screen.findByText('cancelado')).toBeInTheDocument()
  })

  it('resuelve false con Escape y devuelve el foco al botón que abrió el diálogo', async () => {
    renderProbador()
    const abrir = screen.getByRole('button', { name: 'Abrir' })
    await userEvent.click(abrir)
    await userEvent.keyboard('{Escape}')
    expect(await screen.findByText('cancelado')).toBeInTheDocument()
    expect(abrir).toHaveFocus()
  })

  it('el foco entra en el botón de confirmar y el diálogo es la variante de peligro por defecto', async () => {
    renderProbador()
    await userEvent.click(screen.getByRole('button', { name: 'Abrir' }))
    const confirmarBtn = screen.getByRole('button', { name: 'Confirmar' })
    expect(confirmarBtn).toHaveFocus()
    expect(confirmarBtn).toHaveClass('boton-peligro')
  })

  it('Tab desde el botón de confirmar vuelve al de cancelar (foco atrapado)', async () => {
    renderProbador()
    await userEvent.click(screen.getByRole('button', { name: 'Abrir' }))
    await userEvent.tab()
    expect(screen.getByRole('button', { name: 'Cancelar' })).toHaveFocus()
  })
})
