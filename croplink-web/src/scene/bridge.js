// Shared, framework-agnostic state between the DOM (scroll / pointer) and the 3D scene.
// p1: hero → exit progress (0..1)   p2: arrival into the vision composition (0..1)
export const bridge = {
  p1: 0,
  p2: 0,
  visible: true,
  pointer: { x: 0, y: 0 },
};
