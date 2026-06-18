import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Activity, Database, FileText, Briefcase, Target, TrendingUp, Zap, MessageSquare, ArrowUpRight, CheckCircle2, Clock } from 'lucide-react';
import { getJobStats, listResumes, healthCheck } from '../api';
import { useAuth } from '../context/AuthContext';

function AnimatedNumber({ value }: { value: number | string }) {
  return <span>{value}</span>;
}


export default function Dashboard() {
  const { user, isAuthenticated } = useAuth();
  const [stats, setStats] = useState<any>(null);
  const [resumeCount, setResumeCount] = useState(0);
  const [health, setHealth] = useState<any>(null);
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';

  useEffect(() => {
    getJobStats().then(setStats).catch(() => {});
    listResumes().then((r: any[]) => setResumeCount(r.length)).catch(() => {});
    healthCheck().then(setHealth).catch(() => {});
  }, []);

  const statItems = [
    { label: 'Resumes Uploaded', value: resumeCount, sub: 'Parsed & embedded', icon: FileText, color: 'var(--accent)' },
    { label: 'Jobs Scraped', value: stats?.total_jobs ?? '—', sub: 'Across all sources', icon: Briefcase, color: 'var(--cyan)' },
    { label: 'AI Extracted', value: stats?.with_extraction ?? '—', sub: 'Skills & requirements', icon: Zap, color: '#a78bfa' },
    { label: 'Embeddings Ready', value: stats?.with_embeddings ?? '—', sub: 'Ready for matching', icon: Target, color: 'var(--success)' },
  ];

  const systemItems = [
    { label: 'API Server', ok: !!health, status: health ? 'Online' : 'Connecting...' },
    { label: 'MongoDB', ok: health?.database === 'connected', status: health?.database === 'connected' ? 'Connected' : 'Checking...' },
    { label: 'Groq LLM', ok: true, status: 'Active' },
    { label: 'ChromaDB', ok: true, status: 'Active' },
  ];

  const quickActions = [
    { icon: FileText, label: 'Upload Resume', desc: 'Parse & embed your CV', href: '/resumes', color: 'var(--accent)' },
    { icon: Briefcase, label: 'Search Jobs', desc: 'Scrape from 6+ sources', href: '/jobs', color: 'var(--cyan)' },
    { icon: Target, label: 'AI Match', desc: 'Find your best fits', href: '/matches', color: '#a78bfa' },
    { icon: MessageSquare, label: 'Career Coach', desc: 'AI career guidance', href: '/coach', color: 'var(--success)' },
    { icon: Zap, label: 'Apply Agent', desc: 'Generate cover letters', href: '/apply', color: 'var(--warning)' },
  ];

  return (
    <div className="animate-fadein">
      {/* Welcome Banner */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="page-header"
      >
        <div className="breadcrumb">✦ CareerGPT · Dashboard</div>
        <h2>
          {greeting},{' '}
          <span>{isAuthenticated && user?.name ? user.name.split(' ')[0] : 'Explorer'}</span> 👋
        </h2>
        <p>Your AI-powered career command center. Here's what's happening today.</p>
      </motion.div>

      {/* Stat Cards */}
      <div className="stats-grid">
        {statItems.map((s, i) => (
          <motion.div key={s.label} className="stat-card"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08, duration: 0.35 }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div className="stat-label">{s.label}</div>
              <div style={{ width: 32, height: 32, borderRadius: 8, background: `${s.color}18`, border: `1px solid ${s.color}28`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <s.icon size={15} color={s.color} />
              </div>
            </div>
            <div className="stat-value"><AnimatedNumber value={s.value} /></div>
            <div className="stat-sub">{s.sub}</div>
          </motion.div>
        ))}
      </div>

      {/* Middle row: system status + sources + AI insight */}
      <div className="grid-2" style={{ marginBottom: 24 }}>
        {/* System Status */}
        <motion.div className="card" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
            <Activity size={17} color="var(--accent)" />
            <span style={{ fontWeight: 700, fontSize: '0.92rem' }}>System Status</span>
            <span className="dot dot-green" style={{ marginLeft: 'auto' }} />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {systemItems.map(item => (
              <div key={item.label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '9px 14px', borderRadius: 8, background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)' }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-2)' }}>{item.label}</span>
                <span style={{ fontSize: '0.72rem', fontFamily: 'var(--mono)', fontWeight: 700, color: item.ok ? 'var(--success)' : 'var(--warning)', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span className={`dot ${item.ok ? 'dot-green' : 'dot-yellow'}`} />
                  {item.status}
                </span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Jobs by Source */}
        <motion.div className="card" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.35 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
            <Database size={17} color="#a78bfa" />
            <span style={{ fontWeight: 700, fontSize: '0.92rem' }}>Jobs by Source</span>
            <span style={{ marginLeft: 'auto', fontSize: '0.68rem', fontFamily: 'var(--mono)', color: 'var(--text-3)' }}>
              {stats?.total_jobs ?? 0} total
            </span>
          </div>
          {stats?.by_source && Object.keys(stats.by_source).length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {Object.entries(stats.by_source).map(([src, count]: any) => {
                const pct = stats.total_jobs > 0 ? Math.round((count / stats.total_jobs) * 100) : 0;
                return (
                  <div key={src}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ fontSize: '0.78rem', color: 'var(--text-2)' }}>{src}</span>
                      <span style={{ fontSize: '0.75rem', fontWeight: 700, fontFamily: 'var(--mono)', color: 'var(--accent)' }}>{count}</span>
                    </div>
                    <div className="progress-bar">
                      <motion.div className="progress-fill" initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ delay: 0.5, duration: 0.8 }} />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--text-3)', fontSize: '0.82rem' }}>
              No jobs scraped yet. Go to <strong style={{ color: 'var(--accent)' }}>Job Search</strong> to start.
            </div>
          )}
        </motion.div>
      </div>

      {/* Quick Actions */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.45 }}>
        <div style={{ fontSize: '0.62rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--text-3)', fontFamily: 'var(--mono)', marginBottom: 14 }}>
          Quick Actions
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
          {[
            { icon: FileText, label: 'Upload Resume', desc: 'Parse & embed your CV', href: '/resumes', color: 'var(--accent)' },
            { icon: Briefcase, label: 'Search Jobs', desc: 'Scrape from 6+ sources', href: '/jobs', color: 'var(--cyan)' },
            { icon: Target, label: 'AI Match', desc: 'Find your best fits', href: '/matches', color: '#a78bfa' },
            { icon: MessageSquare, label: 'Career Coach', desc: 'AI career guidance', href: '/coach', color: 'var(--success)' },
            { icon: Zap, label: 'Apply Agent', desc: 'Generate cover letters', href: '/apply', color: 'var(--warning)' },
          ].map((action, i) => (
            <motion.a
              key={action.label}
              href={action.href}
              whileHover={{ y: -3, scale: 1.02 }}
              transition={{ type: 'spring', stiffness: 400 }}
              style={{
                display: 'flex', alignItems: 'center', gap: 14, padding: '16px 18px',
                background: 'var(--surface)', border: '1px solid var(--border)',
                borderRadius: 'var(--r-lg)', textDecoration: 'none', color: 'inherit',
                cursor: 'pointer',
              }}
            >
              <div style={{ width: 38, height: 38, borderRadius: 10, background: `${action.color}15`, border: `1px solid ${action.color}25`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <action.icon size={17} color={action.color} />
              </div>
              <div>
                <div style={{ fontWeight: 700, fontSize: '0.84rem', marginBottom: 2 }}>{action.label}</div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-3)' }}>{action.desc}</div>
              </div>
              <ArrowUpRight size={14} style={{ marginLeft: 'auto', color: 'var(--text-3)' }} />
            </motion.a>
          ))}
        </div>
      </motion.div>

      {/* AI Insight Banner */}
      {!isAuthenticated && (
        <motion.div
          className="insight-card"
          style={{ marginTop: 24 }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
        >
          <div className="insight-label">
            <Zap size={13} /> AI Insight
          </div>
          <p style={{ fontSize: '0.84rem', color: 'var(--text-2)', lineHeight: 1.7 }}>
            <strong style={{ color: 'var(--text)' }}>Create a free account</strong> to save your job searches, track applications, and unlock personalized AI matching — all powered by Groq LLM + ChromaDB semantic search.
          </p>
          <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
            <a href="/register" className="btn btn-primary btn-sm">Get Started Free</a>
            <a href="/login" className="btn btn-ghost btn-sm">Sign In</a>
          </div>
        </motion.div>
      )}
    </div>
  );
}
