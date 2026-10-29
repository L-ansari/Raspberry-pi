import { useState } from 'react';
import { login } from '../services/api.js';

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function submit(event) {
    event.preventDefault();
    if (busy || !username.trim() || !password) return;
    setBusy(true); setError('');
    try { onLogin(await login(username, password)); }
    catch (failure) { setError(failure instanceof TypeError ? 'Unable to reach the server. Please try again.' : failure.message); }
    finally { setBusy(false); setPassword(''); }
  }
  return <main className="login-page">
    <form className="login-card" onSubmit={submit} aria-busy={busy}>
      <span className="login-card__brand">Smart Greenhouse</span>
      <h1>Welcome back</h1><p>Sign in to monitor your greenhouse.</p>
      <label htmlFor="login-username">Username</label>
      <input id="login-username" autoComplete="username" required maxLength={150} value={username} onChange={(e) => setUsername(e.target.value)} />
      <label htmlFor="login-password">Password</label>
      <input id="login-password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
      {error && <p className="form-error" role="alert">{error}</p>}
      <button type="submit" disabled={busy || !username.trim() || !password}>{busy ? 'Signing in…' : 'Sign in'}</button>
      <p className="assistant-panel__note">Use an account provided by your project administrator.</p>
    </form>
  </main>;
}
