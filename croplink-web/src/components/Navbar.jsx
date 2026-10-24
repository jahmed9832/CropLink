import { useEffect, useState } from 'react';
import { Menu, X } from 'lucide-react';
import { Link } from '../router.jsx';
import { ROUTES } from '../config.js';
import Logo from './Logo.jsx';

const LINKS = [
  { href: '#platform', label: 'Platform' },
  { href: '#intelligence', label: 'Intelligence' },
  { href: '#vision', label: 'Our Vision' },
];

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const on = () => setScrolled(window.scrollY > 40);
    on();
    window.addEventListener('scroll', on, { passive: true });
    return () => window.removeEventListener('scroll', on);
  }, []);

  useEffect(() => {
    document.body.style.overflow = open ? 'hidden' : '';
    return () => {
      document.body.style.overflow = '';
    };
  }, [open]);

  const close = () => setOpen(false);

  return (
    <header className={`nav ${scrolled ? 'is-scrolled' : ''} ${open ? 'is-open' : ''}`}>
      <div className="nav__inner">
        <a href="#top" className="nav__brand" onClick={close} aria-label="CropLink home">
          <Logo />
        </a>
        <nav className="nav__links" aria-label="Primary">
          {LINKS.map((l) => (
            <a key={l.href} href={l.href}>
              {l.label}
            </a>
          ))}
        </nav>
        <div className="nav__actions">
          <Link to={ROUTES.login} className="nav__login">
            Log In
          </Link>
          <Link to={ROUTES.register} className="btn btn--lime btn--sm">
            Get Started
          </Link>
        </div>
        <button className="nav__toggle" onClick={() => setOpen((o) => !o)} aria-label={open ? 'Close menu' : 'Open menu'} aria-expanded={open}>
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      <div className="nav__sheet" aria-hidden={!open}>
        {LINKS.map((l, i) => (
          <a key={l.href} href={l.href} onClick={close} style={{ '--i': i }} tabIndex={open ? 0 : -1}>
            {l.label}
          </a>
        ))}
        <Link to={ROUTES.login} onClick={close} style={{ '--i': 3 }} tabIndex={open ? 0 : -1}>
          Log In
        </Link>
        <Link to={ROUTES.register} className="btn btn--lime" onClick={close} style={{ '--i': 4 }} tabIndex={open ? 0 : -1}>
          Get Started
        </Link>
      </div>
    </header>
  );
}
