import { lazy, Suspense, useEffect, useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import Navbar from '../components/Navbar.jsx';
import HeroSection from '../components/HeroSection.jsx';
import ProblemSection from '../components/ProblemSection.jsx';
import ProductShowcase from '../components/ProductShowcase.jsx';
import MarketIntelligence from '../components/MarketIntelligence.jsx';
import HowItWorks from '../components/HowItWorks.jsx';
import VisionSection from '../components/VisionSection.jsx';
import FinalCTA from '../components/FinalCTA.jsx';
import Footer from '../components/Footer.jsx';
import { bridge } from '../scene/bridge.js';
import { prefersReducedMotion } from '../hooks/useReducedMotion.js';

const AgriculturalScene = lazy(() => import('../components/AgriculturalScene.jsx'));

export default function LandingPage() {
  const heroRef = useRef(null);
  const problemRef = useRef(null);
  const visionRef = useRef(null);
  const rootRef = useRef(null);

  useEffect(() => {
    gsap.registerPlugin(ScrollTrigger);
    const reduced = prefersReducedMotion();
    let heroActive = true;
    let visionActive = false;
    const syncVisible = () => {
      bridge.visible = heroActive || visionActive;
    };

    const ctx = gsap.context(() => {
      // 3D scene progress: hero → exit composition.
      const heroST = ScrollTrigger.create({
        trigger: heroRef.current,
        start: 'top top',
        end: 'bottom top',
        scrub: true,
        onUpdate: (s) => {
          bridge.p1 = s.progress;
        },
        onRefresh: (s) => {
          bridge.p1 = s.progress;
          heroActive = s.isActive;
          syncVisible();
        },
        onToggle: (s) => {
          heroActive = s.isActive;
          syncVisible();
        },
      });

      // Arrival into the vision composition.
      ScrollTrigger.create({
        trigger: visionRef.current,
        start: 'top bottom',
        end: 'top 15%',
        scrub: true,
        onUpdate: (s) => {
          bridge.p2 = s.progress;
        },
        onRefresh: (s) => {
          bridge.p2 = s.progress;
        },
      });
      // Canvas is only rendered while hero or vision are on screen.
      ScrollTrigger.create({
        trigger: visionRef.current,
        start: 'top bottom',
        end: 'bottom top',
        onToggle: (s) => {
          visionActive = s.isActive;
          syncVisible();
        },
        onRefresh: (s) => {
          visionActive = s.isActive;
          syncVisible();
        },
      });
      bridge.p1 = heroST.progress;

      if (reduced) return;

      // Hero copy leaves, the cream section opens up like an aperture.
      gsap.to('.hero__content', {
        opacity: 0,
        y: -90,
        ease: 'none',
        scrollTrigger: { trigger: heroRef.current, start: 'top top', end: '55% top', scrub: true },
      });
      gsap.to('.fcards', {
        opacity: 0,
        ease: 'none',
        scrollTrigger: { trigger: heroRef.current, start: '10% top', end: '60% top', scrub: true },
      });
      gsap.fromTo(
        problemRef.current,
        { clipPath: 'inset(9% 5% 0% 5% round 44px)' },
        {
          clipPath: 'inset(0% 0% 0% 0% round 0px)',
          ease: 'none',
          scrollTrigger: { trigger: problemRef.current, start: 'top bottom', end: 'top 20%', scrub: true },
        },
      );

      // Editorial reveal for everything tagged data-rise (except inside the hero).
      gsap.set('[data-rise]', { opacity: 0, y: 36 });
      ScrollTrigger.batch('[data-rise]', {
        start: 'top 88%',
        once: true,
        onEnter: (batch) => gsap.to(batch, { opacity: 1, y: 0, duration: 1, ease: 'power3.out', stagger: 0.12, overwrite: true }),
      });
    }, rootRef);

    const refresh = () => ScrollTrigger.refresh();
    if (document.fonts?.ready) document.fonts.ready.then(refresh);
    window.addEventListener('load', refresh);

    return () => {
      window.removeEventListener('load', refresh);
      ctx.revert();
    };
  }, []);

  return (
    <div className="landing" ref={rootRef}>
      <Suspense fallback={null}>
        <AgriculturalScene />
      </Suspense>
      <Navbar />
      <main className="landing__main">
        <HeroSection ref={heroRef} />
        <ProblemSection ref={problemRef} />
        <ProductShowcase />
        <MarketIntelligence />
        <HowItWorks />
        <VisionSection ref={visionRef} />
        <FinalCTA />
      </main>
      <Footer />
    </div>
  );
}
