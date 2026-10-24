import { Link } from '../router.jsx';
import { API_URL, ROUTES } from '../config.js';
import Logo from './Logo.jsx';

// No contact details or social profiles exist in the project, so none are shown.
export default function Footer() {
  return (
    <footer className="footer">
      <div className="wrap footer__grid">
        <div className="footer__brand">
          <Logo />
          <p>Market intelligence and fair-price access for farmers, starting in Bangladesh.</p>
        </div>
        <nav className="footer__nav" aria-label="Footer">
          <a href="#platform">Platform</a>
          <a href="#intelligence">Intelligence</a>
          <a href="#vision">Our Vision</a>
          <Link to={ROUTES.login}>Log In</Link>
          <Link to={ROUTES.register}>Get Started</Link>
          <a href={`${API_URL}/docs`} target="_blank" rel="noreferrer">
            API Docs
          </a>
        </nav>
      </div>
      <div className="wrap footer__bar">
        <span>© {new Date().getFullYear()} CropLink. All rights reserved.</span>
      </div>
    </footer>
  );
}
