import * as THREE from 'three';

export const ISLAND_RADIUS = 3.2;
const R = ISLAND_RADIUS;
const STEPS = 5;
const SCALE = 1.25;

// ---------- deterministic noise ----------
function hash(x, z) {
  const s = Math.sin(x * 127.1 + z * 311.7) * 43758.5453;
  return s - Math.floor(s);
}
function vnoise(x, z) {
  const xi = Math.floor(x);
  const zi = Math.floor(z);
  const xf = x - xi;
  const zf = z - zi;
  const u = xf * xf * (3 - 2 * xf);
  const v = zf * zf * (3 - 2 * zf);
  const a = hash(xi, zi);
  const b = hash(xi + 1, zi);
  const c = hash(xi, zi + 1);
  const d = hash(xi + 1, zi + 1);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}
export function fbm(x, z, oct = 3) {
  let amp = 0.5;
  let f = 1;
  let sum = 0;
  let norm = 0;
  for (let i = 0; i < oct; i += 1) {
    sum += vnoise(x * f, z * f) * amp;
    norm += amp;
    amp *= 0.5;
    f *= 2;
  }
  return sum / norm;
}
function smooth(a, b, t) {
  const k = Math.min(1, Math.max(0, (t - a) / (b - a)));
  return k * k * (3 - 2 * k);
}
export function mulberry32(seed) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ---------- height field ----------
function rawHeight(x, z) {
  const r = Math.hypot(x, z) / R;
  const n = fbm(x * 0.7 + 5, z * 0.7 - 3, 3);
  const dome = 1 - Math.pow(Math.min(r, 1.1), 1.7);
  const hill = Math.exp(-((x + 0.6) ** 2 + (z + 0.9) ** 2) / 2.2) * 0.35;
  return Math.max(0, dome * 0.75 + hill + (n - 0.45) * 0.18);
}

// Terraced: flat plateaus joined by short risers.
export function islandHeight(x, z) {
  const h = rawHeight(x, z) * STEPS;
  const f = Math.floor(h);
  const t = h - f;
  return ((f + smooth(0.62, 0.95, t)) / STEPS) * SCALE;
}

export function pathX(z) {
  return Math.sin(z * 1.1 + 0.5) * 0.55 + 0.12 * Math.sin(z * 3.1);
}

function slopeAt(x, z) {
  const e = 0.04;
  const dx = Math.abs(islandHeight(x + e, z) - islandHeight(x - e, z));
  const dz = Math.abs(islandHeight(x, z + e) - islandHeight(x, z - e));
  return (dx + dz) / (2 * e);
}

// ---------- geometry ----------
const PALETTE = ['#2c6a3a', '#38803f', '#4c9a45', '#69b04b', '#88c155', '#a9d363'].map((c) => new THREE.Color(c));
const SOIL = new THREE.Color('#6a4a2e');
const PATH = new THREE.Color('#c2a272');

