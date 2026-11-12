// Nivel de color de un porcentaje de logro: verde ≥ 70 %, naranja ≥ 40 % y
// rojo por debajo (los mismos umbrales del reporte y del leaderboard).

export type NivelColor = 'verde' | 'naranja' | 'rojo'

export function nivelDePorcentaje(porcentaje: number): NivelColor {
  return porcentaje >= 70 ? 'verde' : porcentaje >= 40 ? 'naranja' : 'rojo'
}
