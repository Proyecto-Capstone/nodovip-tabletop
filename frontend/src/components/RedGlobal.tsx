// Fondo animado del inicio de sesión: un globo de puntos que gira con Quito
// como nodo central, arcos de conexión hacia otras ciudades por los que viajan
// paquetes de datos, una órbita con un satélite y una constelación de nodos.
// Es solo decorativo (aria-hidden). Respeta "reducir movimiento" (dibuja un
// cuadro fijo) y se pausa cuando la pestaña o el lienzo no están visibles.

import { useEffect, useRef } from 'react'

type Vec = [number, number, number]

const GRADO = Math.PI / 180
const ACENTO = '42, 99, 216'
const CLARO = '143, 176, 245'
const BLANCO = '235, 241, 255'

// [latitud, longitud] de los nodos. El primero (Quito) es el centro de la red.
const CIUDADES: [number, number][] = [
  [-0.18, -78.47], // Quito
  [4.71, -74.07], // Bogotá
  [-12.05, -77.04], // Lima
  [25.76, -80.19], // Miami
  [19.43, -99.13], // Ciudad de México
  [-23.55, -46.63], // São Paulo
  [-33.45, -70.67], // Santiago
  [40.71, -74.0], // Nueva York
  [34.05, -118.24], // Los Ángeles
  [40.42, -3.7], // Madrid
  [51.51, -0.13], // Londres
  [50.11, 8.68], // Frankfurt
  [6.52, 3.38], // Lagos
  [35.68, 139.69], // Tokio
  [1.35, 103.82], // Singapur
  [-33.87, 151.21], // Sídney
]

const ENLACES: [number, number][] = [
  [0, 1],
  [0, 2],
  [0, 3],
  [0, 4],
  [0, 5],
  [0, 6],
  [0, 7],
  [0, 9],
  [0, 8],
  [3, 7],
  [7, 10],
  [9, 10],
  [10, 11],
  [9, 12],
  [5, 12],
  [11, 14],
  [13, 14],
  [14, 15],
  [8, 13],
  [4, 8],
  [2, 6],
  [1, 3],
]

function aVector(lat: number, lon: number): Vec {
  const la = lat * GRADO
  const lo = lon * GRADO
  return [Math.cos(la) * Math.sin(lo), Math.sin(la), Math.cos(la) * Math.cos(lo)]
}

