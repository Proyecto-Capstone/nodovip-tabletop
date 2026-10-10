import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { RolProvider } from './auth/RolProvider'
import { Layout } from './components/Layout'
import { BancoPreguntasPage } from './pages/BancoPreguntasPage'
import { BibliotecaPage } from './pages/BibliotecaPage'
import { EscenarioDetallePage } from './pages/EscenarioDetallePage'
import { EscenarioFormPage } from './pages/EscenarioFormPage'
import { UsuariosPage } from './pages/UsuariosPage'

export default function App() {
  return (
    <RolProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Navigate to="/escenarios" replace />} />
            <Route path="escenarios" element={<BibliotecaPage />} />
            <Route path="escenarios/nuevo" element={<EscenarioFormPage />} />
            <Route path="escenarios/:id" element={<EscenarioDetallePage />} />
            <Route path="escenarios/:id/editar" element={<EscenarioFormPage />} />
            <Route path="banco-preguntas" element={<BancoPreguntasPage />} />
            <Route path="usuarios" element={<UsuariosPage />} />
            <Route path="*" element={<Navigate to="/escenarios" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </RolProvider>
  )
}
