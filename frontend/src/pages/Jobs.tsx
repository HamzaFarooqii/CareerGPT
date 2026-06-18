import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search, Briefcase, MapPin, ExternalLink, Loader, Building,
  ChevronRight, Globe, Filter, Bookmark, BookmarkCheck, X,
  Zap, FileText, Sparkles, Download
} from 'lucide-react';
import { scrapeJobs, listJobs, getJob, toggleSavedJob } from '../api';
import { useAuth } from '../context/AuthContext';
import JobApplyModal from '../components/JobApplyModal';

const LOCATION_OPTIONS = [
  { label: '🌍 Worldwide / Remote', value: 'Worldwide' },
  { label: '🇵🇰 Pakistan', value: 'Pakistan' },
  { label: '🇺🇸 United States', value: 'USA' },
  { label: '🇬🇧 United Kingdom', value: 'UK' },
  { label: '🇨🇦 Canada', value: 'Canada' },
  { label: '🇦🇺 Australia', value: 'Australia' },
  { label: '🇩🇪 Germany', value: 'Germany' },
  { label: '🇦🇪 UAE / Dubai', value: 'UAE' },
  { label: '📡 Remote Only', value: 'Remote' },
];

const JOB_SUGGESTIONS = [
  'Software Engineer', 'Python Developer', 'React Developer',
  'Full Stack Developer', 'Data Scientist', 'Machine Learning Engineer',
  'DevOps Engineer', 'Backend Developer', 'Frontend Developer',
  'AI Engineer', 'Cloud Engineer', 'Node.js Developer',
  'Android Developer', 'iOS Developer', 'Product Manager',
];

const SOURCES = [
  { id: 'remotive.com',  label: 'Remotive',  icon: '🌐', desc: 'Remote tech jobs' },
  { id: 'jobicy.com',    label: 'Jobicy',    icon: '💼', desc: 'Remote opportunities' },
  { id: 'rozee.pk',      label: 'Rozee.pk',  icon: '🇵🇰', desc: 'Pakistan jobs' },
  { id: 'remoteok.com',  label: 'RemoteOK',  icon: '🚀', desc: 'Remote OK jobs' },
  { id: 'wellfound.com', label: 'Wellfound', icon: '⭐', desc: 'Startup jobs' },
];

// Location → recommended sources hint
const LOCATION_HINT: Record<string, string> = {
  pakistan: 'Tip: Rozee.pk is best for Pakistan jobs',
  remote: 'Remotive, Jobicy & RemoteOK have the best remote listings',
  worldwide: 'All remote boards active',
};

function SkeletonCard() {
  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '18px 22px', display: 'flex', gap: 16 }}>
      <div style={{ width: 42, height: 42, borderRadius: 10, background: 'var(--border)', animation: 'pulse 1.5s infinite' }} />
      <div style={{ flex: 1 }}>
        <div style={{ height: 14, background: 'var(--border)', borderRadius: 4, marginBottom: 8, width: '60%', animation: 'pulse 1.5s infinite' }} />
        <div style={{ height: 11, background: 'var(--border)', borderRadius: 4, width: '40%', animation: 'pulse 1.5s infinite' }} />
      </div>
    </div>
  );
}

