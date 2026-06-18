import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Target, Copy, Check, ExternalLink, ChevronDown, ChevronUp, Loader, MapPin, Star, AlertTriangle, ThumbsUp } from 'lucide-react';
import { listResumes } from '../api';

const API = '/api';

async function runMatching(resumeId: string, topK = 15, coverLetters = false) {
  const params = new URLSearchParams({
    resume_id: resumeId,
    top_k: String(topK),
    generate_cover_letters: String(coverLetters),
  });
  const res = await fetch(`${API}/matches/run?${params}`, { method: 'POST' });
  if (!res.ok) throw new Error((await res.json()).detail || 'Matching failed');
  return res.json();
}

async function getMatchesForResume(resumeId: string) {
  const res = await fetch(`${API}/matches/resume/${resumeId}`);
  return res.json();
}

function ScoreBadge({ score }: { score: number }) {
  const color = score >= 7 ? 'var(--success)' : score >= 5 ? 'var(--warning)' : 'var(--error)';
  return (
    <div style={{ width: 48, height: 48, borderRadius: 10, border: `2px solid ${color}`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
      <span style={{ fontWeight: 800, fontSize: '1rem', color }}>{score.toFixed(1)}</span>
    </div>
  );
}

function SkillTag({ skill, type }: { skill: string; type: 'match' | 'missing' }) {
  const bg = type === 'match' ? 'rgba(52,211,153,0.08)' : 'rgba(248,113,113,0.08)';
  const border = type === 'match' ? 'rgba(52,211,153,0.2)' : 'rgba(248,113,113,0.2)';
  const color = type === 'match' ? 'var(--success)' : 'var(--error)';
  return (
    <span style={{ padding: '2px 8px', borderRadius: 4, fontSize: '0.66rem', fontWeight: 600, fontFamily: 'var(--font-mono)', background: bg, border: `1px solid ${border}`, color }}>{skill}</span>
  );
}

export default function Matches() {
  const [resumes, setResumes] = useState<any[]>([]);
  const [selectedResume, setSelectedResume] = useState('');
  const [matches, setMatches] = useState<any[]>([]);
  const [running, setRunning] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [toast, setToast] = useState<{ msg: string; type: string } | null>(null);

  useEffect(() => { listResumes().then(setResumes).catch(() => {}); }, []);

  const showToast = (msg: string, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 4000);
  };

  const handleRun = async () => {
    if (!selectedResume) { showToast('Select a resume first', 'error'); return; }
    setRunning(true);
    setMatches([]);
    try {
      const results = await runMatching(selectedResume);
      setMatches(results);
      showToast(`✅ ${results.length} matches found and analyzed!`);
    } catch (e: any) {
      showToast(e.message || 'Matching failed', 'error');
    }
    setRunning(false);
  };

  const loadExisting = async (resumeId: string) => {
    try {
      const results = await getMatchesForResume(resumeId);
      if (results.length > 0) setMatches(results);
    } catch {}
  };

  const handleResumeChange = (id: string) => {
    setSelectedResume(id);
    setMatches([]);
    if (id) loadExisting(id);
  };

  const copyLetter = (text: string, matchId: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(matchId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="animate-fadein">
      <div className="page-header">
        <div className="breadcrumb">✦ CareerGPT · AI Matches</div>
        <h2>AI <span>Matches</span></h2>
        <p>Vector search + LLM analysis — find your perfect job fit</p>
      </div>

      {/* Control Panel */}
      <div className="card" style={{ marginBottom: 28, padding: 22 }}>
        <div style={{ fontSize: '0.65rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-muted)', marginBottom: 12, fontFamily: 'var(--font-mono)' }}>
          Select Resume & Run Matching
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
          <div className="input-group" style={{ flex: 1 }}>
            <label>Resume</label>
            <select className="input" value={selectedResume} onChange={e => handleResumeChange(e.target.value)} style={{ cursor: 'pointer' }}>
              <option value="">— Select a resume —</option>
              {resumes.map((r: any) => (
                <option key={r.id} value={r.id}>{r.title} ({r.word_count} words)</option>
              ))}
            </select>
          </div>
          <button className="btn btn-primary" onClick={handleRun} disabled={running || !selectedResume} style={{ height: 42 }}>
            {running ? <><Loader size={14} style={{ animation: 'spin 0.6s linear infinite' }} /> Analyzing...</> : <><Target size={14} /> Find Matches</>}
          </button>
        </div>
        {running && (
          <div style={{ marginTop: 14, padding: '12px 16px', borderRadius: 8, background: 'rgba(109,159,255,0.06)', border: '1px solid var(--accent-border)', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
            ⏳ Analyzing jobs against your resume... This takes 30-90 seconds (LLM is scoring each match).
          </div>
        )}
      </div>

      {/* Results */}
      {matches.length === 0 && !running ? (
        <div className="empty-state">
          <Target size={48} />
          <h3>No matches yet</h3>
          <p>Select a resume above and click "Find Matches" to start AI analysis</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {matches.map((m: any, idx: number) => {
            const isExpanded = expandedId === m.id;
            const score = m.analysis?.overall_score ?? 0;
            const rec = (m.analysis?.recommendation || '').toUpperCase();
            const isApply = rec.includes('APPLY');
            const isSkip = rec.includes('SKIP');

            return (
          <motion.div key={m.id} className="card" style={{ padding: 0, overflow: 'hidden' }}
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.06 }}>
                {/* Header row */}
                <div
                  style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '16px 20px', cursor: 'pointer' }}
                  onClick={() => setExpandedId(isExpanded ? null : m.id)}
                >
                  <div style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', fontWeight: 700, width: 24 }}>#{idx + 1}</div>
                  <ScoreBadge score={score} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 700, fontSize: '0.88rem', marginBottom: 2 }}>{m.job_title || 'Untitled'}</div>
                    {m.job_company && <div style={{ fontSize: '0.78rem', color: 'var(--accent)', fontWeight: 500 }}>{m.job_company}</div>}
                    <div className="job-meta" style={{ marginTop: 4 }}>
                      {m.job_location && <span><MapPin size={10} /> {m.job_location}</span>}
                      <span>🌐 {m.job_source}</span>
                      <span>📐 {(m.similarity_score * 100).toFixed(0)}% vector match</span>
                    </div>
                  </div>
                  <div style={{
                    padding: '4px 10px', borderRadius: 6, fontSize: '0.68rem', fontWeight: 700, fontFamily: 'var(--font-mono)',
                    background: isApply ? 'rgba(52,211,153,0.1)' : isSkip ? 'rgba(248,113,113,0.1)' : 'rgba(251,191,36,0.1)',
                    color: isApply ? 'var(--success)' : isSkip ? 'var(--error)' : 'var(--warning)',
                    border: `1px solid ${isApply ? 'rgba(52,211,153,0.2)' : isSkip ? 'rgba(248,113,113,0.2)' : 'rgba(251,191,36,0.2)'}`,
                  }}>
                    {rec || '—'}
                  </div>
                  {isExpanded ? <ChevronUp size={16} color="var(--text-muted)" /> : <ChevronDown size={16} color="var(--text-muted)" />}
                </div>

                {/* Expanded details */}
                {isExpanded && m.analysis && (
                  <div style={{ padding: '0 20px 20px', borderTop: '1px solid var(--border)' }}>
                    {/* Scores */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, margin: '16px 0' }}>
                      {[
                        { label: 'Skills', value: m.analysis.skill_match_score },
                        { label: 'Experience', value: m.analysis.experience_fit_score },
                        { label: 'Education', value: m.analysis.education_fit_score },
                        { label: 'Overall', value: m.analysis.overall_score },
                      ].map(s => (
                        <div key={s.label} style={{ textAlign: 'center', padding: '10px', borderRadius: 8, background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)' }}>
                          <div style={{ fontSize: '0.6rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>{s.label}</div>
                          <div style={{ fontSize: '1.1rem', fontWeight: 800, color: s.value >= 7 ? 'var(--success)' : s.value >= 5 ? 'var(--warning)' : 'var(--error)' }}>{s.value}/10</div>
                        </div>
                      ))}
                    </div>

                    {/* Reasoning */}
                    {m.analysis.reasoning && (
                      <div style={{ padding: '12px 16px', borderRadius: 8, background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)', fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.65, marginBottom: 14 }}>
                        {m.analysis.reasoning}
                      </div>
                    )}

                    {/* Skills */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
                      {m.analysis.matching_skills?.length > 0 && (
                        <div>
                          <div style={{ fontSize: '0.62rem', fontFamily: 'var(--font-mono)', color: 'var(--success)', fontWeight: 700, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 4 }}><ThumbsUp size={10} /> MATCHING SKILLS</div>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                            {m.analysis.matching_skills.map((s: string, i: number) => <SkillTag key={i} skill={s} type="match" />)}
                          </div>
                        </div>
                      )}
                      {m.analysis.missing_skills?.length > 0 && (
                        <div>
                          <div style={{ fontSize: '0.62rem', fontFamily: 'var(--font-mono)', color: 'var(--error)', fontWeight: 700, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 4 }}><AlertTriangle size={10} /> MISSING SKILLS</div>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                            {m.analysis.missing_skills.map((s: string, i: number) => <SkillTag key={i} skill={s} type="missing" />)}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Strong points & concerns */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
                      {m.analysis.strong_points?.length > 0 && (
                        <div style={{ padding: 12, borderRadius: 8, background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)' }}>
                          <div style={{ fontSize: '0.62rem', fontFamily: 'var(--font-mono)', color: 'var(--success)', fontWeight: 700, marginBottom: 6 }}>✓ STRONG POINTS</div>
                          {m.analysis.strong_points.map((p: string, i: number) => (
                            <div key={i} style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: 3 }}>• {p}</div>
                          ))}
                        </div>
                      )}
                      {m.analysis.concerns?.length > 0 && (
                        <div style={{ padding: 12, borderRadius: 8, background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)' }}>
                          <div style={{ fontSize: '0.62rem', fontFamily: 'var(--font-mono)', color: 'var(--warning)', fontWeight: 700, marginBottom: 6 }}>⚠ CONCERNS</div>
                          {m.analysis.concerns.map((c: string, i: number) => (
                            <div key={i} style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: 3 }}>• {c}</div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Cover letter */}
                    {m.cover_letter && (
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                          <div style={{ fontSize: '0.62rem', fontFamily: 'var(--font-mono)', color: 'var(--accent)', fontWeight: 700 }}>✉ GENERATED COVER LETTER</div>
                          <button className="btn btn-ghost" style={{ padding: '4px 10px', fontSize: '0.7rem' }} onClick={() => copyLetter(m.cover_letter, m.id)}>
                            {copiedId === m.id ? <><Check size={12} /> Copied!</> : <><Copy size={12} /> Copy</>}
                          </button>
                        </div>
                        <div style={{ padding: 16, borderRadius: 8, background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)', fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.75, whiteSpace: 'pre-wrap', maxHeight: 300, overflowY: 'auto' }}>
                          {m.cover_letter}
                        </div>
                      </div>
                    )}

                    {/* Job link */}
                    {m.job_url && (
                      <a href={m.job_url} target="_blank" rel="noopener noreferrer" className="btn btn-ghost" style={{ marginTop: 14, fontSize: '0.75rem' }}>
                        <ExternalLink size={13} /> View Original Job Post
                      </a>
                    )}
                </div>
                )}
              </motion.div>
            );
          })}
        </div>
      )}

      {toast && <div className={`toast ${toast.type}`}>{toast.msg}</div>}
    </div>
  );
}
