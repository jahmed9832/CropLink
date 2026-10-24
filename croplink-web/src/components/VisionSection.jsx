import { forwardRef } from 'react';

const PRINCIPLES = [
  { k: 'Fairness', t: 'Helping farmers understand their market opportunities.' },
  { k: 'Connection', t: 'Bringing farmers and buyers closer together.' },
  { k: 'Intelligence', t: 'Making agricultural market information more accessible.' },
];

// Intentionally transparent: the fixed 3D island shows through in its "vision" composition.
const VisionSection = forwardRef(function VisionSection(_, ref) {
  return (
    <section id="vision" className="vision" ref={ref}>
      <div className="wrap vision__top">
        <p className="eyebrow" data-rise>
          Our vision
        </p>
        <h2 className="display display--center" data-rise>
          Better Markets.
          <br />
          Stronger Farmers.
          <br />
          A Smarter Future.
        </h2>
      </div>
      <div className="wrap vision__principles">
        {PRINCIPLES.map((p, i) => (
          <article key={p.k} className="principle" data-rise>
            <span className="principle__n">0{i + 1}</span>
            <h3>{p.k}</h3>
            <p>{p.t}</p>
          </article>
        ))}
      </div>
    </section>
  );
});

export default VisionSection;
