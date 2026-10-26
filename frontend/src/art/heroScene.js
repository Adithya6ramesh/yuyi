/*
  THE 3D WIREFRAME HERO: a wind turbine on rippling terrain, with wind streaks.
  Ported unchanged from design/Main.dc.html.

  How it works, simply: every point has 3D coordinates (x, y, z). project() turns the
  scene by the "yaw" angle, tilts it by "pitch", then divides by depth so far things
  look smaller (perspective). The result is 2D screen points that we join into SVG
  path strings ("M x y L x y ...").

  heroScene(t) -> { terrain, tower, blades, wind, yawDeg, rpm }   (t = seconds)
*/

const ROTOR_SPEED = 1.3 // radians per second

export function heroScene(t) {
  const yaw = 0.75 + t * 0.12
  const pitch = 0.42
  const D = 14 // camera distance
  const F = 560 // focal length (zoom)
  const CX = 420 // screen centre
  const CY = 410
  const cosYaw = Math.cos(yaw)
  const sinYaw = Math.sin(yaw)
  const cosPitch = Math.cos(pitch)
  const sinPitch = Math.sin(pitch)

  const project = (x, y, z) => {
    const x1 = x * cosYaw - z * sinYaw
    const z1 = x * sinYaw + z * cosYaw
    const y2 = y * cosPitch + z1 * sinPitch
    const z2 = -y * sinPitch + z1 * cosPitch
    const scale = F / (z2 + D)
    return `${(CX + x1 * scale).toFixed(1)} ${(CY - y2 * scale).toFixed(1)}`
  }
  const poly = (points) => `M${points.join(' L')} `

  // --- rippling terrain: a 21 x 21 grid whose height moves with time ---
  const height = (x, z) =>
    -0.5 +
    0.32 * Math.sin(x * 0.75 + t * 1.1) * Math.cos(z * 0.55 - t * 0.6) +
    0.18 * Math.sin((x - z) * 1.1 + t * 1.7)
  const n = 20
  const step = 0.6
  let terrain = ''
  for (let j = 0; j <= n; j++) {
    const z = -6 + j * step
    const row = []
    for (let i = 0; i <= n; i++) {
      const x = -6 + i * step
      row.push(project(x, height(x, z), z))
    }
    terrain += poly(row)
  }
  for (let i = 0; i <= n; i++) {
    const x = -6 + i * step
    const column = []
    for (let j = 0; j <= n; j++) {
      const z = -6 + j * step
      column.push(project(x, height(x, z), z))
    }
    terrain += poly(column)
  }

  // --- tower: 4 rings joined by 4 vertical lines, narrowing towards the top ---
  let tower = ''
  const rings = [-0.5, 1.0, 2.5, 4.15]
  const radius = (y) => 0.24 - 0.025 * (y + 0.5)
  const sides = 8
  const ringPoint = (k, y) => {
    const a = (k / sides) * Math.PI * 2
    return project(Math.cos(a) * radius(y), y, Math.sin(a) * radius(y))
  }
  rings.forEach((y) => {
    const points = []
    for (let k = 0; k <= sides; k++) points.push(ringPoint(k, y))
    tower += poly(points)
  })
  for (let k = 0; k < sides; k += 2) tower += poly(rings.map((y) => ringPoint(k, y)))

  // --- nacelle: the box on top of the tower ---
  const bx = [-0.22, 0.22]
  const by = [4.1, 4.45]
  const bz = [-0.7, 0.35]
  const corner = (i, j, k) => project(bx[i], by[j], bz[k])
  tower += poly([corner(0, 0, 0), corner(1, 0, 0), corner(1, 1, 0), corner(0, 1, 0), corner(0, 0, 0)])
  tower += poly([corner(0, 0, 1), corner(1, 0, 1), corner(1, 1, 1), corner(0, 1, 1), corner(0, 0, 1)])
  tower += poly([corner(0, 0, 0), corner(0, 0, 1)]) + poly([corner(1, 0, 0), corner(1, 0, 1)])
  tower += poly([corner(1, 1, 0), corner(1, 1, 1)]) + poly([corner(0, 1, 0), corner(0, 1, 1)])

  // --- hub and 3 spinning blades ---
  const hub = [0, 4.28, 0.5]
  const hubPoints = []
  for (let k = 0; k <= 8; k++) {
    const a = (k / 8) * Math.PI * 2
    hubPoints.push(project(hub[0] + Math.cos(a) * 0.16, hub[1] + Math.sin(a) * 0.16, hub[2]))
  }
  let blades = poly(hubPoints)
  const spin = t * ROTOR_SPEED
  for (let k = 0; k < 3; k++) {
    const a = spin + (k * Math.PI * 2) / 3
    const dx = Math.cos(a)
    const dy = Math.sin(a)
    // a point `along` the blade and `side` across it
    const at = (along, side) =>
      project(hub[0] + dx * along - dy * side, hub[1] + dy * along + dx * side, hub[2])
    blades += poly([at(0.16, 0.08), at(0.9, 0.2), at(2.9, 0.02), at(0.9, -0.07), at(0.16, -0.06), at(0.16, 0.08)])
    blades += poly([at(0.16, 0), at(2.9, 0)])
  }

  // --- 9 wind streaks drifting across the scene ---
  let wind = ''
  for (let k = 0; k < 9; k++) {
    const z = -5 + k * 1.25
    const x = ((t * 2.2 + k * 1.7) % 13) - 6.5
    const y = 1.4 + 0.9 * Math.sin(k * 1.9) + 0.15 * Math.sin(t * 2 + k)
    const points = []
    for (let s = 0; s <= 4; s++) {
      const xx = x + s * 0.3
      points.push(project(xx, y + 0.08 * Math.sin(xx * 2 + t * 3), z))
    }
    wind += poly(points)
  }

  const degrees = (((yaw * 180) / Math.PI) % 360 + 360) % 360
  return {
    terrain,
    tower,
    blades,
    wind,
    yawDeg: String(Math.round(degrees)).padStart(3, '0'),
    rpm: ((ROTOR_SPEED / (2 * Math.PI)) * 60).toFixed(1),
  }
}