// Contornos simplificados de los continentes, [longitud, latitud]. Solo sirven
// para decidir qué puntos del globo son tierra: no pretenden ser un mapa exacto.
const CONTINENTES: [number, number][][] = [
  // América del Norte y Central
  [
    [-168, 66],
    [-162, 70],
    [-140, 70],
    [-125, 71],
    [-95, 72],
    [-80, 73],
    [-62, 66],
    [-55, 52],
    [-66, 45],
    [-70, 41],
    [-76, 35],
    [-81, 31],
    [-80, 25],
    [-82, 27],
    [-84, 30],
    [-90, 29],
    [-97, 26],
    [-97, 21],
    [-90, 21],
    [-87, 21],
    [-88, 15],
    [-83, 9],
    [-79, 8],
    [-81, 7],
    [-86, 12],
    [-92, 15],
    [-105, 20],
    [-112, 29],
    [-117, 33],
    [-124, 40],
    [-124, 48],
    [-133, 57],
    [-150, 60],
    [-158, 57],
    [-165, 61],
  ],
  // Groenlandia
  [
    [-73, 78],
    [-60, 82],
    [-30, 83],
    [-20, 77],
    [-22, 70],
    [-40, 64],
    [-50, 61],
    [-55, 68],
  ],
  // América del Sur
  [
    [-80, 8],
    [-72, 12],
    [-62, 10],
    [-52, 5],
    [-35, -5],
    [-39, -15],
    [-48, -25],
    [-58, -35],
    [-65, -41],
    [-68, -52],
    [-74, -52],
    [-73, -40],
    [-71, -30],
    [-70, -18],
    [-76, -14],
    [-81, -5],
    [-80, 0],
    [-78, 2],
  ],
  // Europa y Asia
  [
    [-10, 36],
    [-9, 43],
    [-2, 44],
    [-5, 48],
    [2, 51],
    [5, 53],
    [8, 57],
    [5, 62],
    [14, 68],
    [25, 71],
    [40, 68],
    [60, 70],
    [80, 73],
    [105, 78],
    [140, 73],
    [180, 69],
    [175, 62],
    [160, 60],
    [155, 51],
    [142, 47],
    [135, 43],
    [128, 35],
    [121, 31],
    [121, 23],
    [110, 20],
    [106, 10],
    [100, 13],
    [103, 1],
    [98, 8],
    [93, 20],
    [88, 22],
    [80, 15],
    [77, 8],
    [72, 20],
    [66, 25],
    [57, 26],
    [52, 28],
    [48, 30],
    [56, 24],
    [59, 22],
    [52, 16],
    [44, 12],
    [35, 30],
    [35, 36],
    [28, 41],
    [23, 37],
    [15, 40],
    [12, 44],
    [8, 44],
    [3, 42],
    [-1, 37],
  ],
  // Gran Bretaña
  [
    [-5, 50],
    [1, 51],
    [0, 53],
    [-2, 57],
    [-5, 58],
    [-6, 55],
    [-4, 53],
  ],
  // África
  [
    [-17, 15],
    [-17, 21],
    [-10, 30],
    [-6, 36],
    [10, 37],
    [20, 32],
    [32, 31],
    [35, 28],
    [43, 12],
    [51, 12],
    [50, 2],
    [40, -10],
    [40, -16],
    [35, -25],
    [28, -33],
    [19, -35],
    [15, -25],
    [12, -15],
    [13, -5],
    [9, 4],
    [0, 5],
    [-8, 4],
    [-13, 8],
  ],
  // Madagascar
  [
    [44, -25],
    [47, -25],
    [50, -15],
    [49, -12],
    [44, -17],
  ],
  // Australia
  [
    [114, -22],
    [122, -18],
    [130, -12],
    [137, -12],
    [142, -11],
    [146, -19],
    [153, -26],
    [150, -37],
    [141, -38],
    [135, -35],
    [129, -32],
    [115, -34],
    [113, -26],
  ],
  // Japón
  [
    [130, 31],
    [135, 34],
    [140, 36],
    [142, 40],
    [141, 45],
    [144, 44],
    [140, 41],
    [136, 37],
    [131, 34],
  ],
  // Borneo y Sumatra
  [
    [109, 2],
    [118, 7],
    [119, 1],
    [116, -4],
    [110, -3],
  ],
  [
    [95, 5],
    [106, -6],
    [104, -6],
    [98, 1],
  ],
  // Nueva Zelanda
  [
    [172, -34],
    [178, -38],
    [174, -41],
    [167, -46],
    [170, -44],
    [173, -40],
  ],
]

function dentroDe(lon: number, lat: number, poligono: [number, number][]): boolean {
  let dentro = false
  for (let i = 0, j = poligono.length - 1; i < poligono.length; j = i++) {
    const [xi, yi] = poligono[i]
    const [xj, yj] = poligono[j]
    if (yi > lat !== yj > lat && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) {
      dentro = !dentro
    }
  }
  return dentro
}

function esTierra(v: Vec): boolean {
  const lat = Math.asin(v[1]) / GRADO
  const lon = Math.atan2(v[0], v[2]) / GRADO
  return CONTINENTES.some((poligono) => dentroDe(lon, lat, poligono))
}

/** Puntos repartidos de forma uniforme sobre la esfera (espiral de Fibonacci). */
function esferaDePuntos(n: number): Vec[] {
  const puntos: Vec[] = []
  const aureo = Math.PI * (3 - Math.sqrt(5))
  for (let i = 0; i < n; i++) {
    const y = 1 - (2 * (i + 0.5)) / n
    const radio = Math.sqrt(1 - y * y)
    const theta = aureo * i
    puntos.push([Math.cos(theta) * radio, y, Math.sin(theta) * radio])
  }
  return puntos
}

/** Interpolación esférica entre dos vectores unitarios. */
function slerp(a: Vec, b: Vec, t: number): Vec {
  const punto = Math.min(1, Math.max(-1, a[0] * b[0] + a[1] * b[1] + a[2] * b[2]))
  const omega = Math.acos(punto)
  if (omega < 1e-4) return a
  const s = Math.sin(omega)
  const ka = Math.sin((1 - t) * omega) / s
  const kb = Math.sin(t * omega) / s
  return [a[0] * ka + b[0] * kb, a[1] * ka + b[1] * kb, a[2] * ka + b[2] * kb]
}

interface Paquete {
  enlace: number
  t: number
  velocidad: number
  ida: boolean
}

