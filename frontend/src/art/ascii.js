/*
  THE ASCII ANIMATIONS: pictures made of text characters.
  Ported from design/Main.dc.html. Each function takes t (seconds) and returns one
  string with line breaks, ready to put inside a <pre>.
*/

/** The wind field: waves of characters from calm (" ") to strong ("#"). */
export function flowField(t, cols = 132, rows = 12) {
  const ramp = ' .,:-~=+*#'
  const lines = []
  for (let y = 0; y < rows; y++) {
    let line = ''
    for (let x = 0; x < cols; x++) {
      const v =
        Math.sin(x * 0.11 + t * 1.5 + Math.sin(y * 0.45 + t * 0.3) * 1.4) +
        0.7 * Math.sin(y * 0.38 - t * 0.8 + x * 0.04)
      const index = Math.floor(((v + 1.7) / 3.4) * ramp.length)
      line += ramp[Math.max(0, Math.min(ramp.length - 1, index))]
    }
    lines.push(line)
  }
  return lines.join('\n')
}

/** A turbine drawn in text, blades turning, gusts (~-~-~) blowing past. */
export function asciiTurbine(t) {
  const W = 60
  const H = 24
  const hx = 30 // hub position
  const hy = 8
  const grid = Array.from({ length: H }, () => new Array(W).fill(' '))

  // gusts on 4 rows, each moving at its own speed
  ;[2, 5, 13, 16].forEach((row, k) => {
    const offset = Math.floor(t * (5 + k) + row * 7) % W
    for (const start of [offset, (offset + 30) % W]) {
      for (let q = 0; q < 5; q++) grid[row][(start + q) % W] = q % 2 ? '~' : '-'
    }
  })

  // tower, its base, and the ground
  for (let y = hy + 1; y < H - 2; y++) grid[y][hx] = '║'
  for (let y = H - 7; y < H - 2; y++) {
    grid[y][hx - 1] = '/'
    grid[y][hx + 1] = '\\'
  }
  const ground = '▁▁▂▃▂▁▁▁▂▂▁'
  for (let x = 0; x < W; x++) grid[H - 2][x] = ground[x % ground.length]
  grid[H - 2][hx - 1] = '▟'
  grid[H - 2][hx] = '█'
  grid[H - 2][hx + 1] = '▙'

  // 3 blades: pick the character that best matches each blade's angle
  for (let k = 0; k < 3; k++) {
    const a = t * 1.8 + (k * Math.PI * 2) / 3
    const d = ((a % Math.PI) + Math.PI) % Math.PI
    let ch
    if (d < Math.PI / 8 || d > (Math.PI * 7) / 8) ch = '-'
    else if (Math.abs(d - Math.PI / 2) < Math.PI / 8) ch = '|'
    else if (d < Math.PI / 2) ch = '/'
    else ch = '\\'
    for (let s = 1; s <= 9; s++) {
      const x = hx + Math.round(Math.cos(a) * s * 2.1)
      const y = hy - Math.round(Math.sin(a) * s)
      if (y >= 0 && y < H - 2 && x >= 0 && x < W) grid[y][x] = s === 9 ? '◦' : ch
    }
  }
  grid[hy][hx - 1] = '('
  grid[hy][hx] = '@'
  grid[hy][hx + 1] = ')'
  return grid.map((row) => row.join('')).join('\n')
}

/** Format MW for display: 2047.3 -> "2,047". */
export const fmtMw = (value) => Math.round(value).toLocaleString('en-GB')

/** Round to the nearest 50 for reading aloud: 5096 -> "5,100". */
export const fmtAbout = (value) => fmtMw(Math.round(value / 50) * 50)

/** A filled bar of `width` characters, e.g. "████▌·····". Used by the ASCII charts. */
export function asciiBar(value, max, width) {
  const eighths = ['', '▏', '▎', '▍', '▌', '▋', '▊', '▉']
  const units = max > 0 ? (Math.max(0, value) / max) * width : 0
  const full = Math.floor(units)
  const rest = Math.floor((units - full) * 8)
  return '█'.repeat(full) + (eighths[rest] || '') + '·'.repeat(Math.max(0, width - full - (rest ? 1 : 0)))
}
