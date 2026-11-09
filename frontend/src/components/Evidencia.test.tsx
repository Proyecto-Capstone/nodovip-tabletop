import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'
import type { Evidencia, TipoEvidencia } from '../api/escenarios'
import { EditorEvidencia, EvidenciaSimulada } from './Evidencia'

function EditorConEstado({ inicial = null }: { inicial?: Evidencia | null }) {
  const [valor, setValor] = useState<Evidencia | null>(inicial)
  return (
    <>
      <EditorEvidencia valor={valor} onChange={setValor} />
      <output data-testid="valor">{JSON.stringify(valor)}</output>
    </>
  )
}

const valorActual = () => JSON.parse(screen.getByTestId('valor').textContent ?? 'null')

describe('Editor de evidencia simulada (PC-44)', () => {
  it('es opcional: se agrega, se completa y se quita', async () => {
    render(<EditorConEstado />)
    expect(valorActual()).toBeNull()

    await userEvent.click(screen.getByRole('button', { name: /Agregar evidencia simulada/ }))
    expect(screen.getByLabelText('Remitente')).toBeInTheDocument()
    await userEvent.type(screen.getByLabelText('Remitente'), 'rrhh@empresa-ficticia.test')
    await userEvent.type(screen.getByLabelText('Asunto'), 'Actualice su nómina')
    expect(valorActual()).toMatchObject({
      tipo: 'correo',
      origen: 'rrhh@empresa-ficticia.test',
      asunto: 'Actualice su nómina',
      nivel: null,
    })

    await userEvent.click(screen.getByRole('button', { name: 'Quitar evidencia' }))
    expect(valorActual()).toBeNull()
  })

  it('la severidad solo aparece en las alertas y los campos cambian de nombre', async () => {
    render(<EditorConEstado />)
    await userEvent.click(screen.getByRole('button', { name: /Agregar evidencia simulada/ }))
    expect(screen.queryByLabelText('Severidad')).toBeNull()

    await userEvent.selectOptions(screen.getByLabelText('Tipo'), 'alerta')
    expect(screen.getByLabelText('Severidad')).toHaveValue('alta')
    expect(screen.getByLabelText('Sistema que la genera')).toBeInTheDocument()
    expect(valorActual().nivel).toBe('alta')

    await userEvent.selectOptions(screen.getByLabelText('Tipo'), 'noticia')
    expect(screen.queryByLabelText('Severidad')).toBeNull()
    expect(screen.getByLabelText('Titular')).toBeInTheDocument()
    expect(valorActual().nivel).toBeNull()
  })
})

describe('Evidencia simulada', () => {
  const base = { origen: 'Origen ficticio', asunto: 'Asunto de prueba', contenido: 'Contenido' }
  const casos: [TipoEvidencia, RegExp][] = [
    ['correo', /Correo electrónico/],
    ['alerta', /Alerta de seguridad/],
    ['noticia', /Noticia/],
    ['llamada', /Llamada telefónica/],
    ['mensaje', /Mensaje de chat/],
    ['documento', /Documento/],
  ]

  it.each(casos)('muestra un %s con su propio formato', (tipo, nombre) => {
    render(
      <EvidenciaSimulada
        evidencia={{ ...base, tipo, nivel: tipo === 'alerta' ? 'critica' : null }}
      />,
    )
    const articulo = screen.getByRole('article', { name: nombre })
    expect(articulo).toHaveClass(`evidencia-${tipo}`)
    expect(screen.getByText('Contenido')).toBeInTheDocument()
  })
})
