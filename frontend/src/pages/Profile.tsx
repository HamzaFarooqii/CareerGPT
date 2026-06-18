import { useState } from 'react';
import { User, MapPin, Code, Briefcase, Globe, Github, Linkedin, Save, Loader, CheckCircle, Trash2, Clock } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { updateProfile, removeApplication } from '../api';

const STATUS_COLORS: Record<string, string> = {
  applied: '#6366f1',
  interviewing: '#f59e0b',
  offered: '#22c55e',
  rejected: '#ef4444',
  withdrawn: '#6b7280',
};

const STATUS_OPTIONS = ['applied', 'interviewing', 'offered', 'rejected', 'withdrawn'];

export default function Profile() {
  const { user, updateUser, logout } = useAuth();
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: user?.name || '',
    bio: user?.profile?.bio || '',
    phone: user?.profile?.phone || '',
    location: user?.profile?.location || '',
    linkedin: user?.profile?.linkedin || '',
    github: user?.profile?.github || '',
    portfolio: user?.profile?.portfolio || '',
    skills: (user?.profile?.skills || []).join(', '),
    preferred_job_titles: (user?.profile?.preferred_job_titles || []).join(', '),
    preferred_locations: (user?.profile?.preferred_locations || []).join(', '),
  });

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await updateProfile({
        name: form.name,
        profile: {
          bio: form.bio,
          phone: form.phone,
          location: form.location,
          linkedin: form.linkedin,
          github: form.github,
          portfolio: form.portfolio,
          skills: form.skills.split(',').map(s => s.trim()).filter(Boolean),
          preferred_job_titles: form.preferred_job_titles.split(',').map(s => s.trim()).filter(Boolean),
          preferred_locations: form.preferred_locations.split(',').map(s => s.trim()).filter(Boolean),
        },
      });
      updateUser(updated);
      setEditing(false);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e: any) {
      showToast(e.message || 'Save failed');
    }
    setSaving(false);
  };

  const handleRemoveApp = async (jobId: string) => {
    try {
      const updated = await removeApplication(jobId);
      updateUser(updated);
      showToast('Application removed');
    } catch { showToast('Failed to remove'); }
  };

  if (!user) return null;

  return (
    <div style={{ position: 'relative', zIndex: 1 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32 }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: 4 }}>My Profile</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Manage your info and track applications</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {!editing ? (
            <button className="btn btn-primary" onClick={() => setEditing(true)} style={{ height: 38 }}>
              Edit Profile
            </button>
          ) : (
            <>
              <button className="btn btn-ghost" onClick={() => setEditing(false)} style={{ height: 38 }}>Cancel</button>
              <button className="btn btn-primary" onClick={handleSave} disabled={saving} style={{ height: 38 }}>
                {saving ? <><Loader size={14} style={{ animation: 'spin 0.7s linear infinite' }} /> Saving...</> : <><Save size={14} /> Save</>}
              </button>
            </>
          )}
          <button className="btn btn-ghost" onClick={logout} style={{ height: 38, color: 'var(--error)' }}>
            Sign Out
          </button>
        </div>
      </div>

      {saved && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 16px', borderRadius: 'var(--radius)', background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.2)', color: '#4ade80', marginBottom: 20, fontSize: '0.85rem' }}>
          <CheckCircle size={15} /> Profile saved successfully!
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        {/* Basic Info */}
        <div className="card" style={{ padding: 24, gridColumn: '1 / -1' }}>
          <div style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-muted)', marginBottom: 20, fontFamily: 'var(--font-mono)' }}>
            <User size={12} style={{ display: 'inline', marginRight: 6 }} /> Personal Info
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
            {[
              { key: 'name', label: 'Full Name', icon: <User size={12} /> },
              { key: 'phone', label: 'Phone', icon: null },
              { key: 'location', label: 'Location', icon: <MapPin size={12} /> },
              { key: 'linkedin', label: 'LinkedIn URL', icon: <Linkedin size={12} /> },
              { key: 'github', label: 'GitHub URL', icon: <Github size={12} /> },
              { key: 'portfolio', label: 'Portfolio URL', icon: <Globe size={12} /> },
            ].map(({ key, label, icon }) => (
              <div key={key} className="input-group" style={{ marginBottom: 0 }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 5 }}>{icon}{label}</label>
                {editing ? (
                  <input className="input" value={(form as any)[key]}
                    onChange={e => setForm(p => ({ ...p, [key]: e.target.value }))} />
                ) : (
                  <div style={{ padding: '8px 0', fontSize: '0.875rem', color: (form as any)[key] ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                    {(form as any)[key] || '—'}
                  </div>
                )}
              </div>
            ))}
            <div className="input-group" style={{ marginBottom: 0, gridColumn: '1 / -1' }}>
              <label>Bio</label>
              {editing ? (
                <textarea className="input" value={form.bio} rows={3}
                  onChange={e => setForm(p => ({ ...p, bio: e.target.value }))}
                  style={{ resize: 'vertical', fontFamily: 'inherit' }} />
              ) : (
                <div style={{ padding: '8px 0', fontSize: '0.875rem', color: form.bio ? 'var(--text-primary)' : 'var(--text-muted)', lineHeight: 1.6 }}>
                  {form.bio || '—'}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Skills & Preferences */}
        <div className="card" style={{ padding: 24, gridColumn: '1 / -1' }}>
          <div style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-muted)', marginBottom: 20, fontFamily: 'var(--font-mono)' }}>
            <Code size={12} style={{ display: 'inline', marginRight: 6 }} /> Skills & Job Preferences
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 16 }}>
            {[
              { key: 'skills', label: 'Skills (comma separated)', placeholder: 'Python, React, Docker, AWS...' },
              { key: 'preferred_job_titles', label: 'Preferred Job Titles', placeholder: 'Software Engineer, Backend Developer...' },
              { key: 'preferred_locations', label: 'Preferred Locations', placeholder: 'Remote, USA, Pakistan...' },
            ].map(({ key, label, placeholder }) => (
              <div key={key} className="input-group" style={{ marginBottom: 0 }}>
                <label>{label}</label>
                {editing ? (
                  <input className="input" value={(form as any)[key]} placeholder={placeholder}
                    onChange={e => setForm(p => ({ ...p, [key]: e.target.value }))} />
                ) : (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, paddingTop: 6 }}>
                    {((form as any)[key] || '').split(',').map((s: string) => s.trim()).filter(Boolean).map((s: string, i: number) => (
                      <span key={i} className="tag">{s}</span>
                    ))}
                    {!(form as any)[key] && <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>—</span>}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Applications tracker */}
        <div className="card" style={{ padding: 24, gridColumn: '1 / -1' }}>
          <div style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-muted)', marginBottom: 20, fontFamily: 'var(--font-mono)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span><Briefcase size={12} style={{ display: 'inline', marginRight: 6 }} /> Job Applications ({user.applications?.length || 0})</span>
          </div>
          {(!user.applications || user.applications.length === 0) ? (
            <div className="empty-state" style={{ padding: 32 }}>
              <Clock size={32} />
              <h3 style={{ fontSize: '1rem' }}>No applications yet</h3>
              <p>Track jobs you've applied to by clicking "Track Application" on a job listing</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {user.applications.map((app: any) => (
                <div key={app.job_id} style={{
                  display: 'flex', alignItems: 'center', gap: 16, padding: '14px 18px',
                  borderRadius: 'var(--radius)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)',
                }}>
                  <div style={{
                    width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                    background: STATUS_COLORS[app.status] || '#6b7280',
                    boxShadow: `0 0 8px ${STATUS_COLORS[app.status] || '#6b7280'}`,
                  }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 700, fontSize: '0.875rem' }}>{app.job_title || 'Job'}</div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>
                      {app.company && <span>{app.company} · </span>}
                      Applied {new Date(app.applied_at).toLocaleDateString()}
                    </div>
                  </div>
                  <span style={{
                    padding: '3px 10px', borderRadius: 20, fontSize: '0.7rem', fontWeight: 700, textTransform: 'capitalize',
                    background: `${STATUS_COLORS[app.status]}22`, color: STATUS_COLORS[app.status] || '#6b7280',
                    border: `1px solid ${STATUS_COLORS[app.status]}44`,
                  }}>
                    {app.status}
                  </span>
                  {app.notes && <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{app.notes}</div>}
                  <button className="btn btn-ghost" style={{ padding: '4px 8px', color: 'var(--error)' }}
                    onClick={() => handleRemoveApp(app.job_id)}>
                    <Trash2 size={13} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {toast && <div className="toast success">{toast}</div>}
    </div>
  );
}
