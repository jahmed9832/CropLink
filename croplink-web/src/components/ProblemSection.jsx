import { forwardRef } from 'react';

const BLOCKS = [
  { n: '01', title: 'Market Uncertainty', text: 'Farmers often lack timely market information to make confident selling decisions.' },
  { n: '02', title: 'Limited Connections', text: 'Finding reliable buyers and reaching better markets can be difficult.' },
  { n: '03', title: 'Information Asymmetry', text: 'Farmers may lack the tools to understand market demand, prices, and opportunities.' },
];

const ProblemSection = forwardRef(function ProblemSection(_, ref) {
  return (
    <section id="story" className="problem" ref={ref}>
      <div className="wrap">
        <p className="eyebrow eyebrow--dark" data-rise>
          The problem
        </p>
        <h2 className="problem__title" data-rise>
          Farmers Feed the World.
          <br />
          <em>But the Market Doesn&rsquo;t Always Reward Them.</em>
        </h2>
        <div className="problem__grid">
          {BLOCKS.map((b) => (
            <article className="pblock" key={b.n} data-rise>
              <span className="pblock__num" aria-hidden="true">
                {b.n}
              </span>
              <h3>
                <span className="pblock__idx">{b.n} —</span> {b.title}
              </h3>
              <p>{b.text}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
});

export default ProblemSection;
