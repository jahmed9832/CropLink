import { useEffect } from 'react';
import { bridge } from '../scene/bridge.js';
import { prefersReducedMotion } from './useReducedMotion.js';

// Tracks the cursor once, publishes it to the 3D scene (bridge.pointer) and to
// CSS custom properties (--mx / --my, damped) on the given element for DOM parallax.
export function usePointerVars(ref) {
  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const reduced = prefersReducedMotion();
    let tx = 0;
    let ty = 0;
    let cx = 0;
    let cy = 0;
    let raf = 0;

    const onMove = (e) => {
      tx = (e.clientX / window.innerWidth) * 2 - 1;
      ty = (e.clientY / window.innerHeight) * 2 - 1;
      if (!reduced) {
        bridge.pointer.x = tx;
        bridge.pointer.y = ty;
      }
    };
    const loop = () => {
      cx += (tx - cx) * 0.07;
      cy += (ty - cy) * 0.07;
      el.style.setProperty('--mx', cx.toFixed(4));
      el.style.setProperty('--my', cy.toFixed(4));
      raf = requestAnimationFrame(loop);
    };
    window.addEventListener('pointermove', onMove, { passive: true });
    if (!reduced) raf = requestAnimationFrame(loop);
    return () => {
      window.removeEventListener('pointermove', onMove);
      cancelAnimationFrame(raf);
    };
  }, [ref]);
}
