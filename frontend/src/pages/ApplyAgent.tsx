import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { Zap, FileText, Copy, CheckCheck, Loader, PlusCircle, Trash2, Sparkles } from 'lucide-react';
import { generateCoverLetter, generateATSResume, generateScreeningAnswers, listResumes, getResume } from '../api';
import { useEffect } from 'react';

const TABS = [
  { id: 'cover', label: 'Cover Letter', icon: FileText },
  { id: 'resume', label: 'ATS Resume', icon: Zap },
  { id: 'screening', label: 'Screening Q&A', icon: Sparkles },
  { id: 'tracker', label: 'Applications', icon: CheckCheck },
];

const TONE_OPTIONS = [
  { value: 'professional', label: '👔 Professional' },
  { value: 'enthusiastic', label: '🔥 Enthusiastic' },
  { value: 'concise', label: '⚡ Concise' },
];

const APP_STATUSES = ['Applied', 'Interview', 'Offer', 'Rejected'];
const STATUS_COLORS: Record<string, string> = {
  Applied: 'var(--accent)',
  Interview: 'var(--warning)',
  Offer: 'var(--success)',
  Rejected: 'var(--error)',
};

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button className="btn btn-ghost btn-sm" onClick={copy}>
      {copied ? <><CheckCheck size={13} /> Copied!</> : <><Copy size={13} /> Copy</>}
    </button>
  );
}

