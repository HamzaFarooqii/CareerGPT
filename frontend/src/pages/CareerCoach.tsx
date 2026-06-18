import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { MessageSquare, Send, Loader, ChevronDown, FileText, Mic, Map, BarChart3, Sparkles } from 'lucide-react';
import { coachChat, reviewResume, interviewPrep, generateRoadmap } from '../api';
import { listResumes, getResume } from '../api';

type Message = { role: 'user' | 'ai'; content: string };

const STARTERS = [
  { label: '📄 Review my resume', msg: 'Can you give me detailed feedback on my resume and how to improve it?' },
  { label: '🎯 Interview tips', msg: 'What are the most common interview questions for a software engineer and how should I answer them?' },
  { label: '🗺️ Career roadmap', msg: 'I want to become a full-stack developer. Can you create a 6-month learning roadmap for me?' },
  { label: '💼 LinkedIn tips', msg: 'How can I optimize my LinkedIn profile to attract more recruiters?' },
  { label: '💰 Salary negotiation', msg: 'What are the best strategies for negotiating a higher salary at a tech company?' },
  { label: '🚀 Switch careers', msg: 'I am a marketing professional and want to switch to a product manager role. How should I approach this?' },
];

const TABS = [
  { id: 'chat', label: 'AI Chat', icon: MessageSquare },
  { id: 'review', label: 'Resume Review', icon: FileText },
  { id: 'interview', label: 'Interview Prep', icon: Mic },
  { id: 'roadmap', label: 'Roadmap', icon: Map },
];

