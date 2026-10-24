import * as THREE from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { bridge } from './bridge.js';
import {
  ISLAND_RADIUS,
  buildTopGeometry,
  buildUndersideGeometry,
  findBarnSpot,
  mulberry32,
  scatterPlants,
} from './terrain.js';

const LIME = '#C8F169';
const BG = '#07150F';
const FOV = 32;
const TAN = Math.tan(THREE.MathUtils.degToRad(FOV / 2));

const ease = (t) => t * t * (3 - 2 * t);
const mix = (a, b, t) => a.map((v, i) => v + (b[i] - v) * t);

// Flat state layout: cam(3) look(3) pos(3) rot scale sun
function keyframes(layout, z, visW, visH) {
  const stacked = layout === 'stacked';
  const ix = stacked ? 0 : visW * 0.2;
  const iy = stacked ? -visH * 0.2 : -0.1;
  return {
    hero: [0, z * 0.3, z, 0, 0, 0, ix, iy, 0, 0.5, 1, 0],
    exit: [0.4, z * 0.4, z * 0.88, 0, 0.5, 0, stacked ? 0 : ix * 0.35, stacked ? iy + visH * 0.25 : 0.9, -1, 1.3, stacked ? 0.8 : 0.78, 0],
    vision: [0, z * 0.13, z * 0.92, 0, 0.3, 0, 0, stacked ? visH * 0.02 : -0.1, 0, 2.6, stacked ? 0.95 : 1.12, 1],
  };
}

