import { useEffect, useRef, useState } from 'react';
import { prefersReducedMotion } from '../hooks/useReducedMotion.js';

// Hosts the fixed full-viewport canvas. Three.js is imported lazily so the
// hero copy renders before the 3D bundle has even been fetched.
export default function AgriculturalScene() {
  const canvasRef = useRef(null);
  const [status, setStatus] = useState('loading'); // loading | ready | fallback

  useEffect(() => {
    let disposed = false;
    let handle = null;
    const canvas = canvasRef.current;

    const hasWebGL = () => {
      try {
        const c = document.createElement('canvas');
        return !!(window.WebGLRenderingContext && (c.getContext('webgl2') || c.getContext('webgl')));
      } catch {
        return false;
      }
    };

    if (!hasWebGL()) {
      setStatus('fallback');
      return undefined;
    }

    import('../scene/createAgriculturalScene.js')
      .then(({ createAgriculturalScene }) => {
        if (disposed) return;
        const mobile = window.matchMedia('(max-width: 959px), (pointer: coarse)').matches;
        handle = createAgriculturalScene(canvas, {
          mobile,
          reducedMotion: prefersReducedMotion(),
          onReady: () => !disposed && setStatus('ready'),
          onContextLost: () => !disposed && setStatus('fallback'),
        });
      })
      .catch(() => !disposed && setStatus('fallback'));

    return () => {
      disposed = true;
      handle?.dispose();
    };
  }, []);

  return (
    <div className={`scene scene--${status}`} aria-hidden="true">
      <canvas ref={canvasRef} className="scene__canvas" />
      {status === 'fallback' && (
        <div className="scene__fallback">
          <span className="scene__fb-layer scene__fb-layer--a" />
          <span className="scene__fb-layer scene__fb-layer--b" />
          <span className="scene__fb-layer scene__fb-layer--c" />
        </div>
      )}
      <div className="scene__loader">
        <span className="scene__loader-line" />
        <span>Growing the landscape</span>
      </div>
    </div>
  );
}
