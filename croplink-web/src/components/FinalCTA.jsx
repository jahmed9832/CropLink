import { Link } from '../router.jsx';
import { ROUTES } from '../config.js';

export default function FinalCTA() {
  return (
    <section className="cta">
      <div className="cta__orb" aria-hidden="true" />
      <div className="wrap cta__inner">
        <h2 className="display display--xl" data-rise>
          Your Harvest.
          <br />
          <span className="lime">Your Future.</span>
        </h2>
        <p className="lead" data-rise>
          Build a better connection between your hard work and the market.
        </p>
        <div className="cta__buttons" data-rise>
          <Link to={`${ROUTES.register}?role=farmer`} className="btn btn--lime btn--lg">
            Join as Farmer
          </Link>
          <Link to={`${ROUTES.register}?role=buyer`} className="btn btn--ghost btn--lg">
            Join as Buyer
          </Link>
          <a href="#platform" className="btn btn--ghost btn--lg">
            Explore the Platform
          </a>
        </div>
      </div>
    </section>
  );
}
