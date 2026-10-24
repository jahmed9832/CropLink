import { useEffect, useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import { Link, useSearch } from '../router.jsx';
import { ROUTES } from '../config.js';
import Logo from '../components/Logo.jsx';
import { getSession, login, logout, register } from '../api/auth.js';

// Minimal web auth wired to the real backend (POST /auth/login, POST /auth/register).
// The farmer/buyer tools themselves currently live in the CropLink mobile app.
export default function AuthPage({ mode }) {
  const isLogin = mode === 'login';
  const search = useSearch();
  const queryRole = new URLSearchParams(search).get('role');
  const [session, setSession] = useState(getSession());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [role, setRole] = useState(queryRole === 'buyer' ? 'buyer' : 'farmer');

  useEffect(() => {
    if (queryRole === 'buyer' || queryRole === 'farmer') {
      setRole(queryRole);
    }
  }, [queryRole]);

  const submit = async (e) => {
    e.preventDefault();
    if (busy) return;
    setError('');
    setBusy(true);
    const f = new FormData(e.currentTarget);
    try {
      const s = isLogin
        ? await login({ phone: f.get('phone').trim(), password: f.get('password') })
        : await register({
            name: f.get('name').trim(),
            phone: f.get('phone').trim(),
            password: f.get('password'),
            role,
            district: f.get('district').trim(),
          });
      setSession(s);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth">
      <div className="auth__card">
        <Link to="/" className="auth__back">
          <ArrowLeft size={16} /> Back to CropLink
        </Link>
        <Link to="/" style={{ textDecoration: 'none', color: 'inherit', display: 'inline-flex' }} aria-label="CropLink homepage">
          <Logo />
        </Link>

        {session ? (
          <div className="auth__done">
            <h1>You&rsquo;re signed in.</h1>
            <p>
              Your {session.role} account is ready. The CropLink web dashboard is not available yet — the farmer and buyer tools currently run in the CropLink mobile app, where you can sign in with the same phone number and password.
            </p>
            <button
              className="btn btn--ghost"
              onClick={() => {
                logout();
                setSession(null);
              }}
            >
              Sign out
            </button>
          </div>
        ) : (
          <form onSubmit={submit} className="auth__form">
            <h1>{isLogin ? 'Welcome back.' : 'Join CropLink.'}</h1>
            <p className="auth__sub">{isLogin ? 'Log in with your phone number.' : 'Create a farmer or buyer account.'}</p>

            {!isLogin && (
              <>
                <div className="seg" role="radiogroup" aria-label="Account type">
                  {['farmer', 'buyer'].map((r) => (
                    <button type="button" key={r} role="radio" aria-checked={role === r} className={role === r ? 'is-on' : ''} onClick={() => setRole(r)}>
                      {r === 'farmer' ? 'I’m a farmer' : 'I’m a buyer'}
                    </button>
                  ))}
                </div>
                <label>
                  Full name
                  <input name="name" required autoComplete="name" />
                </label>
              </>
            )}
            <label>
              Phone number
              <input name="phone" type="tel" required minLength={6} autoComplete="tel" placeholder="01XXXXXXXXX" />
            </label>
            <label>
              Password
              <input name="password" type="password" required minLength={6} autoComplete={isLogin ? 'current-password' : 'new-password'} />
            </label>
            {!isLogin && (
              <label>
                District
                <input name="district" placeholder="Dhaka" autoComplete="address-level2" />
              </label>
            )}

            {error && (
              <p className="auth__error" role="alert">
                {error}
              </p>
            )}
            <button className="btn btn--lime btn--lg" disabled={busy}>
              {busy ? 'Please wait…' : isLogin ? 'Log In' : 'Create account'}
            </button>
            <p className="auth__hint">The server may take up to a minute to wake on the first request.</p>
            <p className="auth__switch">
              {isLogin ? (
                <>
                  New to CropLink? <Link to={ROUTES.register}>Get started</Link>
                </>
              ) : (
                <>
                  Already have an account? <Link to={ROUTES.login}>Log in</Link>
                </>
              )}
            </p>
          </form>
        )}
      </div>
    </div>
  );
}
