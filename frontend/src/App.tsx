import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { SesionProvider } from './auth/SesionProvider'
import { Layout } from './components/Layout'
import { RutaProtegida } from './components/RutaProtegida'
import { AccesosPage } from './pages/AccesosPage'
import { BancoPreguntasPage } from './pages/BancoPreguntasPage'
import { BibliotecaPage } from './pages/BibliotecaPage'
import { EscenarioDetallePage } from './pages/EscenarioDetallePage'
import { EscenarioFormPage } from './pages/EscenarioFormPage'
import { InicioPage } from './pages/InicioPage'
import { LoginPage } from './pages/LoginPage'
import { UsuariosPage } from './pages/UsuariosPage'

export default function App() {
  return (
    <SesionProvider>
      <BrowserRouter>
        <Routes>
          <Route path="login" element={<LoginPage />} />
          <Route element={<RutaProtegida />}>
            <Route element={<Layout />}>
              <Route index element={<InicioPage />} />
              <Route element={<RutaProtegida permiso="escenarios:leer" />}>
                <Route path="escenarios" element={<BibliotecaPage />} />
                <Route path="escenarios/:id" element={<EscenarioDetallePage />} />
                <Route path="banco-preguntas" element={<BancoPreguntasPage />} />
              </Route>
              <Route element={<RutaProtegida permiso="escenarios:gestionar" />}>
                <Route path="escenarios/nuevo" element={<EscenarioFormPage />} />
                <Route path="escenarios/:id/editar" element={<EscenarioFormPage />} />
              </Route>
              <Route element={<RutaProtegida permiso="usuarios:gestionar" />}>
                <Route path="usuarios" element={<UsuariosPage />} />
                <Route path="accesos" element={<AccesosPage />} />
              </Route>
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </SesionProvider>
  )
}
