import { forwardRef, useEffect, useRef } from 'react';
import gsap from 'gsap';
import { ArrowDownRight } from 'lucide-react';
import FloatingMarketCards from './FloatingMarketCards.jsx';
import { usePointerVars } from '../hooks/usePointerVars.js';
import { prefersReducedMotion } from '../hooks/useReducedMotion.js';

const HeroSection = forwardRef(function HeroSection(_, ref) {
  const local = useRef(null);
  usePointerVars(local);

  useEffect(() => {
    if (prefersReducedMotion()) return undefined;
    const ctx = gsap.context(() => {
      gsap.from('[data-intro]', { y: 44, opacity: 0, duration: 1.1, ease: 'power3.out', stagger: 0.12, delay: 0.15 });
      gsap.from('.fcard__in', { scale: 0.92, opacity: 0, duration: 1.2, ease: 'power3.out', stagger: 0.15, delay: 0.9 });
    }, local);
    return () => ctx.revert();
  }, []);

  return (
    <section
      id="top"
      className="hero"
      ref={(node) => {
        local.current = node;
        if (typeof ref === 'function') ref(node);
        else if (ref) ref.current = node;
      }}
    >
      <div className="hero__content">
        <p className="eyebrow" data-intro>
          The next era of agriculture
        </p>
        <h1 className="hero__title" data-intro>
          <span>Grow Smarter.</span>
          <span className="hero__title-accent">Sell Fairer.</span>
        </h1>
        <p className="hero__lead" data-intro>
          CropLink connects farmers to smarter market decisions, AI-powered agricultural intelligence, and opportunities for a fairer harvest.
        </p>
        <div className="hero__ctas" data-intro>
          <a href="#story" className="btn btn--lime">
            Discover CropLink
          </a>
          <a href="#platform" className="btn btn--ghost">
            Explore the Platform
          </a>
        </div>
        <p className="hero__trust" data-intro>
          Built for farmers. Powered by intelligence.
        </p>
      </div>
      <FloatingMarketCards />
      <a href="#story" className="hero__scroll" aria-label="Scroll to next section">
        <span>Scroll</span>
        <ArrowDownRight size={16} />
      </a>
    </section>
  );
});

export default HeroSection;
