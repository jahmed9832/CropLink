import { useEffect, useState } from 'react';

// Tiny History-API router: the landing page owns "/", auth screens own /login and /register.
export function navigate(path) {
  if (window.location.pathname + window.location.search === path) return;
  window.history.pushState({}, '', path);
  window.dispatchEvent(new Event('croplink:navigate'));
  window.scrollTo(0, 0);
}

export function usePath() {
  const [path, setPath] = useState(window.location.pathname);
  useEffect(() => {
    const sync = () => setPath(window.location.pathname);
    window.addEventListener('popstate', sync);
    window.addEventListener('croplink:navigate', sync);
    return () => {
      window.removeEventListener('popstate', sync);
      window.removeEventListener('croplink:navigate', sync);
    };
  }, []);
  return path;
}

export function useSearch() {
  const [search, setSearch] = useState(window.location.search);
  useEffect(() => {
    const sync = () => setSearch(window.location.search);
    window.addEventListener('popstate', sync);
    window.addEventListener('croplink:navigate', sync);
    return () => {
      window.removeEventListener('popstate', sync);
      window.removeEventListener('croplink:navigate', sync);
    };
  }, []);
  return search;
}

export function Link({ to, children, onClick, ...rest }) {
  return (
    <a
      href={to}
      onClick={(e) => {
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
        e.preventDefault();
        onClick?.(e);
        navigate(to);
      }}
      {...rest}
    >
      {children}
    </a>
  );
}
