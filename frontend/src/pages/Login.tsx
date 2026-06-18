import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Mail, Lock, ArrowRight, Loader, Briefcase } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { loginUser } from '../api';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await loginUser(form.email, form.password);
      login(res.access_token, res.user);
      navigate('/');
    } catch (e: any) {
      setError(e.message || 'Login failed');
    }
    setLoading(false);
  };

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'var(--bg)', padding: 24,
    }}>
      <div style={{
        position: 'fixed', top: '20%', left: '50%', transform: 'translateX(-50%)',
        width: 600, height: 600, borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />

      <div style={{ width: '100%', maxWidth: 400, position: 'relative', zIndex: 1 }}>
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <div style={{
            width: 56, height: 56, borderRadius: 16, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px',
            boxShadow: '0 0 32px rgba(99,102,241,0.4)',
          }}>
            <Briefcase size={26} color="white" />
          </div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 900, letterSpacing: '-0.03em', marginBottom: 6 }}>
            Welcome back
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            Sign in to your JobMatchr account
          </p>
        </div>

        <div className="card" style={{ padding: 32 }}>
          {error && (
            <div style={{
              padding: '12px 16px', borderRadius: 'var(--radius)', marginBottom: 20,
              background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
              color: '#f87171', fontSize: '0.85rem',
            }}>
              ⚠ {error}
            </div>
          )}

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
            <div className="input-group">
              <label>Email Address</label>
              <div style={{ position: 'relative' }}>
                <Mail size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input className="input" type="email" placeholder="you@example.com"
                  value={form.email} onChange={e => setForm(p => ({ ...p, email: e.target.value }))}
                  style={{ paddingLeft: 36 }} required autoFocus />
              </div>
            </div>

            <div className="input-group">
              <label>Password</label>
              <div style={{ position: 'relative' }}>
                <Lock size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input className="input" type="password" placeholder="Your password"
                  value={form.password} onChange={e => setForm(p => ({ ...p, password: e.target.value }))}
                  style={{ paddingLeft: 36 }} required />
              </div>
            </div>

            <button className="btn btn-primary" type="submit" disabled={loading}
              style={{ marginTop: 4, height: 46, fontSize: '0.9rem', fontWeight: 700 }}>
              {loading
                ? <><Loader size={16} style={{ animation: 'spin 0.7s linear infinite' }} /> Signing in...</>
                : <><ArrowRight size={16} /> Sign In</>
              }
            </button>
          </form>

          <div style={{ textAlign: 'center', marginTop: 24, fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Don't have an account?{' '}
            <Link to="/register" style={{ color: 'var(--accent)', fontWeight: 600, textDecoration: 'none' }}>
              Create one
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
