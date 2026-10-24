import { lazy, Suspense } from 'react';
import { usePath } from './router.jsx';
import LandingPage from './pages/LandingPage.jsx';

const AuthPage = lazy(() => import('./pages/AuthPage.jsx'));

export default function App() {
  const path = usePath();
  if (path === '/login' || path === '/register') {
    return (
      <Suspense fallback={null}>
        <AuthPage mode={path === '/login' ? 'login' : 'register'} />
      </Suspense>
    );
  }
  return <LandingPage />;
}
