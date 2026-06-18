import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { User, Mail, Lock, ArrowRight, Loader, Briefcase } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { registerUser } from '../api';

export default function Register() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: '', email: '', password: '', confirm: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (form.password !== form.confirm) { setError('Passwords do not match'); return; }
    if (form.password.length < 6) { setError('Password must be at least 6 characters'); return; }

    setLoading(true);
    try {
      const res = await registerUser(form.name, form.email, form.password);
      login(res.access_token, res.user);
      navigate('/');
    } catch (e: any) {
      setError(e.message || 'Registration failed');
    }
    setLoading(false);
  };

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'var(--bg)', padding: 24,
    }}>
      {/* Background glow */}
      <div style={{
        position: 'fixed', top: '20%', left: '50%', transform: 'translateX(-50%)',
        width: 600, height: 600, borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />

      <div style={{ width: '100%', maxWidth: 420, position: 'relative', zIndex: 1 }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <div style={{
            width: 56, height: 56, borderRadius: 16, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px',
            boxShadow: '0 0 32px rgba(99,102,241,0.4)',
          }}>
            <Briefcase size={26} color="white" />
          </div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 900, letterSpacing: '-0.03em', marginBottom: 6 }}>
            Create Account
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            Join JobMatchr and find your perfect role
          </p>
        </div>

        {/* Card */}
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
              <label>Full Name</label>
              <div style={{ position: 'relative' }}>
                <User size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input className="input" type="text" placeholder="Muhammad Ahmad"
                  value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))}
                  style={{ paddingLeft: 36 }} required />
              </div>
            </div>

            <div className="input-group">
              <label>Email Address</label>
              <div style={{ position: 'relative' }}>
                <Mail size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input className="input" type="email" placeholder="you@example.com"
                  value={form.email} onChange={e => setForm(p => ({ ...p, email: e.target.value }))}
                  style={{ paddingLeft: 36 }} required />
              </div>
            </div>

            <div className="input-group">
              <label>Password</label>
              <div style={{ position: 'relative' }}>
                <Lock size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input className="input" type="password" placeholder="Min. 6 characters"
                  value={form.password} onChange={e => setForm(p => ({ ...p, password: e.target.value }))}
                  style={{ paddingLeft: 36 }} required />
              </div>
            </div>

            <div className="input-group">
              <label>Confirm Password</label>
              <div style={{ position: 'relative' }}>
                <Lock size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input className="input" type="password" placeholder="Repeat password"
                  value={form.confirm} onChange={e => setForm(p => ({ ...p, confirm: e.target.value }))}
                  style={{ paddingLeft: 36 }} required />
              </div>
            </div>

            <button className="btn btn-primary" type="submit" disabled={loading}
              style={{ marginTop: 4, height: 46, fontSize: '0.9rem', fontWeight: 700 }}>
              {loading
                ? <><Loader size={16} style={{ animation: 'spin 0.7s linear infinite' }} /> Creating account...</>
                : <><ArrowRight size={16} /> Create Account</>
              }
            </button>
          </form>

          <div style={{ textAlign: 'center', marginTop: 24, fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Already have an account?{' '}
            <Link to="/login" style={{ color: 'var(--accent)', fontWeight: 600, textDecoration: 'none' }}>
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