function ResultBox({ content, title }: { content: string; title: string }) {
  return (
    <div className="card" style={{ marginTop: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div style={{ fontSize: '0.62rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--accent)', fontFamily: 'var(--mono)' }}>
          🤖 {title}
        </div>
        <CopyButton text={content} />
      </div>
      <div style={{ fontSize: '0.84rem', color: 'var(--text-2)', lineHeight: 1.8, maxHeight: 500, overflowY: 'auto' }}>
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    </div>
  );
}

export default function ApplyAgent() {
  const [tab, setTab] = useState('cover');
  const [resumes, setResumes] = useState<any[]>([]);

  // Cover letter state
  const [coverResume, setCoverResume] = useState('');
  const [jobTitle, setJobTitle] = useState('');
  const [company, setCompany] = useState('');
  const [jobDesc, setJobDesc] = useState('');
  const [tone, setTone] = useState('professional');
  const [coverResult, setCoverResult] = useState('');
  const [coverLoading, setCoverLoading] = useState(false);

  // ATS resume state
  const [atsResume, setAtsResume] = useState('');
  const [atsJobTitle, setAtsJobTitle] = useState('');
  const [atsJobDesc, setAtsJobDesc] = useState('');
  const [atsResult, setAtsResult] = useState('');
  const [atsLoading, setAtsLoading] = useState(false);

  // Screening state
  const [screenResume, setScreenResume] = useState('');
  const [screenJobTitle, setScreenJobTitle] = useState('');
  const [screenCompany, setScreenCompany] = useState('');
  const [questions, setQuestions] = useState<string[]>(['Why do you want to work here?', 'What are your salary expectations?']);
  const [screenResult, setScreenResult] = useState('');
  const [screenLoading, setScreenLoading] = useState(false);

  // Application tracker (local state, could be synced with API)
  const [applications, setApplications] = useState<any[]>([]);

  useEffect(() => { listResumes().then(setResumes).catch(() => {}); }, []);

  const getResumeText = async (id: string) => {
    if (!id) return '';
    try { const r = await getResume(id); return r.raw_text || ''; }
    catch { return ''; }
  };

  const handleCoverLetter = async () => {
    setCoverLoading(true);
    try {
      const resumeText = await getResumeText(coverResume);
      const result = await generateCoverLetter({ resume_text: resumeText, job_title: jobTitle, company, job_description: jobDesc, tone });
      setCoverResult(result.cover_letter);
    } catch (e: any) { setCoverResult(`Error: ${e.message}`); }
    setCoverLoading(false);
  };

  const handleATSResume = async () => {
    setAtsLoading(true);
    try {
      const resumeText = await getResumeText(atsResume);
      const result = await generateATSResume({ resume_text: resumeText, job_title: atsJobTitle, job_description: atsJobDesc });
      setAtsResult(result.optimized_resume);
    } catch (e: any) { setAtsResult(`Error: ${e.message}`); }
    setAtsLoading(false);
  };

  const handleScreening = async () => {
    setScreenLoading(true);
    try {
      const resumeText = await getResumeText(screenResume);
      const filtered = questions.filter(q => q.trim());
      const result = await generateScreeningAnswers({ questions: filtered, resume_text: resumeText, job_title: screenJobTitle, company: screenCompany });
      setScreenResult(result.answers);
    } catch (e: any) { setScreenResult(`Error: ${e.message}`); }
    setScreenLoading(false);
  };

  // Kanban columns
  const cols = APP_STATUSES.map(status => ({
    status,
    apps: applications.filter(a => a.status === status),
  }));

  return (
    <div className="animate-fadein">
      <div className="page-header">
        <div className="breadcrumb">✦ CareerGPT · Apply Agent</div>
        <h2>Apply <span>Agent</span></h2>
        <p>AI-powered application tools — cover letters, ATS resumes, screening answers</p>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 24, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: 4, width: 'fit-content', flexWrap: 'wrap' }}>
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)} style={{
            display: 'flex', alignItems: 'center', gap: 8, padding: '8px 16px', borderRadius: 8, border: 'none', cursor: 'pointer', fontSize: '0.8rem', fontWeight: 600, fontFamily: 'var(--font)', transition: 'all 0.15s',
            background: tab === t.id ? 'var(--accent)' : 'transparent',
            color: tab === t.id ? '#fff' : 'var(--text-3)',
          }}>
            <t.icon size={14} /> {t.label}
          </button>
        ))}
      </div>

      {/* Cover Letter */}
      {tab === 'cover' && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <div className="grid-2" style={{ marginBottom: 16 }}>
            <div className="input-group">
              <label>Resume</label>
              <select className="input" value={coverResume} onChange={e => setCoverResume(e.target.value)}>
                <option value="">-- No resume (manual input) --</option>
                {resumes.map((r: any) => <option key={r.id} value={r.id}>{r.title || 'Untitled'}</option>)}
              </select>
            </div>
            <div className="input-group">
              <label>Tone</label>
              <select className="input" value={tone} onChange={e => setTone(e.target.value)}>
                {TONE_OPTIONS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div className="input-group">
              <label>Job Title *</label>
              <input className="input" value={jobTitle} onChange={e => setJobTitle(e.target.value)} placeholder="e.g. Senior Software Engineer" />
            </div>
            <div className="input-group">
              <label>Company *</label>
              <input className="input" value={company} onChange={e => setCompany(e.target.value)} placeholder="e.g. Google, Meta, Startup Inc." />
            </div>
          </div>
          <div className="input-group" style={{ marginBottom: 16 }}>
            <label>Job Description</label>
            <textarea className="input" value={jobDesc} onChange={e => setJobDesc(e.target.value)} placeholder="Paste the job description here for a personalized letter..." style={{ height: 120, resize: 'vertical' }} />
          </div>
          <button className="btn btn-primary" onClick={handleCoverLetter} disabled={coverLoading || !jobTitle || !company}>
            {coverLoading ? <><Loader size={14} style={{ animation: 'spin 0.8s linear infinite' }} /> Generating...</> : <><FileText size={14} /> Generate Cover Letter</>}
          </button>
          {coverResult && <ResultBox content={coverResult} title="Generated Cover Letter" />}
        </motion.div>
      )}

      {/* ATS Resume */}
      {tab === 'resume' && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <div className="insight-card" style={{ marginBottom: 20 }}>
            <div className="insight-label"><Zap size={13} /> ATS Optimization</div>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-2)', lineHeight: 1.6 }}>
              Our AI rewrites your resume to perfectly match the job description — mirroring keywords, restructuring bullet points, and quantifying achievements to maximize your ATS score.
            </p>
          </div>
          <div className="grid-2" style={{ marginBottom: 16 }}>
            <div className="input-group">
              <label>Select Resume *</label>
              <select className="input" value={atsResume} onChange={e => setAtsResume(e.target.value)}>
                <option value="">-- Select a resume --</option>
                {resumes.map((r: any) => <option key={r.id} value={r.id}>{r.title || 'Untitled'}</option>)}
              </select>
            </div>
            <div className="input-group">
              <label>Target Job Title *</label>
              <input className="input" value={atsJobTitle} onChange={e => setAtsJobTitle(e.target.value)} placeholder="e.g. Machine Learning Engineer" />
            </div>
          </div>
          <div className="input-group" style={{ marginBottom: 16 }}>
            <label>Job Description *</label>
            <textarea className="input" value={atsJobDesc} onChange={e => setAtsJobDesc(e.target.value)} placeholder="Paste the complete job description..." style={{ height: 140, resize: 'vertical' }} />
          </div>
          <button className="btn btn-primary" onClick={handleATSResume} disabled={atsLoading || !atsResume || !atsJobTitle || !atsJobDesc}>
            {atsLoading ? <><Loader size={14} style={{ animation: 'spin 0.8s linear infinite' }} /> Optimizing...</> : <><Zap size={14} /> Generate ATS-Optimized Resume</>}
          </button>
          {atsResult && <ResultBox content={atsResult} title="ATS-Optimized Resume" />}
        </motion.div>
      )}

      {/* Screening Q&A */}
      {tab === 'screening' && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <div className="grid-2" style={{ marginBottom: 16 }}>
            <div className="input-group">
              <label>Resume</label>
              <select className="input" value={screenResume} onChange={e => setScreenResume(e.target.value)}>
                <option value="">-- No resume --</option>
                {resumes.map((r: any) => <option key={r.id} value={r.id}>{r.title || 'Untitled'}</option>)}
              </select>
            </div>
            <div className="input-group">
              <label>Job Title *</label>
              <input className="input" value={screenJobTitle} onChange={e => setScreenJobTitle(e.target.value)} placeholder="e.g. Product Manager" />
            </div>
            <div className="input-group">
              <label>Company</label>
              <input className="input" value={screenCompany} onChange={e => setScreenCompany(e.target.value)} placeholder="e.g. Tesla" />
            </div>
          </div>
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: '0.62rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-3)', fontFamily: 'var(--mono)', marginBottom: 10 }}>Screening Questions</div>
            {questions.map((q, i) => (
              <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                <input className="input" value={q} onChange={e => setQuestions(prev => prev.map((pq, pi) => pi === i ? e.target.value : pq))} placeholder={`Question ${i + 1}`} style={{ flex: 1 }} />
                <button className="btn btn-ghost btn-sm" onClick={() => setQuestions(prev => prev.filter((_, pi) => pi !== i))}><Trash2 size={13} /></button>
              </div>
            ))}
            <button className="btn btn-ghost btn-sm" onClick={() => setQuestions(prev => [...prev, ''])} style={{ marginTop: 4 }}>
              <PlusCircle size={13} /> Add Question
            </button>
          </div>
          <button className="btn btn-primary" onClick={handleScreening} disabled={screenLoading || !screenJobTitle || questions.filter(q => q.trim()).length === 0}>
            {screenLoading ? <><Loader size={14} style={{ animation: 'spin 0.8s linear infinite' }} /> Generating...</> : <><Sparkles size={14} /> Generate Answers</>}
          </button>
          {screenResult && <ResultBox content={screenResult} title="AI-Generated Screening Answers" />}
        </motion.div>
      )}

      {/* Application Tracker */}
      {tab === 'tracker' && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <div className="insight-card" style={{ marginBottom: 20 }}>
            <div className="insight-label"><CheckCheck size={13} /> Application Tracker</div>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-2)', lineHeight: 1.6 }}>
              Track applications from the <strong style={{ color: 'var(--text)' }}>Job Search</strong> page using "Track Application" button on any job. Your applications will appear here organized by status.
            </p>
          </div>
          <div className="kanban-board">
            {cols.map(col => (
              <div key={col.status} className="kanban-col">
                <div className="kanban-col-header">
                  <span className="dot" style={{ background: STATUS_COLORS[col.status], boxShadow: `0 0 6px ${STATUS_COLORS[col.status]}` }} />
                  {col.status}
                  <span style={{ marginLeft: 'auto', fontSize: '0.65rem', color: 'var(--text-3)', fontFamily: 'var(--mono)' }}>{col.apps.length}</span>
                </div>
                {col.apps.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '20px 10px', color: 'var(--text-3)', fontSize: '0.72rem' }}>No applications</div>
                ) : (
                  col.apps.map((app: any, i: number) => (
                    <div key={i} className="kanban-card">
                      <div style={{ fontWeight: 700, fontSize: '0.8rem', marginBottom: 4 }}>{app.job_title || 'Unknown Role'}</div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-3)' }}>{app.company}</div>
                      <div style={{ fontSize: '0.65rem', color: 'var(--text-3)', marginTop: 6, fontFamily: 'var(--mono)' }}>{app.applied_at?.slice(0, 10)}</div>
                    </div>
                  ))
                )}
              </div>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
}