export function buildTopGeometry(rings, seg) {
  const pos = [];
  const idx = [];
  for (let i = 0; i <= rings; i += 1) {
    const r = (i / rings) * R;
    for (let j = 0; j <= seg; j += 1) {
      const th = (j / seg) * Math.PI * 2;
      const x = r * Math.cos(th);
      const z = r * Math.sin(th);
      pos.push(x, islandHeight(x, z), z);
    }
  }
  for (let i = 0; i < rings; i += 1) {
    for (let j = 0; j < seg; j += 1) {
      const a = i * (seg + 1) + j;
      const b = a + 1;
      const c = a + (seg + 1);
      const d = c + 1;
      idx.push(a, b, c, b, d, c); // counter-clockwise seen from +Y
    }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geo.setIndex(idx);
  geo.computeVertexNormals();

  const count = pos.length / 3;
  const nrm = geo.attributes.normal;
  const col = new Float32Array(count * 3);
  const c = new THREE.Color();
  for (let k = 0; k < count; k += 1) {
    const x = pos[k * 3];
    const z = pos[k * 3 + 2];
    const level = Math.min(Math.floor(rawHeight(x, z) * STEPS), PALETTE.length - 1);
    const r = Math.hypot(x, z) / R;
    c.copy(PALETTE[level]);
    c.offsetHSL(0, 0, Math.sin((x * 0.8 + z * 0.6) * 10 + level * 1.7) * 0.022);
    const slope = 1 - nrm.getY(k);
    c.lerp(SOIL, smooth(0.05, 0.26, slope));
    if (r < 0.93) c.lerp(PATH, 1 - smooth(0.06, 0.13, Math.abs(x - pathX(z))));
    c.lerp(SOIL, smooth(0.9, 0.99, r));
    col[k * 3] = c.r;
    col[k * 3 + 1] = c.g;
    col[k * 3 + 2] = c.b;
  }
  geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
  return geo;
}

const STRATA = [
  { y: -0.35, c: new THREE.Color('#4a3220') },
  { y: -1.0, c: new THREE.Color('#6b4a30') },
  { y: -1.8, c: new THREE.Color('#8a6a47') },
  { y: -2.6, c: new THREE.Color('#5d5b55') },
  { y: -9, c: new THREE.Color('#3b3f3d') },
];

export function buildUndersideGeometry(segments) {
  const pts = [];
  const N = 18;
  for (let i = 0; i <= N; i += 1) {
    const t = i / N;
    const radius = Math.max(0.03, R * (1 - Math.pow(t, 1.15)) * (1 + 0.05 * Math.sin(t * 9)));
    pts.push(new THREE.Vector2(radius, -3.5 * t - 0.02));
  }
  pts.reverse(); // tip -> rim, the order LatheGeometry expects for outward faces
  const geo = new THREE.LatheGeometry(pts, segments);
  const p = geo.attributes.position;
  const col = new Float32Array(p.count * 3);
  const c = new THREE.Color();
  for (let k = 0; k < p.count; k += 1) {
    const x = p.getX(k);
    let y = p.getY(k);
    const z = p.getZ(k);
    const depth = Math.min(1, Math.max(0, -y / 3.5));
    const bump = (fbm(x * 1.3 + y, z * 1.3 - y, 3) - 0.5) * 0.45 * (1 - depth * 0.6);
    const len = Math.hypot(x, z) || 1;
    p.setX(k, x + (x / len) * bump);
    p.setZ(k, z + (z / len) * bump);
    y += (fbm(x * 2, z * 2, 2) - 0.5) * 0.18;
    p.setY(k, y);

    const yy = y + (fbm(x * 1.5, z * 1.5, 2) - 0.5) * 0.3;
    let i = 0;
    while (i < STRATA.length - 1 && yy < STRATA[i].y) i += 1;
    c.copy(STRATA[i].c);
    col[k * 3] = c.r;
    col[k * 3 + 1] = c.g;
    col[k * 3 + 2] = c.b;
  }
  geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
  return geo;
}

// ---------- props ----------
export function findBarnSpot() {
  let best = null;
  for (let x = -1.8; x <= 1.8; x += 0.1) {
    for (let z = -1.8; z <= 1.8; z += 0.1) {
      const r = Math.hypot(x, z);
      if (r > R * 0.6 || r < 0.5) continue;
      if (Math.abs(x - pathX(z)) < 0.4) continue;
      const y = islandHeight(x, z);
      const flat =
        slopeAt(x, z) < 0.02 &&
        Math.abs(islandHeight(x + 0.28, z) - y) < 0.01 &&
        Math.abs(islandHeight(x - 0.28, z) - y) < 0.01 &&
        Math.abs(islandHeight(x, z + 0.24) - y) < 0.01 &&
        Math.abs(islandHeight(x, z - 0.24) - y) < 0.01;
      if (flat && (!best || y > best.y)) best = { x, y, z };
    }
  }
  return best || { x: -0.9, y: islandHeight(-0.9, 0.4), z: 0.4 };
}

export function scatterPlants(spacingX, spacingZ, barn) {
  const rand = mulberry32(7);
  const out = [];
  for (let x = -R; x <= R; x += spacingX) {
    for (let z = -R; z <= R; z += spacingZ) {
      const px = x + (rand() - 0.5) * spacingX * 0.45;
      const pz = z + (rand() - 0.5) * spacingZ * 0.35;
      const r = Math.hypot(px, pz);
      if (r > R * 0.9) continue;
      if (Math.abs(px - pathX(pz)) < 0.17) continue;
      if (barn && Math.hypot(px - barn.x, pz - barn.z) < 0.5) continue;
      if (slopeAt(px, pz) > 0.3) continue;
      out.push({ x: px, y: islandHeight(px, pz), z: pz, rot: rand() * Math.PI * 2, s: 0.75 + rand() * 0.75, t: rand() });
    }
  }
  return out;
}
