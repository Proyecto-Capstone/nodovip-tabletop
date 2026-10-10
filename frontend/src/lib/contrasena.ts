// Misma política de contraseñas que el backend (domain/usuarios.py), para guiar
// al administrador mientras escribe. El backend vuelve a validarla siempre.

export function reglasContrasena(valor: string) {
  const bytes = new TextEncoder().encode(valor).length
  return [
    { ok: valor.length >= 10, texto: 'Al menos 10 caracteres' },
    { ok: /[a-zà-ÿñ]/.test(valor), texto: 'Una letra minúscula' },
    { ok: /[A-ZÀ-ÝÑ]/.test(valor), texto: 'Una letra mayúscula' },
    { ok: /\d/.test(valor), texto: 'Un número' },
    { ok: valor === valor.trim(), texto: 'Sin espacios al inicio ni al final' },
    { ok: bytes <= 72, texto: 'Máximo 72 bytes' },
  ]
}

export function contrasenaValida(valor: string) {
  return reglasContrasena(valor).every((r) => r.ok)
}
