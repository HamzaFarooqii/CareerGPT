import { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import {
  X, FileText, Zap, Sparkles, Loader, Copy, CheckCheck,
  Download, ExternalLink, ChevronRight, User, PlusCircle, Trash2
} from 'lucide-react';
import { generateCoverLetter, generateATSResume, generateScreeningAnswers, listResumes, getResume } from '../api';
import { useEffect } from 'react';

interface Props {
  job: any;   // Full job object with title, company, description, url
  onClose: () => void;
}

type Tab = 'cover' | 'ats' | 'screening';

const TONE_OPTIONS = [
  { value: 'professional', label: '👔 Professional' },
  { value: 'enthusiastic', label: '🔥 Enthusiastic' },
  { value: 'concise',      label: '⚡ Concise' },
];

function CopyBtn({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button className="btn btn-ghost btn-sm" onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000); }}>
      {copied ? <><CheckCheck size={13} /> Copied!</> : <><Copy size={13} /> Copy</>}
    </button>
  );
}

function ResultBox({ content, title, onDownload }: { content: string; title: string; onDownload?: () => void }) {
  return (
    <div style={{ marginTop: 16, background: 'var(--bg-3)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', overflow: 'hidden' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', borderBottom: '1px solid var(--border)' }}>
        <span style={{ fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--accent)', fontFamily: 'var(--mono)' }}>
          🤖 {title}
        </span>
        <div style={{ display: 'flex', gap: 8 }}>
          <CopyBtn text={content} />
          {onDownload && (
            <button className="btn btn-ghost btn-sm" onClick={onDownload}>
              <Download size={13} /> PDF
            </button>
          )}
        </div>
      </div>
      <div style={{ padding: '16px', fontSize: '0.82rem', color: 'var(--text-2)', lineHeight: 1.8, maxHeight: 360, overflowY: 'auto' }}>
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    </div>
  );
}

export default function JobApplyModal({ job, onClose }: Props) {
  const [tab, setTab] = useState<Tab>('cover');
  const [resumes, setResumes] = useState<any[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState('');
  const printRef = useRef<HTMLDivElement>(null);

  // Cover Letter
  const [tone, setTone] = useState('professional');
  const [coverResult, setCoverResult] = useState('');
  const [coverLoading, setCoverLoading] = useState(false);

  // ATS Resume
  const [atsFields, setAtsFields] = useState({
    name: '', email: '', phone: '', linkedin: '',
    summary: '', experience: '', education: '', skills: '',
  });
  const [atsResult, setAtsResult] = useState('');
  const [atsLoading, setAtsLoading] = useState(false);
  const [useExistingResume, setUseExistingResume] = useState(true);

  // Screening
  const [questions, setQuestions] = useState(['Why do you want to work here?', 'What are your salary expectations?']);
  const [screenResult, setScreenResult] = useState('');
  const [screenLoading, setScreenLoading] = useState(false);

  useEffect(() => {
    listResumes().then(r => {
      setResumes(r);
      if (r.length > 0) setSelectedResumeId(r[0].id);
    }).catch(() => {});
  }, []);

  const getResumeText = async () => {
    if (!selectedResumeId) return '';
    try { const r = await getResume(selectedResumeId); return r.raw_text || ''; }
    catch { return ''; }
  };

  const buildManualResumeText = () =>
    `Name: ${atsFields.name}\nEmail: ${atsFields.email}\nPhone: ${atsFields.phone}\nLinkedIn: ${atsFields.linkedin}\n\nSummary:\n${atsFields.summary}\n\nExperience:\n${atsFields.experience}\n\nEducation:\n${atsFields.education}\n\nSkills:\n${atsFields.skills}`;

  const handleCoverLetter = async () => {
    setCoverLoading(true);
    try {
      const resumeText = await getResumeText();
      const res = await generateCoverLetter({
        resume_text: resumeText,
        job_title: job.title || '',
        company: job.company || '',
        job_description: job.description || '',
        tone,
      });
      setCoverResult(res.cover_letter);
    } catch (e: any) { setCoverResult(`❌ Error: ${e.message}`); }
    setCoverLoading(false);
  };

  const handleATSResume = async () => {
    setAtsLoading(true);
    try {
      const resumeText = useExistingResume ? await getResumeText() : buildManualResumeText();
      const res = await generateATSResume({
        resume_text: resumeText,
        job_title: job.title || '',
        job_description: job.description || '',
      });
      setAtsResult(res.optimized_resume);
    } catch (e: any) { setAtsResult(`❌ Error: ${e.message}`); }
    setAtsLoading(false);
  };

  const handleScreening = async () => {
    setScreenLoading(true);
    try {
      const resumeText = await getResumeText();
      const res = await generateScreeningAnswers({
        questions: questions.filter(q => q.trim()),
        resume_text: resumeText,
        job_title: job.title || '',
        company: job.company || '',
      });
      setScreenResult(res.answers);
    } catch (e: any) { setScreenResult(`❌ Error: ${e.message}`); }
    setScreenLoading(false);
  };

  // PDF download using browser print
  const downloadPDF = (content: string, filename: string) => {
    const win = window.open('', '_blank');
    if (!win) return;
    win.document.write(`
      <!DOCTYPE html><html><head>
      <title>${filename}</title>
      <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; max-width: 800px; margin: 40px auto; color: #1a1a2e; line-height: 1.6; font-size: 14px; }
        h1,h2,h3 { color: #1a1a2e; margin-top: 20px; }
        h1 { font-size: 22px; border-bottom: 2px solid #6366f1; padding-bottom: 8px; }
        h2 { font-size: 16px; color: #6366f1; }
        ul { padding-left: 20px; } li { margin-bottom: 4px; }
        strong { color: #1a1a2e; }
        p { margin: 8px 0; }
        @media print { body { margin: 20px; } }
      </style>
      </head><body>${content.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/^# (.*)/gm, '<h1>$1</h1>').replace(/^## (.*)/gm, '<h2>$1</h2>').replace(/^### (.*)/gm, '<h3>$1</h3>').replace(/^- (.*)/gm, '<li>$1</li>')}</body></html>
    `);
    win.document.close();
    setTimeout(() => { win.print(); }, 500);
  };

  const TABS: { id: Tab; label: string; icon: any }[] = [
    { id: 'cover',     label: 'Cover Letter', icon: FileText },
    { id: 'ats',       label: 'ATS Resume',   icon: Zap },
    { id: 'screening', label: 'Screening Q&A', icon: Sparkles },
  ];

  return (
    <>
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        onClick={onClose}
        style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)', zIndex: 1000 }}
      />

      {/* Modal */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        transition={{ type: 'spring', stiffness: 380, damping: 30 }}
        style={{
          position: 'fixed', top: '50%', left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '90vw', maxWidth: 760, maxHeight: '88vh',
          background: 'var(--bg-2)', border: '1px solid var(--border)',
          borderRadius: 'var(--r-xl)', zIndex: 1001,
          display: 'flex', flexDirection: 'column',
          boxShadow: '0 32px 80px rgba(0,0,0,0.6)',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div style={{ padding: '20px 24px 16px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div style={{ fontSize: '0.62rem', color: 'var(--accent)', fontFamily: 'var(--mono)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 6 }}>
                ⚡ AI Apply Toolkit
              </div>
              <h3 style={{ fontWeight: 800, fontSize: '1.05rem', marginBottom: 2 }}>{job.title}</h3>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-2)' }}>
                {job.company && <span>{job.company}</span>}
                {job.location && <span style={{ color: 'var(--text-3)' }}> · {job.location}</span>}
                {job.url && (
                  <a href={job.url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent)', marginLeft: 10, fontSize: '0.75rem', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                    <ExternalLink size={11} /> View Job
                  </a>
                )}
              </div>
            </div>
            <button className="btn btn-ghost btn-sm" onClick={onClose} style={{ flexShrink: 0 }}>
              <X size={16} />
            </button>
          </div>

          {/* Tabs */}
          <div style={{ display: 'flex', gap: 4, marginTop: 16, background: 'var(--surface)', borderRadius: 10, padding: 4, width: 'fit-content' }}>
            {TABS.map(t => (
              <button key={t.id} onClick={() => setTab(t.id)} style={{
                display: 'flex', alignItems: 'center', gap: 7, padding: '7px 14px',
                borderRadius: 7, border: 'none', cursor: 'pointer',
                fontSize: '0.78rem', fontWeight: 600, fontFamily: 'var(--font)',
                background: tab === t.id ? 'var(--accent)' : 'transparent',
                color: tab === t.id ? '#fff' : 'var(--text-3)', transition: 'all 0.15s',
              }}>
                <t.icon size={13} /> {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Scrollable body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px 24px' }}>

          {/* Resume selector (shared across tabs) */}
          <div style={{ marginBottom: 16, padding: '12px 16px', background: 'rgba(99,102,241,0.06)', border: '1px solid var(--accent-border)', borderRadius: 'var(--r)', display: 'flex', alignItems: 'center', gap: 12 }}>
            <User size={14} style={{ color: 'var(--accent)', flexShrink: 0 }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '0.62rem', color: 'var(--text-3)', fontFamily: 'var(--mono)', fontWeight: 700, textTransform: 'uppercase', marginBottom: 5 }}>Your Resume</div>
              <select className="input" value={selectedResumeId} onChange={e => setSelectedResumeId(e.target.value)}
                style={{ padding: '6px 10px', fontSize: '0.82rem', height: 'auto' }}>
                <option value="">— No resume (AI generates from scratch) —</option>
                {resumes.map((r: any) => <option key={r.id} value={r.id}>{r.title || 'Untitled Resume'}</option>)}
              </select>
            </div>
          </div>

          {/* ── Cover Letter Tab ── */}
          {tab === 'cover' && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
              <div style={{ marginBottom: 14 }}>
                <div style={{ fontSize: '0.62rem', color: 'var(--text-3)', fontFamily: 'var(--mono)', fontWeight: 700, textTransform: 'uppercase', marginBottom: 8 }}>Tone</div>
                <div style={{ display: 'flex', gap: 8 }}>
                  {TONE_OPTIONS.map(t => (
                    <button key={t.value} onClick={() => setTone(t.value)}
                      style={{ padding: '8px 14px', borderRadius: 8, border: `1px solid ${tone === t.value ? 'var(--accent)' : 'var(--border)'}`, background: tone === t.value ? 'rgba(99,102,241,0.1)' : 'transparent', color: tone === t.value ? 'var(--accent)' : 'var(--text-2)', cursor: 'pointer', fontSize: '0.78rem', fontFamily: 'var(--font)' }}>
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>
              <button className="btn btn-primary" onClick={handleCoverLetter} disabled={coverLoading} style={{ width: '100%' }}>
                {coverLoading ? <><Loader size={14} style={{ animation: 'spin 0.8s linear infinite' }} /> Generating Cover Letter...</> : <><FileText size={14} /> Generate Cover Letter</>}
              </button>
              {coverResult && (
                <ResultBox
                  content={coverResult}
                  title="Generated Cover Letter"
                  onDownload={() => downloadPDF(coverResult, `Cover_Letter_${job.company || 'Company'}.pdf`)}
                />
              )}
            </motion.div>
          )}

          {/* ── ATS Resume Tab ── */}
          {tab === 'ats' && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
              <div style={{ padding: '10px 14px', borderRadius: 'var(--r)', background: 'rgba(99,102,241,0.06)', border: '1px solid var(--accent-border)', marginBottom: 16, fontSize: '0.8rem', color: 'var(--text-2)', lineHeight: 1.6 }}>
                <strong style={{ color: 'var(--accent)' }}>🤖 ATS-Optimized Resume</strong> — AI rewrites your CV to perfectly match this job's keywords. Download as a professional PDF.
              </div>

              {/* Toggle: use uploaded vs manual */}
              <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
                <button onClick={() => setUseExistingResume(true)}
                  style={{ padding: '8px 14px', borderRadius: 8, border: `1px solid ${useExistingResume ? 'var(--accent)' : 'var(--border)'}`, background: useExistingResume ? 'rgba(99,102,241,0.1)' : 'transparent', color: useExistingResume ? 'var(--accent)' : 'var(--text-2)', cursor: 'pointer', fontSize: '0.78rem', fontFamily: 'var(--font)' }}>
                  📄 Use Uploaded CV
                </button>
                <button onClick={() => setUseExistingResume(false)}
                  style={{ padding: '8px 14px', borderRadius: 8, border: `1px solid ${!useExistingResume ? 'var(--accent)' : 'var(--border)'}`, background: !useExistingResume ? 'rgba(99,102,241,0.1)' : 'transparent', color: !useExistingResume ? 'var(--accent)' : 'var(--text-2)', cursor: 'pointer', fontSize: '0.78rem', fontFamily: 'var(--font)' }}>
                  ✏️ Enter Details Manually
                </button>
              </div>

              {/* Manual entry fields */}
              {!useExistingResume && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 14 }}>
                  <div className="grid-2" style={{ gap: 10 }}>
                    {[
                      { key: 'name', label: 'Full Name', placeholder: 'e.g. Muhammad Ali' },
                      { key: 'email', label: 'Email', placeholder: 'ali@example.com' },
                      { key: 'phone', label: 'Phone', placeholder: '+92 300 1234567' },
                      { key: 'linkedin', label: 'LinkedIn / GitHub', placeholder: 'linkedin.com/in/...' },
                    ].map(f => (
                      <div key={f.key}>
                        <label style={{ fontSize: '0.62rem', color: 'var(--text-3)', fontFamily: 'var(--mono)', fontWeight: 700, textTransform: 'uppercase', display: 'block', marginBottom: 5 }}>{f.label}</label>
                        <input className="input" value={(atsFields as any)[f.key]} onChange={e => setAtsFields(p => ({ ...p, [f.key]: e.target.value }))} placeholder={f.placeholder} />
                      </div>
                    ))}
                  </div>
                  {[
                    { key: 'summary', label: 'Professional Summary', placeholder: 'Brief summary of your background and goals...' },
                    { key: 'experience', label: 'Work Experience', placeholder: 'Company Name | Role | Date Range\n- Achievement 1\n- Achievement 2\n\nCompany 2 | Role | Date...' },
                    { key: 'education', label: 'Education', placeholder: 'University Name | Degree | Year\nGPA / Achievements...' },
                    { key: 'skills', label: 'Skills', placeholder: 'Python, React, Node.js, SQL, Docker, AWS...' },
                  ].map(f => (
                    <div key={f.key}>
                      <label style={{ fontSize: '0.62rem', color: 'var(--text-3)', fontFamily: 'var(--mono)', fontWeight: 700, textTransform: 'uppercase', display: 'block', marginBottom: 5 }}>{f.label}</label>
                      <textarea className="input" value={(atsFields as any)[f.key]} onChange={e => setAtsFields(p => ({ ...p, [f.key]: e.target.value }))} placeholder={f.placeholder} style={{ height: f.key === 'experience' ? 120 : 70, resize: 'vertical' }} />
                    </div>
                  ))}
                </div>
              )}

              <button className="btn btn-primary" onClick={handleATSResume} disabled={atsLoading} style={{ width: '100%' }}>
                {atsLoading ? <><Loader size={14} style={{ animation: 'spin 0.8s linear infinite' }} /> Optimizing Resume...</> : <><Zap size={14} /> Generate ATS-Optimized Resume</>}
              </button>

              {atsResult && (
                <ResultBox
                  content={atsResult}
                  title="ATS-Optimized Resume"
                  onDownload={() => downloadPDF(atsResult, `ATS_Resume_${job.title?.replace(/\s+/g, '_') || 'Resume'}.pdf`)}
                />
              )}
            </motion.div>
          )}

          {/* ── Screening Q&A Tab ── */}
          {tab === 'screening' && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
              <div style={{ marginBottom: 14 }}>
                <div style={{ fontSize: '0.62rem', color: 'var(--text-3)', fontFamily: 'var(--mono)', fontWeight: 700, textTransform: 'uppercase', marginBottom: 10 }}>Application Questions</div>
                {questions.map((q, i) => (
                  <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                    <input
                      className="input"
                      value={q}
                      onChange={e => setQuestions(prev => prev.map((pq, pi) => pi === i ? e.target.value : pq))}
                      placeholder={`Question ${i + 1}`}
                      style={{ flex: 1, fontSize: '0.82rem' }}
                    />
                    <button className="btn btn-ghost btn-sm" onClick={() => setQuestions(prev => prev.filter((_, pi) => pi !== i))}>
                      <Trash2 size={13} />
                    </button>
                  </div>
                ))}
                <button className="btn btn-ghost btn-sm" onClick={() => setQuestions(prev => [...prev, ''])} style={{ marginTop: 4 }}>
                  <PlusCircle size={13} /> Add Question
                </button>
              </div>

              <button className="btn btn-primary" onClick={handleScreening} disabled={screenLoading || questions.filter(q => q.trim()).length === 0} style={{ width: '100%' }}>
                {screenLoading ? <><Loader size={14} style={{ animation: 'spin 0.8s linear infinite' }} /> Generating Answers...</> : <><Sparkles size={14} /> Generate AI Answers</>}
              </button>

              {screenResult && (
                <ResultBox
                  content={screenResult}
                  title="AI-Generated Answers"
                  onDownload={() => downloadPDF(screenResult, `Screening_Answers_${job.company || 'Company'}.pdf`)}
                />
              )}
            </motion.div>
          )}
        </div>
      </motion.div>
    </>
  );
}
