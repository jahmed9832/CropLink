import { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { prefersReducedMotion } from '../hooks/useReducedMotion.js';

const STEPS = [
  { n: '01', title: 'Know Your Harvest', text: 'Farmers provide their crop information.' },
  { n: '02', title: 'Understand Your Market', text: 'CropLink presents available market insights and supported AI features.' },
  { n: '03', title: 'Find Your Opportunity', text: 'Farmers explore market connections and selling opportunities.' },
];

export default function HowItWorks() {
  const root = useRef(null);

  useEffect(() => {
    const el = root.current;
    const items = el.querySelectorAll('.step');
    const apply = (p) => {
      el.style.setProperty('--p', p.toFixed(3));
      items.forEach((it, i) => it.classList.toggle('is-on', p >= i * 0.42 - 0.02));
    };
    if (prefersReducedMotion()) {
      apply(1);
      return undefined;
    }
    gsap.registerPlugin(ScrollTrigger);
    const st = ScrollTrigger.create({
      trigger: el.querySelector('.steps'),
      start: 'top 75%',
      end: 'bottom 55%',
      scrub: 0.4,
      onUpdate: (s) => apply(s.progress),
      onRefresh: (s) => apply(s.progress),
    });
    apply(st.progress);
    return () => st.kill();
  }, []);

  return (
    <section className="how" ref={root}>
      <div className="wrap">
        <p className="eyebrow eyebrow--dark" data-rise>
          How it works
        </p>
        <h2 className="how__title" data-rise>
          From harvest to opportunity, in three steps.
        </h2>
        <ol className="steps">
          <li className="steps__track" aria-hidden="true">
            <span className="steps__fill" />
          </li>
          {STEPS.map((s) => (
            <li className="step" key={s.n}>
              <span className="step__marker">{s.n}</span>
              <h3>
                <span className="step__kicker">Step {s.n}</span>
                {s.title}
              </h3>
              <p>{s.text}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