export default function Jobs() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [applyJob, setApplyJob] = useState<any>(null);
  const [scraping, setScraping] = useState(false);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState('Software Engineer');
  const [lastQuery, setLastQuery] = useState('');
  const [lastLocation, setLastLocation] = useState('');
  const { user, isAuthenticated } = useAuth();
  const [locationInput, setLocationInput] = useState('Pakistan');
  const [showLocationDD, setShowLocationDD] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [filterSearch, setFilterSearch] = useState('');
  const [scrapeResult, setScrapeResult] = useState<any[] | null>(null);
  const [toast, setToast] = useState<{ msg: string; type: string } | null>(null);
  const [activeSources, setActiveSources] = useState<string[]>(['rozee.pk']);

  const showToast = (msg: string, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 4000);
  };

  // Auto-select sources based on location
  const handleLocationChange = (loc: string) => {
    setLocationInput(loc);
    const l = loc.toLowerCase();
    if (l === 'pakistan' || l === 'uae') setActiveSources(['rozee.pk']);
    else if (l === 'remote' || l === 'worldwide') setActiveSources(['remotive.com', 'jobicy.com', 'remoteok.com']);
    else setActiveSources(['remotive.com', 'remoteok.com', 'wellfound.com']);
  };

  const load = useCallback((sq?: string, sl?: string) => {
    setLoading(true);
    listJobs({
      search: filterSearch || undefined,
      query: (sq ?? lastQuery) || undefined,
      location: (sl ?? lastLocation) || undefined,
      limit: 100,
    })
      .then(data => setJobs(Array.isArray(data) ? data : []))
      .catch(e => console.error(e))
      .finally(() => setLoading(false));
  }, [filterSearch, lastQuery, lastLocation]);

  useEffect(() => { load(); }, [load]);

  const handleScrape = async () => {
    if (!query.trim()) return;
    if (activeSources.length === 0) { showToast('Select at least one source', 'error'); return; }
    setScraping(true);
    setScrapeResult(null);
    const q = query.trim();
    const loc = locationInput;
    try {
      const results = await scrapeJobs(q, loc, 3, activeSources);
      setScrapeResult(results);
      const totalNew = results.reduce((s: number, r: any) => s + (r.jobs_new || 0), 0);
      showToast(`✅ ${totalNew} new jobs scraped for "${q}" in ${loc}`);
      setLastQuery(q.toLowerCase());
      setLastLocation(loc.toLowerCase());
      setTimeout(() => load(q.toLowerCase(), loc.toLowerCase()), 2000);
      setTimeout(() => load(q.toLowerCase(), loc.toLowerCase()), 6000);
    } catch (e: any) { showToast(e.message || 'Scrape failed', 'error'); }
    setScraping(false);
  };

  const handleSaveJob = async (jobId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!isAuthenticated) { showToast('Sign in to save jobs', 'error'); return; }
    try {
      const res = await toggleSavedJob(jobId);
      showToast(res.saved ? '✅ Job saved!' : 'Removed from saved');
    } catch { showToast('Failed to save job', 'error'); }
  };

  const viewJob = async (id: string) => {
    try {
      const j = await getJob(id);
      setSelected(j);
    } catch { showToast('Failed to load job', 'error'); }
  };

  const openApply = async (e: React.MouseEvent, job: any) => {
    e.stopPropagation();
    // If we already have full details, use them; otherwise fetch
    if (job.description !== undefined) {
      setApplyJob(job);
    } else {
      try {
        const full = await getJob(job.id);
        setApplyJob(full);
      } catch {
        setApplyJob(job);
      }
    }
  };

  const filteredSuggestions = JOB_SUGGESTIONS.filter(s =>
    s.toLowerCase().includes(query.toLowerCase()) && s !== query
  ).slice(0, 6);

  const locHint = LOCATION_HINT[locationInput.toLowerCase()];

  return (
    <div onClick={() => { setShowLocationDD(false); setShowSuggestions(false); }}>
      <div className="page-header">
        <div className="breadcrumb">✦ CareerGPT · Job Search</div>
        <h2>Job <span>Search</span></h2>
        <p>Smart scraping across {SOURCES.length} platforms — filtered by YOUR location</p>
      </div>

      {/* Search Panel */}
      <motion.div className="card" style={{ marginBottom: 24 }} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
        <div style={{ fontSize: '0.62rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--text-3)', fontFamily: 'var(--mono)', marginBottom: 16 }}>
          🔍 Search Jobs
        </div>

        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 14 }}>
          {/* Job query */}
          <div style={{ flex: 2, minWidth: 220, position: 'relative' }}>
            <label style={{ fontSize: '0.62rem', color: 'var(--text-3)', display: 'block', marginBottom: 6, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', fontFamily: 'var(--mono)' }}>Job Title / Role</label>
            <div style={{ position: 'relative' }}>
              <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-3)', pointerEvents: 'none' }} />
              <input
                className="input"
                value={query}
                onChange={e => { setQuery(e.target.value); setShowSuggestions(true); }}
                onFocus={() => setShowSuggestions(true)}
                onClick={e => e.stopPropagation()}
                placeholder="e.g. Python Developer, React Engineer"
                style={{ paddingLeft: 36 }}
                onKeyDown={e => e.key === 'Enter' && handleScrape()}
              />
              <AnimatePresence>
                {showSuggestions && filteredSuggestions.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                    style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 100, background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--r)', marginTop: 4, boxShadow: '0 16px 48px rgba(0,0,0,0.5)' }}
                    onClick={e => e.stopPropagation()}
                  >
                    {filteredSuggestions.map(s => (
                      <div key={s}
                        style={{ padding: '9px 14px', cursor: 'pointer', fontSize: '0.8rem', color: 'var(--text-2)', display: 'flex', alignItems: 'center', gap: 8 }}
                        onMouseEnter={e => (e.currentTarget.style.background = 'rgba(99,102,241,0.08)')}
                        onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                        onClick={() => { setQuery(s); setShowSuggestions(false); }}
                      >
                        <Search size={11} style={{ opacity: 0.4 }} /> {s}
                      </div>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>

          {/* Location */}
          <div style={{ flex: 1, minWidth: 180, position: 'relative' }}>
            <label style={{ fontSize: '0.62rem', color: 'var(--text-3)', display: 'block', marginBottom: 6, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', fontFamily: 'var(--mono)' }}>Location</label>
            <div style={{ position: 'relative' }}>
              <Globe size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-3)', pointerEvents: 'none' }} />
              <input
                className="input"
                value={locationInput}
                onChange={e => handleLocationChange(e.target.value)}
                onFocus={() => setShowLocationDD(true)}
                onClick={e => { e.stopPropagation(); setShowLocationDD(true); }}
                style={{ paddingLeft: 36 }}
              />
              <AnimatePresence>
                {showLocationDD && (
                  <motion.div
                    initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                    style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 100, background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--r)', marginTop: 4, boxShadow: '0 16px 48px rgba(0,0,0,0.5)' }}
                    onClick={e => e.stopPropagation()}
                  >
                    {LOCATION_OPTIONS.map(opt => (
                      <div key={opt.value}
                        style={{ padding: '10px 14px', cursor: 'pointer', fontSize: '0.8rem', color: locationInput === opt.value ? 'var(--accent)' : 'var(--text-2)', background: locationInput === opt.value ? 'rgba(99,102,241,0.1)' : 'transparent', transition: 'background 0.15s' }}
                        onMouseEnter={e => { if (locationInput !== opt.value) e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
                        onMouseLeave={e => { if (locationInput !== opt.value) e.currentTarget.style.background = 'transparent'; }}
                        onClick={() => { handleLocationChange(opt.value); setShowLocationDD(false); }}
                      >{opt.label}</div>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
            {locHint && <div style={{ fontSize: '0.62rem', color: 'var(--accent)', marginTop: 5, fontFamily: 'var(--mono)' }}>💡 {locHint}</div>}
          </div>

          <div style={{ display: 'flex', alignItems: 'flex-end', paddingBottom: locHint ? 22 : 0 }}>
            <button className="btn btn-primary" onClick={handleScrape} disabled={scraping} style={{ height: 42, minWidth: 130 }}>
              {scraping ? <><Loader size={14} style={{ animation: 'spin 0.7s linear infinite' }} /> Scraping...</> : <><Search size={14} /> Find Jobs</>}
            </button>
          </div>
        </div>

        {/* Source toggles */}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ fontSize: '0.62rem', color: 'var(--text-3)', fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.08em', display: 'flex', alignItems: 'center', gap: 4 }}>
            <Filter size={11} /> Sources:
          </span>
          {SOURCES.map(src => (
            <button key={src.id}
              onClick={() => setActiveSources(prev => prev.includes(src.id) ? prev.filter(s => s !== src.id) : [...prev, src.id])}
              className={`source-pill ${activeSources.includes(src.id) ? 'active' : 'inactive'}`}
              title={src.desc}
            >
              {src.icon} {src.label}
            </button>
          ))}
        </div>

        {/* Scrape results summary */}
        <AnimatePresence>
          {scrapeResult && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 14, paddingTop: 14, borderTop: '1px solid var(--border)' }}>
              {scrapeResult.filter((r: any) => !r.errors?.[0]?.includes('Skipped')).map((r: any, i: number) => (
                <div key={i} style={{ padding: '8px 14px', borderRadius: 8, background: r.errors?.length ? 'rgba(239,68,68,0.08)' : 'rgba(16,185,129,0.08)', border: `1px solid ${r.errors?.length ? 'rgba(239,68,68,0.2)' : 'rgba(16,185,129,0.2)'}`, fontSize: '0.76rem' }}>
                  <span style={{ color: 'var(--accent)', fontWeight: 700 }}>{r.source}</span>
                  <span style={{ color: 'var(--text-3)', margin: '0 6px' }}>→</span>
                  <span style={{ color: 'var(--success)', fontWeight: 600 }}>{r.jobs_new} new</span>
                  <span style={{ color: 'var(--text-3)', margin: '0 4px' }}>/</span>
                  <span style={{ color: 'var(--text-2)' }}>{r.jobs_found} found</span>
                </div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Filter bar */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16, flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: 1, maxWidth: 360 }}>
          <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-3)', pointerEvents: 'none' }} />
          <input className="input" placeholder="Filter by title..." value={filterSearch} onChange={e => setFilterSearch(e.target.value)} style={{ paddingLeft: 36 }} />
        </div>
        {(lastQuery || lastLocation) && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 12px', borderRadius: 20, background: 'rgba(99,102,241,0.1)', border: '1px solid var(--accent-border)', fontSize: '0.72rem', color: 'var(--accent)', fontFamily: 'var(--mono)' }}>
            {lastQuery && `"${lastQuery}"`}{lastLocation && ` · ${lastLocation}`}
            <button onClick={() => { setLastQuery(''); setLastLocation(''); }} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-3)', lineHeight: 1 }}>
              <X size={12} />
            </button>
          </div>
        )}
        <span style={{ fontSize: '0.7rem', color: 'var(--text-3)', fontFamily: 'var(--mono)', marginLeft: 'auto' }}>
          {jobs.length} jobs
        </span>
      </div>

      {/* Job list */}
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {[1,2,3,4,5].map(i => <SkeletonCard key={i} />)}
        </div>
      ) : jobs.length === 0 ? (
        <div className="empty-state">
          <Briefcase size={48} />
          <h3>No jobs found</h3>
          <p>Search for a role above — results will appear filtered by your selected location</p>
        </div>
      ) : (
        <div className="jobs-list">
          {jobs.map((j: any, idx: number) => (
            <motion.div
              key={j.id}
              className="job-card"
              onClick={() => viewJob(j.id)}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: Math.min(idx * 0.02, 0.4), duration: 0.2 }}
            >
              <div className="job-icon"><Briefcase size={18} /></div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="job-title">{j.title}</div>
                {j.company && <div className="job-company"><Building size={11} style={{ display: 'inline', marginRight: 4 }} />{j.company}</div>}
                <div className="job-meta">
                  {j.location && <span><MapPin size={10} /> {j.location}</span>}
                  {j.salary_range && <span>💰 {j.salary_range}</span>}
                  <span>🌐 {j.source}</span>
                  <span className={`tag ${j.has_embedding ? 'tag-success' : 'tag-gray'}`} style={{ fontSize: '0.6rem' }}>
                    {j.has_embedding ? '🧠 AI Ready' : '⏳ Processing'}
                  </span>
                </div>
              </div>
              {/* Action buttons */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
                <button
                  className="btn btn-primary btn-sm"
                  onClick={e => openApply(e, j)}
                  title="Apply with AI tools"
                  style={{ fontSize: '0.72rem', gap: 5 }}
                >
                  <Zap size={12} /> Apply
                </button>
                <button
                  onClick={e => handleSaveJob(j.id, e)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: user?.saved_jobs?.includes(j.id) ? 'var(--accent)' : 'var(--text-3)', padding: 4 }}
                >
                  {user?.saved_jobs?.includes(j.id) ? <BookmarkCheck size={16} /> : <Bookmark size={16} />}
                </button>
                <ChevronRight size={16} style={{ color: 'var(--text-3)' }} />
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Job Detail Side Panel */}
      <AnimatePresence>
        {selected && (
          <>
            <motion.div className="detail-panel-backdrop" onClick={() => setSelected(null)} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
            <motion.div className="detail-panel" initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }} transition={{ type: 'spring', stiffness: 300, damping: 30 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
                <div>
                  <h3 style={{ fontWeight: 800, fontSize: '1.1rem', marginBottom: 4 }}>{selected.title}</h3>
                  {selected.company && <div style={{ color: 'var(--accent)', fontWeight: 600, fontSize: '0.88rem' }}>{selected.company}</div>}
                </div>
                <button className="btn btn-ghost btn-sm" onClick={() => setSelected(null)}>✕</button>
              </div>

              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
                {selected.location && <span className="tag tag-gray"><MapPin size={10} /> {selected.location}</span>}
                {selected.salary_range && <span className="tag tag-success">💰 {selected.salary_range}</span>}
                <span className="tag tag-gray">🌐 {selected.source}</span>
              </div>

              <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
                <button className="btn btn-primary btn-sm" onClick={e => { setSelected(null); openApply(e, selected); }}>
                  <Zap size={13} /> Apply with AI
                </button>
                {selected.url && (
                  <a href={selected.url} target="_blank" rel="noopener noreferrer" className="btn btn-ghost btn-sm">
                    <ExternalLink size={13} /> View Post
                  </a>
                )}
              </div>

              {selected.extracted && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: '0.62rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--accent)', marginBottom: 10, fontFamily: 'var(--mono)' }}>🧠 AI-Extracted Requirements</div>
                  {selected.extracted.required_skills?.length > 0 && (
                    <div style={{ marginBottom: 10 }}>
                      <div style={{ fontSize: '0.62rem', color: 'var(--text-3)', marginBottom: 6, fontFamily: 'var(--mono)', textTransform: 'uppercase' }}>Required Skills</div>
                      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        {selected.extracted.required_skills.map((s: string, i: number) => <span key={i} className="tag">{s}</span>)}
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div style={{ fontSize: '0.62rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-3)', marginBottom: 8, fontFamily: 'var(--mono)' }}>Description</div>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-2)', lineHeight: 1.75, whiteSpace: 'pre-wrap', maxHeight: 360, overflowY: 'auto', padding: 14, borderRadius: 'var(--r)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)' }}>
                {selected.description || 'No description available'}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Apply Modal */}
      <AnimatePresence>
        {applyJob && (
          <JobApplyModal job={applyJob} onClose={() => setApplyJob(null)} />
        )}
      </AnimatePresence>

      {toast && (
        <motion.div className={`toast ${toast.type}`} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
          {toast.msg}
        </motion.div>
      )}
    </div>
  );
}
