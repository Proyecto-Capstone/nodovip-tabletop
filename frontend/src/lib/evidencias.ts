// Nombres de los tipos de evidencia simulada y de los niveles de alerta (PC-44).

import type { NivelAlerta, TipoEvidencia } from '../api/escenarios'

interface TextosTipo {
  nombre: string
  icono: string
  origen: string
  asunto: string
  contenido: string
}

/** Nombre de cada tipo y cómo se llaman sus campos en el formulario. */
export const TIPOS_EVIDENCIA: Record<TipoEvidencia, TextosTipo> = {
  correo: {
    nombre: 'Correo electrónico',
    icono: '✉',
    origen: 'Remitente',
    asunto: 'Asunto',
    contenido: 'Cuerpo del correo',
  },
  alerta: {
    nombre: 'Alerta de seguridad (SIEM, EDR…)',
    icono: '⚠',
    origen: 'Sistema que la genera',
    asunto: 'Título de la alerta',
    contenido: 'Detalle técnico',
  },
  noticia: {
    nombre: 'Noticia o publicación',
    icono: '📰',
    origen: 'Medio o red social',
    asunto: 'Titular',
    contenido: 'Texto de la nota',
  },
  llamada: {
    nombre: 'Llamada telefónica',
    icono: '📞',
    origen: 'Quién llama',
    asunto: 'Motivo',
    contenido: 'Lo que dice (transcripción)',
  },
  mensaje: {
    nombre: 'Mensaje de chat',
    icono: '💬',
    origen: 'Quién escribe',
    asunto: 'Resumen',
    contenido: 'Mensaje',
  },
  documento: {
    nombre: 'Documento',
    icono: '📄',
    origen: 'Emisor',
    asunto: 'Título del documento',
    contenido: 'Contenido',
  },
}

export const NIVELES_ALERTA: Record<NivelAlerta, string> = {
  baja: 'Baja',
  media: 'Media',
  alta: 'Alta',
  critica: 'Crítica',
}