interface Particula {
  x: number
  y: number
  vx: number
  vy: number
}

export function RedGlobal({ className }: { className?: string }) {
  const lienzoRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    // Sin estos observadores (navegadores muy antiguos, jsdom en las pruebas)
    // el fondo queda liso: es decorativo y el login funciona igual.
    if (typeof ResizeObserver === 'undefined' || typeof IntersectionObserver === 'undefined') {
      return
    }
    const lienzo = lienzoRef.current
    const ctx = lienzo?.getContext('2d')
    if (!lienzo || !ctx) return

    const reducirMovimiento = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    // Tierra: puntos densos y brillantes. Océano: una malla tenue de fondo.
    const todos = esferaDePuntos(16000)
    const tierra = todos.filter(esTierra)
    const oceano = todos.filter((v, i) => i % 8 === 0 && !esTierra(v))
    const ciudades = CIUDADES.map(([lat, lon]) => aVector(lat, lon))
    // Inclinado hacia el espectador (se ve más el hemisferio norte). El globo
    // oscila con Quito siempre de frente en vez de dar la vuelta completa.
    const inclinacion = 0.3
    const centroRotacion = 62 * GRADO
    let rotacion = centroRotacion
    let reloj = 0
    let ancho = 0
    let alto = 0
    let cx = 0
    let cy = 0
    let radio = 0
    let particulas: Particula[] = []
    const paquetes: Paquete[] = []

    const proyectar = (v: Vec, escala = 1): [number, number, number] => {
      const c = Math.cos(rotacion)
      const s = Math.sin(rotacion)
      const x = v[0] * c + v[2] * s
      const z0 = -v[0] * s + v[2] * c
      const ci = Math.cos(inclinacion)
      const si = Math.sin(inclinacion)
      const y = v[1] * ci - z0 * si
      const z = v[1] * si + z0 * ci
      return [cx + x * radio * escala, cy - y * radio * escala, z]
    }

    const medir = () => {
      const caja = lienzo.getBoundingClientRect()
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      ancho = caja.width
      alto = caja.height
      lienzo.width = Math.round(ancho * dpr)
      lienzo.height = Math.round(alto * dpr)
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      if (ancho < 700) {
        // Cabecera del móvil: globo pequeño asomando por la derecha.
        radio = Math.min(alto * 0.62, 150)
        cx = ancho - radio * 0.55
        cy = radio * 0.75
      } else {
        radio = Math.min(ancho * 0.3, alto * 0.27)
        cx = ancho / 2
        cy = alto * 0.43
      }
      const cantidad = Math.round(Math.min(70, (ancho * alto) / 16000))
      particulas = Array.from({ length: cantidad }, () => ({
        x: Math.random() * ancho,
        y: Math.random() * alto,
        vx: (Math.random() - 0.5) * 12,
        vy: (Math.random() - 0.5) * 12,
      }))
    }

    const nuevoPaquete = () => {
      const enlace = Math.floor(Math.random() * ENLACES.length)
      paquetes.push({
        enlace,
        t: 0,
        velocidad: 0.25 + Math.random() * 0.25,
        ida: Math.random() < 0.5,
      })
    }

    const alturas = ENLACES.map(([a, b]) => {
      const va = ciudades[a]
      const vb = ciudades[b]
      const angulo = Math.acos(va[0] * vb[0] + va[1] * vb[1] + va[2] * vb[2])
      return 0.04 + 0.16 * (angulo / Math.PI)
    })

    const puntoDelArco = (enlace: number, t: number): [number, number, number] => {
      const [a, b] = ENLACES[enlace]
      const v = slerp(ciudades[a], ciudades[b], t)
      return proyectar(v, 1 + alturas[enlace] * Math.sin(Math.PI * t))
    }

    const dibujarConstelacion = (dt: number) => {
      for (const p of particulas) {
        p.x += p.vx * dt
        p.y += p.vy * dt
        if (p.x < 0 || p.x > ancho) p.vx *= -1
        if (p.y < 0 || p.y > alto) p.vy *= -1
      }
      const maximo = 130
      ctx.lineWidth = 1
      for (let i = 0; i < particulas.length; i++) {
        const a = particulas[i]
        for (let j = i + 1; j < particulas.length; j++) {
          const b = particulas[j]
          const d = Math.hypot(a.x - b.x, a.y - b.y)
          if (d < maximo) {
            ctx.strokeStyle = `rgba(${CLARO}, ${0.14 * (1 - d / maximo)})`
            ctx.beginPath()
            ctx.moveTo(a.x, a.y)
            ctx.lineTo(b.x, b.y)
            ctx.stroke()
          }
        }
        ctx.fillStyle = `rgba(${CLARO}, 0.4)`
        ctx.beginPath()
        ctx.arc(a.x, a.y, 1.3, 0, Math.PI * 2)
        ctx.fill()
      }
    }

    const dibujarOrbita = (tiempo: number) => {
      const rx = radio * 1.42
      const ry = radio * 0.36
      ctx.save()
      ctx.translate(cx, cy)
      ctx.rotate(-0.38)
      ctx.setLineDash([2, 7])
      ctx.strokeStyle = `rgba(${CLARO}, 0.35)`
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.ellipse(0, 0, rx, ry, 0, 0, Math.PI * 2)
      ctx.stroke()
      ctx.setLineDash([])
      const angulo = tiempo * 0.00035
      const sx = Math.cos(angulo) * rx
      const sy = Math.sin(angulo) * ry
      const brillo = ctx.createRadialGradient(sx, sy, 0, sx, sy, 10)
      brillo.addColorStop(0, `rgba(${BLANCO}, 0.95)`)
      brillo.addColorStop(1, `rgba(${ACENTO}, 0)`)
      ctx.fillStyle = brillo
      ctx.beginPath()
      ctx.arc(sx, sy, 10, 0, Math.PI * 2)
      ctx.fill()
      ctx.restore()
    }

    const dibujarGlobo = (tiempo: number) => {
      // Halo atmosférico.
      const halo = ctx.createRadialGradient(cx, cy, radio * 0.6, cx, cy, radio * 1.6)
      halo.addColorStop(0, `rgba(${ACENTO}, 0.32)`)
      halo.addColorStop(0.45, `rgba(${ACENTO}, 0.1)`)
      halo.addColorStop(1, `rgba(${ACENTO}, 0)`)
      ctx.fillStyle = halo
      ctx.beginPath()
      ctx.arc(cx, cy, radio * 1.6, 0, Math.PI * 2)
      ctx.fill()

      // Cuerpo del globo con luz desde arriba a la izquierda.
      const cuerpo = ctx.createRadialGradient(
        cx - radio * 0.35,
        cy - radio * 0.4,
        radio * 0.1,
        cx,
        cy,
        radio,
      )
      cuerpo.addColorStop(0, 'rgba(44, 76, 160, 0.35)')
      cuerpo.addColorStop(1, 'rgba(20, 22, 44, 0.75)')
      ctx.fillStyle = cuerpo
      ctx.beginPath()
      ctx.arc(cx, cy, radio, 0, Math.PI * 2)
      ctx.fill()
      ctx.strokeStyle = `rgba(${CLARO}, 0.35)`
      ctx.lineWidth = 1.2
      ctx.stroke()

      // Océano: malla tenue solo en la cara visible.
      ctx.fillStyle = `rgba(${CLARO}, 0.13)`
      for (const p of oceano) {
        const [x, y, z] = proyectar(p)
        if (z < 0.05) continue
        ctx.fillRect(x - 0.6, y - 0.6, 1.2, 1.2)
      }
      // Continentes: más brillantes hacia el centro de la cara visible.
      for (const p of tierra) {
        const [x, y, z] = proyectar(p)
        if (z < 0) continue
        ctx.fillStyle = `rgba(${CLARO}, ${0.25 + z * 0.65})`
        const tam = 0.9 + z * 0.9
        ctx.fillRect(x - tam / 2, y - tam / 2, tam, tam)
      }

      // Arcos de conexión.
      ctx.lineWidth = 1.1
      for (let e = 0; e < ENLACES.length; e++) {
        let previo: [number, number, number] | null = null
        for (let k = 0; k <= 28; k++) {
          const actual = puntoDelArco(e, k / 28)
          if (previo && previo[2] > -0.05 && actual[2] > -0.05) {
            const alfa = 0.12 + Math.max(0, (previo[2] + actual[2]) / 2) * 0.38
            ctx.strokeStyle = `rgba(${CLARO}, ${alfa})`
            ctx.beginPath()
            ctx.moveTo(previo[0], previo[1])
            ctx.lineTo(actual[0], actual[1])
            ctx.stroke()
          }
          previo = actual
        }
      }

      // Paquetes de datos con estela.
      for (const p of paquetes) {
        for (let k = 6; k >= 0; k--) {
          const t = p.t - k * 0.018
          if (t < 0) continue
          const [x, y, z] = puntoDelArco(p.enlace, p.ida ? t : 1 - t)
          if (z < -0.05) continue
          const alfa = (1 - k / 7) * (0.35 + z * 0.65)
          ctx.fillStyle = k === 0 ? `rgba(${BLANCO}, ${alfa})` : `rgba(${CLARO}, ${alfa * 0.7})`
          ctx.beginPath()
          ctx.arc(x, y, k === 0 ? 2.4 : 1.6, 0, Math.PI * 2)
          ctx.fill()
        }
      }

      // Nodos de las ciudades; Quito con pulsos.
      ciudades.forEach((v, i) => {
        const [x, y, z] = proyectar(v)
        if (z < 0) return
        if (i === 0) {
          for (let onda = 0; onda < 3; onda++) {
            const fase = (((tiempo / 2400 + onda / 3) % 1) + 1) % 1
            ctx.strokeStyle = `rgba(${CLARO}, ${(1 - fase) * 0.7 * z})`
            ctx.lineWidth = 1.4
            ctx.beginPath()
            ctx.arc(x, y, 4 + fase * 26, 0, Math.PI * 2)
            ctx.stroke()
          }
        }
        const r = i === 0 ? 4.2 : 2.6
        const brillo = ctx.createRadialGradient(x, y, 0, x, y, r * 3.2)
        brillo.addColorStop(0, `rgba(${BLANCO}, ${0.9 * z + 0.1})`)
        brillo.addColorStop(0.35, `rgba(${CLARO}, ${0.6 * z})`)
        brillo.addColorStop(1, `rgba(${ACENTO}, 0)`)
        ctx.fillStyle = brillo
        ctx.beginPath()
        ctx.arc(x, y, r * 3.2, 0, Math.PI * 2)
        ctx.fill()
      })
    }

    let anterior = performance.now()
    let siguientePaquete = 0
    const cuadro = (ahora: number) => {
      const dt = Math.min(0.05, (ahora - anterior) / 1000)
      anterior = ahora
      reloj += dt
      rotacion = centroRotacion + 0.9 * Math.sin((reloj * 2 * Math.PI) / 90)
      siguientePaquete -= dt
      if (siguientePaquete <= 0 && paquetes.length < 14) {
        nuevoPaquete()
        siguientePaquete = 0.35 + Math.random() * 0.5
      }
      for (const p of paquetes) p.t += dt * p.velocidad
      for (let i = paquetes.length - 1; i >= 0; i--) {
        if (paquetes[i].t > 1.12) paquetes.splice(i, 1)
      }
      ctx.clearRect(0, 0, ancho, alto)
      dibujarConstelacion(dt)
      dibujarOrbita(ahora)
      dibujarGlobo(ahora)
    }

    medir()
    let idCuadro = 0
    let visible = true
    const bucle = (ahora: number) => {
      cuadro(ahora)
      idCuadro = requestAnimationFrame(bucle)
    }
    const arrancar = () => {
      if (reducirMovimiento || idCuadro || !visible || document.hidden) return
      anterior = performance.now()
      idCuadro = requestAnimationFrame(bucle)
    }
    const detener = () => {
      cancelAnimationFrame(idCuadro)
      idCuadro = 0
    }

    if (reducirMovimiento) {
      // Cuadro fijo con algunos paquetes en camino.
      for (let i = 0; i < 8; i++) {
        nuevoPaquete()
        paquetes[i].t = 0.2 + Math.random() * 0.6
      }
      cuadro(performance.now())
    } else {
      arrancar()
    }

    const alCambiarTamano = new ResizeObserver(() => {
      medir()
      if (reducirMovimiento) cuadro(performance.now())
    })
    alCambiarTamano.observe(lienzo)
    const alVer = new IntersectionObserver(([entrada]) => {
      visible = entrada.isIntersecting
      if (visible) arrancar()
      else detener()
    })
    alVer.observe(lienzo)
    const alCambiarPestana = () => (document.hidden ? detener() : arrancar())
    document.addEventListener('visibilitychange', alCambiarPestana)

    return () => {
      detener()
      alCambiarTamano.disconnect()
      alVer.disconnect()
      document.removeEventListener('visibilitychange', alCambiarPestana)
    }
  }, [])

  return <canvas ref={lienzoRef} className={className} aria-hidden="true" />
}