export default function CareerCoach() {
  const [tab, setTab] = useState('chat');
  const [messages, setMessages] = useState<Message[]>([
    { role: 'ai', content: "Hello! I'm your **CareerGPT Career Coach** 🚀\n\nI can help you with:\n- **Resume reviews** and optimization\n- **Interview preparation** and practice\n- **Career roadmaps** tailored to your goals\n- **Salary negotiation** strategies\n- **LinkedIn** profile optimization\n\nWhat would you like to work on today?" },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Resume review state
  const [resumes, setResumes] = useState<any[]>([]);
  const [selectedResume, setSelectedResume] = useState('');
  const [targetRole, setTargetRole] = useState('');
  const [reviewResult, setReviewResult] = useState('');
  const [reviewLoading, setReviewLoading] = useState(false);

  // Interview prep state
  const [jobTitle, setJobTitle] = useState('');
  const [jobDesc, setJobDesc] = useState('');
  const [prepResult, setPrepResult] = useState('');
  const [prepLoading, setPrepLoading] = useState(false);

  // Roadmap state
  const [skills, setSkills] = useState('');
  const [roadTarget, setRoadTarget] = useState('');
  const [yearsExp, setYearsExp] = useState('0');
  const [roadmapResult, setRoadmapResult] = useState('');
  const [roadmapLoading, setRoadmapLoading] = useState(false);

  useEffect(() => { listResumes().then(setResumes).catch(() => {}); }, []);
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const sendMessage = async (text?: string) => {
    const msg = text || input.trim();
    if (!msg || loading) return;
    setInput('');
    const newMessages: Message[] = [...messages, { role: 'user', content: msg }];
    setMessages(newMessages);
    setLoading(true);
    try {
      const history = messages.map(m => ({ role: m.role, content: m.content }));
      const res = await coachChat(msg, history);
      setMessages([...newMessages, { role: 'ai', content: res.reply }]);
    } catch (e: any) {
      setMessages([...newMessages, { role: 'ai', content: `❌ Error: ${e.message}. Please try again.` }]);
    }
    setLoading(false);
  };

  const handleReviewResume = async () => {
    if (!selectedResume) return;
    setReviewLoading(true);
    try {
      const r = await getResume(selectedResume);
      const result = await reviewResume(r.raw_text || '', targetRole);
      setReviewResult(result.feedback);
    } catch (e: any) { setReviewResult(`Error: ${e.message}`); }
    setReviewLoading(false);
  };

  const handleInterviewPrep = async () => {
    if (!jobTitle) return;
    setPrepLoading(true);
    try {
      const result = await interviewPrep(jobTitle, jobDesc, '');
      setPrepResult(result.prep_guide);
    } catch (e: any) { setPrepResult(`Error: ${e.message}`); }
    setPrepLoading(false);
  };

  const handleRoadmap = async () => {
    if (!roadTarget) return;
    setRoadmapLoading(true);
    try {
      const skillList = skills.split(',').map(s => s.trim()).filter(Boolean);
      const result = await generateRoadmap(skillList, roadTarget, parseInt(yearsExp) || 0);
      setRoadmapResult(result.roadmap);
    } catch (e: any) { setRoadmapResult(`Error: ${e.message}`); }
    setRoadmapLoading(false);
  };

  return (
    <div className="animate-fadein">
      <div className="page-header">
        <div className="breadcrumb">✦ CareerGPT · Career Coach</div>
        <h2>Career <span>Coach</span></h2>
        <p>Your personal AI career advisor — available 24/7</p>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 24, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: 4, width: 'fit-content' }}>
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

      {/* Chat Tab */}
      {tab === 'chat' && (
        <div className="card" style={{ height: '65vh', display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden' }}>
          {/* Messages */}
          <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
            {messages.length === 1 && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 10, marginBottom: 24 }}>
                {STARTERS.map(s => (
                  <motion.button key={s.label} whileHover={{ scale: 1.02, y: -2 }} onClick={() => sendMessage(s.msg)}
                    style={{ padding: '12px 16px', background: 'var(--bg-3)', border: '1px solid var(--border)', borderRadius: 10, cursor: 'pointer', textAlign: 'left', fontSize: '0.8rem', color: 'var(--text-2)', fontFamily: 'var(--font)', transition: 'all 0.15s' }}>
                    {s.label}
                  </motion.button>
                ))}
              </div>
            )}
            <div className="chat-messages">
              {messages.map((m, i) => (
                <motion.div key={i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}
                  className={`chat-bubble ${m.role}`}>
                  {m.role === 'ai' ? (
                    <ReactMarkdown>{m.content}</ReactMarkdown>
                  ) : m.content}
                </motion.div>
              ))}
              {loading && (
                <div className="chat-bubble ai" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Loader size={14} style={{ animation: 'spin 0.8s linear infinite', color: 'var(--accent)' }} />
                  <span style={{ fontSize: '0.78rem' }}>CareerGPT is thinking...</span>
                </div>
              )}
            </div>
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div style={{ padding: '16px 24px', borderTop: '1px solid var(--border)', display: 'flex', gap: 10 }}>
            <input
              className="input"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage()}
              placeholder="Ask your career coach anything..."
              disabled={loading}
              style={{ flex: 1 }}
            />
            <button className="btn btn-primary" onClick={() => sendMessage()} disabled={loading || !input.trim()} style={{ padding: '10px 16px' }}>
              <Send size={15} />
            </button>
          </div>
        </div>
      )}

      {/* Resume Review Tab */}
      {tab === 'review' && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <div className="grid-2" style={{ marginBottom: 16 }}>
            <div className="input-group">
              <label>Select Resume</label>
              <select className="input" value={selectedResume} onChange={e => setSelectedResume(e.target.value)}>
                <option value="">-- Select a resume --</option>
                {resumes.map((r: any) => <option key={r.id} value={r.id}>{r.title || 'Untitled Resume'}</option>)}
              </select>
            </div>
            <div className="input-group">
              <label>Target Role (optional)</label>
              <input className="input" value={targetRole} onChange={e => setTargetRole(e.target.value)} placeholder="e.g. Senior Software Engineer" />
            </div>
          </div>
          <button className="btn btn-primary" onClick={handleReviewResume} disabled={reviewLoading || !selectedResume} style={{ marginBottom: 24 }}>
            {reviewLoading ? <><Loader size={14} style={{ animation: 'spin 0.8s linear infinite' }} /> Analyzing...</> : <><Sparkles size={14} /> Review Resume</>}
          </button>
          {reviewResult && (
            <div className="card">
              <div style={{ fontSize: '0.62rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--accent)', marginBottom: 16, fontFamily: 'var(--mono)' }}>🧠 AI Review</div>
              <div style={{ fontSize: '0.84rem', color: 'var(--text-2)', lineHeight: 1.75 }}>
                <ReactMarkdown>{reviewResult}</ReactMarkdown>
              </div>
            </div>
          )}
        </motion.div>
      )}

      {/* Interview Prep Tab */}
      {tab === 'interview' && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <div className="grid-2" style={{ marginBottom: 16 }}>
            <div className="input-group">
              <label>Job Title *</label>
              <input className="input" value={jobTitle} onChange={e => setJobTitle(e.target.value)} placeholder="e.g. Senior React Developer" />
            </div>
            <div className="input-group">
              <label>Job Description (optional)</label>
              <textarea className="input" value={jobDesc} onChange={e => setJobDesc(e.target.value)} placeholder="Paste job description..." style={{ height: 80, resize: 'vertical' }} />
            </div>
          </div>
          <button className="btn btn-primary" onClick={handleInterviewPrep} disabled={prepLoading || !jobTitle} style={{ marginBottom: 24 }}>
            {prepLoading ? <><Loader size={14} style={{ animation: 'spin 0.8s linear infinite' }} /> Generating...</> : <><Mic size={14} /> Generate Interview Guide</>}
          </button>
          {prepResult && (
            <div className="card">
              <div style={{ fontSize: '0.62rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--accent)', marginBottom: 16, fontFamily: 'var(--mono)' }}>🎤 Interview Preparation Guide</div>
              <div style={{ fontSize: '0.84rem', color: 'var(--text-2)', lineHeight: 1.75 }}>
                <ReactMarkdown>{prepResult}</ReactMarkdown>
              </div>
            </div>
          )}
        </motion.div>
      )}

      {/* Roadmap Tab */}
      {tab === 'roadmap' && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <div className="grid-2" style={{ marginBottom: 16 }}>
            <div className="input-group">
              <label>Target Role *</label>
              <input className="input" value={roadTarget} onChange={e => setRoadTarget(e.target.value)} placeholder="e.g. Machine Learning Engineer" />
            </div>
            <div className="input-group">
              <label>Years of Experience</label>
              <input className="input" type="number" min="0" max="20" value={yearsExp} onChange={e => setYearsExp(e.target.value)} />
            </div>
          </div>
          <div className="input-group" style={{ marginBottom: 16 }}>
            <label>Current Skills (comma-separated)</label>
            <input className="input" value={skills} onChange={e => setSkills(e.target.value)} placeholder="e.g. Python, JavaScript, SQL, React" />
          </div>
          <button className="btn btn-primary" onClick={handleRoadmap} disabled={roadmapLoading || !roadTarget} style={{ marginBottom: 24 }}>
            {roadmapLoading ? <><Loader size={14} style={{ animation: 'spin 0.8s linear infinite' }} /> Generating...</> : <><Map size={14} /> Generate Roadmap</>}
          </button>
          {roadmapResult && (
            <div className="card">
              <div style={{ fontSize: '0.62rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--accent)', marginBottom: 16, fontFamily: 'var(--mono)' }}>🗺️ Your Career Roadmap</div>
              <div style={{ fontSize: '0.84rem', color: 'var(--text-2)', lineHeight: 1.75 }}>
                <ReactMarkdown>{roadmapResult}</ReactMarkdown>
              </div>
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
}