function radialTexture(inner, outer) {
  const c = document.createElement('canvas');
  c.width = 128;
  c.height = 128;
  const g = c.getContext('2d');
  const grad = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  grad.addColorStop(0, inner);
  grad.addColorStop(1, outer);
  g.fillStyle = grad;
  g.fillRect(0, 0, 128, 128);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

function buildPlantGeometry() {
  const leaves = [];
  for (let k = 0; k < 3; k += 1) {
    const cone = new THREE.ConeGeometry(0.03, 0.22, 4, 1, true);
    cone.translate(0, 0.11, 0);
    const m = new THREE.Matrix4().makeRotationY(k * 2.09).multiply(new THREE.Matrix4().makeRotationZ(0.3));
    cone.applyMatrix4(m);
    leaves.push(cone);
  }
  return mergeGeometries(leaves);
}

export function createAgriculturalScene(canvas, { mobile, reducedMotion, onReady, onContextLost }) {
  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: !mobile,
    alpha: true,
    powerPreference: 'high-performance',
  });
  renderer.setClearColor(0x000000, 0);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, mobile ? 1.5 : 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = mobile ? THREE.PCFShadowMap : THREE.PCFSoftShadowMap;

  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(BG, 20, 40);
  const camera = new THREE.PerspectiveCamera(FOV, 1, 0.1, 120);

  // Environment lighting (procedural – no external asset).
  const pmrem = new THREE.PMREMGenerator(renderer);
  const envTex = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environment = envTex;
  scene.environmentIntensity = 0.3;
  pmrem.dispose();

  // Lights
  const hemi = new THREE.HemisphereLight('#f4f1e8', '#1d4a33', 0.7);
  scene.add(hemi);
  const sun = new THREE.DirectionalLight('#ffeccb', 2.4);
  sun.castShadow = true;
  sun.shadow.mapSize.set(mobile ? 512 : 2048, mobile ? 512 : 2048);
  sun.shadow.camera.left = -4.5;
  sun.shadow.camera.right = 4.5;
  sun.shadow.camera.top = 4.5;
  sun.shadow.camera.bottom = -4.5;
  sun.shadow.camera.near = 1;
  sun.shadow.camera.far = 24;
  sun.shadow.bias = -0.0006;
  sun.shadow.normalBias = 0.02;
  scene.add(sun, sun.target);
  const rim = new THREE.DirectionalLight('#9bd96a', 1.1);
  rim.position.set(-6, 3, -7);
  scene.add(rim);

  const resources = [];
  const track = (r) => {
    resources.push(r);
    return r;
  };

  // ---------- the island ----------
  const island = new THREE.Group();
  scene.add(island);

  const topGeo = track(buildTopGeometry(mobile ? 36 : 60, mobile ? 96 : 168));
  const topMat = track(new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.92, metalness: 0 }));
  const top = new THREE.Mesh(topGeo, topMat);
  top.receiveShadow = true;
  top.castShadow = true;
  island.add(top);

  const underGeo = track(buildUndersideGeometry(mobile ? 40 : 72));
  const underMat = track(new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1, flatShading: true, side: THREE.DoubleSide }));
  const under = new THREE.Mesh(underGeo, underMat);
  under.castShadow = true;
  island.add(under);

  // Barn
  const barnSpot = findBarnSpot();
  const barn = new THREE.Group();
  const wallMat = track(new THREE.MeshStandardMaterial({ color: '#f4f1e8', roughness: 0.8 }));
  const roofMat = track(new THREE.MeshStandardMaterial({ color: '#1c3a2b', roughness: 0.7 }));
  const wallGeo = track(new THREE.BoxGeometry(0.34, 0.2, 0.26));
  const roofGeo = track(new THREE.CylinderGeometry(0.17, 0.17, 0.38, 3));
  roofGeo.rotateX(-Math.PI / 2); // apex up
  roofGeo.rotateY(Math.PI / 2); // ridge along X
  const walls = new THREE.Mesh(wallGeo, wallMat);
  walls.position.y = 0.1;
  const roof = new THREE.Mesh(roofGeo, roofMat);
  roof.position.y = 0.285;
  walls.castShadow = true;
  roof.castShadow = true;
  barn.add(walls, roof);
  barn.position.set(barnSpot.x, barnSpot.y - 0.01, barnSpot.z);
  barn.rotation.y = 0.5;
  island.add(barn);

  // Crops – one InstancedMesh, wind sway in the vertex shader.
  const plantSpots = mobile ? scatterPlants(0.15, 0.19, barnSpot) : scatterPlants(0.08, 0.1, barnSpot);
  const plantGeo = track(buildPlantGeometry());
  const plantMat = track(new THREE.MeshStandardMaterial({ color: '#ffffff', roughness: 0.7, side: THREE.DoubleSide }));
  const plantUniforms = { uTime: { value: 0 } };
  plantMat.onBeforeCompile = (shader) => {
    shader.uniforms.uTime = plantUniforms.uTime;
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nuniform float uTime;')
      .replace(
        '#include <begin_vertex>',
        `vec3 transformed = vec3(position);
#ifdef USE_INSTANCING
float ph = instanceMatrix[3].x * 2.7 + instanceMatrix[3].z * 1.9;
float sw = sin(uTime * 1.6 + ph) * 0.25 * position.y;
transformed.x += sw;
transformed.z += sw * 0.6;
#endif`,
      );
  };
  const plants = new THREE.InstancedMesh(plantGeo, plantMat, plantSpots.length);
  const dummy = new THREE.Object3D();
  const cA = new THREE.Color('#3f8f3a');
  const cB = new THREE.Color('#b9de5c');
  const tmp = new THREE.Color();
  plantSpots.forEach((p, i) => {
    dummy.position.set(p.x, p.y, p.z);
    dummy.rotation.set(0, p.rot, 0);
    dummy.scale.set(p.s, p.s * (0.9 + p.t * 0.5), p.s);
    dummy.updateMatrix();
    plants.setMatrixAt(i, dummy.matrix);
    plants.setColorAt(i, tmp.copy(cA).lerp(cB, p.t));
  });
  plants.instanceMatrix.needsUpdate = true;
  if (plants.instanceColor) plants.instanceColor.needsUpdate = true;
  plants.frustumCulled = false;
  island.add(plants);

  // ---------- atmosphere & data elements (not rotating with the island) ----------
  const floaters = new THREE.Group();
  scene.add(floaters);

  const glowTex = track(radialTexture('rgba(200,241,105,0.55)', 'rgba(200,241,105,0)'));
  const glow = new THREE.Sprite(
    track(new THREE.SpriteMaterial({ map: glowTex, transparent: true, opacity: 0.35, depthWrite: false, fog: false })),
  );
  glow.scale.set(11, 11, 1);
  glow.position.set(0, -0.6, -3.2);
  floaters.add(glow);

  const ringGeo = track(new THREE.TorusGeometry(4.1, 0.006, 6, 200));
  const ringMat = track(new THREE.MeshBasicMaterial({ color: LIME, transparent: true, opacity: 0.35 }));
  const ring = new THREE.Mesh(ringGeo, ringMat);
  ring.rotation.x = Math.PI / 2 + 0.3;
  ring.position.y = 0.2;
  floaters.add(ring);

  const nodeGeo = track(new THREE.SphereGeometry(0.05, 10, 10));
  const nodeMat = track(new THREE.MeshBasicMaterial({ color: LIME }));
  const nodes = [];
  const nodeCount = mobile ? 8 : 14;
  for (let i = 0; i < nodeCount; i += 1) {
    const m = new THREE.Mesh(nodeGeo, nodeMat);
    m.userData.a = (i / nodeCount) * Math.PI * 2;
    m.userData.s = 0.6 + (i % 4) * 0.3;
    nodes.push(m);
    ring.add(m);
  }

  // Holographic data panels
  const panelFrameMat = track(new THREE.LineBasicMaterial({ color: LIME, transparent: true, opacity: 0.7 }));
  const panelFillMat = track(new THREE.MeshBasicMaterial({ color: '#285C3C', transparent: true, opacity: 0.28, side: THREE.DoubleSide }));
  const barMat = track(new THREE.MeshBasicMaterial({ color: LIME, transparent: true, opacity: 0.85 }));
  const planeGeo = track(new THREE.PlaneGeometry(0.95, 0.6));
  const edgeGeo = track(new THREE.EdgesGeometry(planeGeo));
  const barGeo = track(new THREE.PlaneGeometry(0.07, 1));
  const panelDefs = [
    { x: -2.7, y: 2.2, z: 1.2, depth: 1.2, side: -1 },
    { x: 2.9, y: 1.9, z: 0.6, depth: 0.8, side: 1 },
    { x: 0.4, y: 3.0, z: -0.8, depth: 1.6, side: 1 },
  ].slice(0, mobile ? 2 : 3);
  const panels = panelDefs.map((d, n) => {
    const g = new THREE.Group();
    g.add(new THREE.Mesh(planeGeo, panelFillMat), new THREE.LineSegments(edgeGeo, panelFrameMat));
    for (let b = 0; b < 5; b += 1) {
      const h = 0.12 + ((b * 37 + n * 13) % 10) * 0.035;
      const bar = new THREE.Mesh(barGeo, barMat);
      bar.scale.y = h;
      bar.position.set(-0.3 + b * 0.15, -0.22 + h / 2, 0.005);
      g.add(bar);
    }
    g.userData = d;
    floaters.add(g);
    return g;
  });

  // Clouds
  const cloudGeo = track(new THREE.IcosahedronGeometry(1, 1));
  const cloudMat = track(
    new THREE.MeshStandardMaterial({ color: '#f4f1e8', roughness: 1, flatShading: true, transparent: true, opacity: 0.55 }),
  );
  const clouds = [];
  const rand = mulberry32(21);
  const cloudCount = mobile ? 3 : 6;
  for (let i = 0; i < cloudCount; i += 1) {
    const g = new THREE.Group();
    const parts = 3 + Math.floor(rand() * 2);
    for (let k = 0; k < parts; k += 1) {
      const m = new THREE.Mesh(cloudGeo, cloudMat);
      m.position.set((k - parts / 2) * 0.7, rand() * 0.2, rand() * 0.3);
      m.scale.set(0.6 + rand() * 0.4, 0.3 + rand() * 0.15, 0.4);
      g.add(m);
    }
    g.position.set((rand() - 0.5) * 18, -1 + rand() * 4.5, -3 - rand() * 5);
    g.userData.speed = 0.08 + rand() * 0.12;
    g.scale.setScalar(1 + rand());
    scene.add(g);
    clouds.push(g);
  }

  // Pollen / dust particles
  const dustCount = mobile ? 50 : 160;
  const dustPos = new Float32Array(dustCount * 3);
  for (let i = 0; i < dustCount; i += 1) {
    dustPos[i * 3] = (rand() - 0.5) * 12;
    dustPos[i * 3 + 1] = (rand() - 0.5) * 7;
    dustPos[i * 3 + 2] = (rand() - 0.5) * 8;
  }
  const dustGeo = track(new THREE.BufferGeometry());
  dustGeo.setAttribute('position', new THREE.BufferAttribute(dustPos, 3));
  const dustMat = track(
    new THREE.PointsMaterial({
      map: track(radialTexture('rgba(255,255,255,1)', 'rgba(255,255,255,0)')),
      color: LIME,
      size: 0.09,
      transparent: true,
      opacity: 0.6,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    }),
  );
  const dust = new THREE.Points(dustGeo, dustMat);
  floaters.add(dust);

  // ---------- state / layout ----------
  let layout = window.innerWidth < 960 ? 'stacked' : 'desktop';
  let K = null;
  let visW = 12;
  let visH = 7;
  let cur = null;
  const ptr = { x: 0, y: 0 };

  function targetState() {
    const a = ease(bridge.p1);
    const b = ease(bridge.p2);
    return mix(mix(K.hero, K.exit, a), K.vision, b);
  }

  function resize() {
    const w = canvas.clientWidth || window.innerWidth;
    const h = canvas.clientHeight || window.innerHeight;
    layout = window.innerWidth < 960 ? 'stacked' : 'desktop';
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    const aspect = w / h;
    const z =
      layout === 'stacked'
        ? Math.min(Math.max(7.8 / (2 * TAN * aspect), 13), 36)
        : Math.max(13, 10.9 / (2 * TAN * aspect));
    visH = 2 * z * TAN;
    visW = visH * aspect;
    K = keyframes(layout, z, visW, visH);
    scene.fog.near = z * 1.1;
    scene.fog.far = z * 2.6;
    if (!cur) cur = targetState();
  }
  resize();

  // ---------- loop ----------
  const clock = new THREE.Clock();
  let t = 0;
  let ready = false;
  const sunCool = new THREE.Color('#ffeccb');
  const sunWarm = new THREE.Color('#ffc07a');

  function frame() {
    const dt = Math.min(clock.getDelta(), 0.05);
    if (!bridge.visible) return;
    if (!reducedMotion) t += dt;

    const tgt = targetState();
    const k = 1 - Math.exp(-dt * (reducedMotion ? 60 : 3.5));
    for (let i = 0; i < cur.length; i += 1) cur[i] += (tgt[i] - cur[i]) * k;

    const pk = reducedMotion ? 0 : 1 - Math.exp(-dt * 3);
    const pf = layout === 'stacked' ? 0.5 : 1;
    ptr.x += (bridge.pointer.x * pf - ptr.x) * pk;
    ptr.y += (bridge.pointer.y * pf - ptr.y) * pk;

    camera.position.set(cur[0] + ptr.x * 0.8, cur[1] - ptr.y * 0.4, cur[2]);
    camera.lookAt(cur[3], cur[4], cur[5]);

    const bob = Math.sin(t * 0.8) * 0.12;
    island.position.set(cur[6], cur[7] + bob, cur[8]);
    island.rotation.set(ptr.y * 0.05, cur[9] + Math.sin(t * 0.25) * 0.08 + ptr.x * 0.18, 0);
    island.scale.setScalar(cur[10]);

    floaters.position.set(cur[6], cur[7], 0);
    floaters.scale.setScalar(cur[10]);
    ring.rotation.z = t * 0.05;
    nodes.forEach((n) => {
      const a = n.userData.a + t * 0.12 * n.userData.s;
      n.position.set(Math.cos(a) * 4.1, Math.sin(a) * 4.1, 0);
    });
    panels.forEach((p, i) => {
      const d = p.userData;
      p.position.set(
        d.x + ptr.x * 0.35 * d.depth,
        d.y + Math.sin(t * 0.9 + i * 1.7) * 0.1 - ptr.y * 0.2 * d.depth,
        d.z,
      );
      p.lookAt(camera.position);
      p.rotateY(0.25 * d.side);
    });
    clouds.forEach((c) => {
      c.position.x += c.userData.speed * dt;
      const lim = visW * 0.7 + 4;
      if (c.position.x > lim) c.position.x = -lim;
    });
    const dp = dustGeo.attributes.position;
    if (!reducedMotion) {
      for (let i = 0; i < dustCount; i += 1) {
        let y = dp.getY(i) + dt * (0.08 + (i % 5) * 0.015);
        if (y > 3.5) y = -3.5;
        dp.setY(i, y);
        dp.setX(i, dp.getX(i) + Math.sin(t * 0.4 + i) * 0.0008);
      }
      dp.needsUpdate = true;
    }

    // Sun: warmer & lower for the vision composition; shadows follow the island.
    const w = cur[11];
    sun.color.copy(sunCool).lerp(sunWarm, w);
    sun.intensity = 2.4 - w * 0.3;
    const sx = 5 - w * 9;
    const sy = 6 - w * 2.5;
    const sz = 4 + w * 1;
    sun.position.set(cur[6] + sx, cur[7] + sy, sz);
    sun.target.position.set(cur[6], cur[7], 0);

    plantUniforms.uTime.value = t;
    renderer.render(scene, camera);
    if (!ready) {
      ready = true;
      onReady?.();
    }
  }
  renderer.setAnimationLoop(frame);

  const onLost = (e) => {
    e.preventDefault();
    onContextLost?.();
  };
  canvas.addEventListener('webglcontextlost', onLost);
  window.addEventListener('resize', resize);

  return {
    dispose() {
      renderer.setAnimationLoop(null);
      window.removeEventListener('resize', resize);
      canvas.removeEventListener('webglcontextlost', onLost);
      resources.forEach((r) => {
        if (r.map) r.map.dispose();
        r.dispose?.();
      });
      plants.dispose();
      envTex.dispose();
      renderer.dispose();
    },
  };
}

export { ISLAND_RADIUS };
