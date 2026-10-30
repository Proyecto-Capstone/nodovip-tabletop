import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { SesionProvider } from './auth/SesionProvider'
import { Layout } from './components/Layout'
import { RutaProtegida } from './components/RutaProtegida'
import { AccesosPage } from './pages/AccesosPage'
import { BancoPreguntasPage } from './pages/BancoPreguntasPage'
import { BibliotecaPage } from './pages/BibliotecaPage'
import { ConducirSesionPage } from './pages/ConducirSesionPage'
import { DisenadorPage } from './pages/DisenadorPage'
import { EscenarioDetallePage } from './pages/EscenarioDetallePage'
import { EscenarioFormPage } from './pages/EscenarioFormPage'
import { InicioPage } from './pages/InicioPage'
import { LeaderboardPage } from './pages/LeaderboardPage'
import { LeaderboardSesionPage } from './pages/LeaderboardSesionPage'
import { LoginPage } from './pages/LoginPage'
import { NuevaSesionPage } from './pages/NuevaSesionPage'
import { RespuestasSesionPage } from './pages/RespuestasSesionPage'
import { ReportePage } from './pages/ReportePage'
import { ReportesPage } from './pages/ReportesPage'
import { MiSesionPage } from './pages/MiSesionPage'
import { MisSesionesPage } from './pages/MisSesionesPage'
import { MonitoreoPage } from './pages/MonitoreoPage'
import { MonitoreoSesionPage } from './pages/MonitoreoSesionPage'
import { SesionEnVivoPage } from './pages/SesionEnVivoPage'
import { SesionesPage } from './pages/SesionesPage'
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
              <Route element={<RutaProtegida permiso="sesiones:disenar" />}>
                <Route path="sesiones" element={<SesionesPage />} />
                <Route path="sesiones/nueva" element={<NuevaSesionPage />} />
                <Route path="sesiones/:id/disenar" element={<DisenadorPage />} />
              </Route>
              <Route element={<RutaProtegida permiso="sesiones:conducir" />}>
                <Route path="sesiones/:id/conducir" element={<ConducirSesionPage />} />
                <Route path="sesiones/:id/respuestas" element={<RespuestasSesionPage />} />
              </Route>
              <Route element={<RutaProtegida permiso="reportes:ver" />}>
                <Route path="reportes" element={<ReportesPage />} />
                <Route path="reportes/:id" element={<ReportePage />} />
              </Route>
              <Route element={<RutaProtegida permiso="leaderboard:ver" />}>
                <Route path="leaderboard" element={<LeaderboardPage />} />
                <Route path="leaderboard/:id" element={<LeaderboardSesionPage />} />
              </Route>
              <Route element={<RutaProtegida permiso="sesiones:monitorear" />}>
                <Route path="monitoreo" element={<MonitoreoPage />} />
                <Route path="monitoreo/:id" element={<MonitoreoSesionPage />} />
              </Route>
              <Route element={<RutaProtegida permiso="sesiones:participar" />}>
                <Route path="mis-sesiones" element={<MisSesionesPage />} />
                <Route path="mis-sesiones/:id" element={<MiSesionPage />} />
                <Route path="mis-sesiones/:id/en-vivo" element={<SesionEnVivoPage />} />
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
