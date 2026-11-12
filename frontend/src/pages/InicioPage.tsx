// Portada después del login: el logo de NODOVIP, un saludo y los accesos
// directos a las secciones que el rol del usuario puede usar (los mismos que
// el menú lateral, filtrados por permisos).

import { Link } from 'react-router-dom'
import logoNodovip from '../assets/marca/nodovip-horizontal-claro.webp'
import { nombreRolSistema, useSesion } from '../auth/sesionContext'
import { useGruposNav } from '../components/navegacion'

export function InicioPage() {
  const { usuario } = useSesion()
  const accesos = useGruposNav()
    .flatMap((g) => g.enlaces)
    .filter((e) => e.mostrar && e.to !== '/')
  const nombre = usuario?.nombre.split(/\s+/)[0]

  return (
    <div className="portada">
      <div className="portada-hero">
        <div className="portada-halo" aria-hidden="true" />
        <img
          className="portada-logo"
          src={logoNodovip}
          alt="NODOVIP — Conectamos tu mundo digital"
          width={720}
          height={206}
        />
        <p className="portada-producto">Tabletop Exercise</p>
        <h1 className="portada-saludo">
          {nombre ? `Hola, ${nombre}` : 'Bienvenido'}
          {usuario && <span>{nombreRolSistema(usuario.rol)}</span>}
        </h1>
        <p className="portada-texto">
          Plataforma de ejercicios tabletop de ciberseguridad. Elige por dónde empezar.
        </p>
      </div>

      <nav className="portada-dock" aria-label="Accesos directos">
        {accesos.map(({ to, texto, corto, icono: Icono }) => (
          <Link key={to} to={to} className="portada-acceso" title={texto}>
            <span className="portada-acceso-icono" aria-hidden="true">
              <Icono />
            </span>
            <span className="portada-acceso-texto">{corto ?? texto}</span>
            {corto && corto !== texto && <span className="solo-lector"> ({texto})</span>}
          </Link>
        ))}
      </nav>
    </div>
  )
}
