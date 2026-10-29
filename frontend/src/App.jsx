import Dashboard from './pages/Dashboard.jsx';
import Login from './pages/Login.jsx';
import { useEffect, useState } from 'react';
import { getCurrentUser, getSession, logout } from './services/api.js';

export default function App() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(Boolean(getSession()?.access));
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const clear = () => { setUser(null); setChecking(false); setError(''); };
    window.addEventListener('greenhouse-logout', clear);
    return () => window.removeEventListener('greenhouse-logout', clear);
  }, []);
  useEffect(() => {
    let active = true;
    if (!getSession()?.access) { setChecking(false); return; }
    setChecking(true); setError('');
    getCurrentUser().then((profile) => { if (active) setUser(profile); })
      .catch((error) => { if (active && getSession() && error.message !== 'Session changed.') setError('Unable to verify your session. Check the server and retry.'); })
      .finally(() => { if (active) setChecking(false); });
    return () => { active = false; };
  }, [attempt]);
  if (checking) return <main className="session-state" role="status">Checking your session…</main>;
  if (error) return <main className="session-state"><p role="alert">{error}</p><button onClick={() => setAttempt((n) => n + 1)}>Retry</button><button onClick={logout}>Sign out</button></main>;
  return user ? <Dashboard key={user.id} user={user} onLogout={logout} /> : <Login onLogin={setUser} />;
}
