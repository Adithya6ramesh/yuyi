/*
  THE MINI WIREFRAME MESH in the desk sidebar: a small rippling "wind field" surface.
  Ported unchanged from design/Dashboard.dc.html. Same idea as heroScene.js: turn 3D
  grid points into 2D screen points, then join them into one SVG path.
*/

export function miniMesh(t) {
  const yaw = 0.6 + t * 0.15
  const pitch = 0.5
  const D = 9
  const F = 120
  const CX = 130
  const CY = 80
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
  const height = (x, z) =>
    0.45 * Math.sin(x * 0.9 + t * 1.2) * Math.cos(z * 0.7 - t * 0.7) + 0.2 * Math.sin((x + z) * 1.3 - t * 1.6)

  const n = 14
  const step = 0.6
  let path = ''
  for (let j = 0; j <= n; j++) {
    const z = -4.2 + j * step
    const points = []
    for (let i = 0; i <= n; i++) {
      const x = -4.2 + i * step
      points.push(project(x, height(x, z), z))
    }
    path += `M${points.join(' L')} `
  }
  for (let i = 0; i <= n; i++) {
    const x = -4.2 + i * step
    const points = []
    for (let j = 0; j <= n; j++) {
      const z = -4.2 + j * step
      points.push(project(x, height(x, z), z))
    }
    path += `M${points.join(' L')} `
  }
  return path
}

/** "rendering |", "rendering /", ... a text spinner. */
export const spinner = (t) => `rendering ${['|', '/', '-', '\\'][Math.floor(t * 8) % 4]}`
