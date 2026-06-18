const API = '/api';

const getToken = () => localStorage.getItem('jm_token');
const authHeaders = () => {
  const token = getToken();
  return token ? { 'Authorization': `Bearer ${token}` } : {};
};

async function handleRes(res: Response) {
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

// ── Auth ──────────────────────────────────────────────────

export async function registerUser(name: string, email: string, password: string) {
  return handleRes(await fetch(`${API}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, password }),
  }));
}

export async function loginUser(email: string, password: string) {
  return handleRes(await fetch(`${API}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  }));
}

export async function updateProfile(data: any) {
  return handleRes(await fetch(`${API}/auth/profile`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...(authHeaders() as any) },
    body: JSON.stringify(data),
  }));
}

export async function toggleSavedJob(jobId: string) {
  return handleRes(await fetch(`${API}/auth/saved-jobs/${jobId}`, {
    method: 'POST',
    headers: authHeaders() as any,
  }));
}

export async function trackApplication(data: {
  job_id: string; job_title?: string; company?: string;
  status?: string; notes?: string;
}) {
  return handleRes(await fetch(`${API}/auth/applications`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(authHeaders() as any) },
    body: JSON.stringify(data),
  }));
}

export async function removeApplication(jobId: string) {
  return handleRes(await fetch(`${API}/auth/applications/${jobId}`, {
    method: 'DELETE',
    headers: authHeaders() as any,
  }));
}

// ── Resumes ────────────────────────────────────────────────

export async function uploadResume(file: File, title?: string) {
  const form = new FormData();
  form.append('file', file);
  if (title) form.append('title', title);
  return handleRes(await fetch(`${API}/resumes/upload`, { method: 'POST', body: form }));
}

export async function listResumes() {
  return handleRes(await fetch(`${API}/resumes`));
}

export async function getResume(id: string) {
  return handleRes(await fetch(`${API}/resumes/${id}`));
}

export async function deleteResume(id: string) {
  return handleRes(await fetch(`${API}/resumes/${id}`, { method: 'DELETE' }));
}

export async function reEmbedResume(id: string) {
  return handleRes(await fetch(`${API}/resumes/${id}/embed`, { method: 'POST' }));
}

// ── Jobs ───────────────────────────────────────────────────

export async function scrapeJobs(
  query: string, location = 'Worldwide', maxPages = 2, sources?: string[]
) {
  const params = new URLSearchParams({ query, location, max_pages: String(maxPages) });
  if (sources && sources.length > 0) params.set('sources', sources.join(','));
  return handleRes(await fetch(`${API}/jobs/scrape?${params}`, { method: 'POST' }));
}

export async function listJobs(opts?: {
  source?: string; search?: string; query?: string;
  location?: string; limit?: number; skip?: number;
}) {
  const params = new URLSearchParams();
  if (opts?.source) params.set('source', opts.source);
  if (opts?.search) params.set('search', opts.search);
  if (opts?.query) params.set('query', opts.query);
  if (opts?.location && opts.location.toLowerCase() !== 'worldwide') params.set('location', opts.location);
  if (opts?.limit) params.set('limit', String(opts.limit));
  if (opts?.skip) params.set('skip', String(opts.skip));
  const paramStr = params.toString();
  return handleRes(await fetch(`${API}/jobs${paramStr ? '?' + paramStr : ''}`));
}

export async function getJob(id: string) {
  return handleRes(await fetch(`${API}/jobs/${id}`));
}

export async function getJobStats() {
  return handleRes(await fetch(`${API}/jobs/stats/overview`));
}

// ── Matches ────────────────────────────────────────────────

export async function runMatching(resumeId: string, topK = 10) {
  const params = new URLSearchParams({ resume_id: resumeId, top_k: String(topK) });
  return handleRes(await fetch(`${API}/matches/run?${params}`, { method: 'POST' }));
}

export async function listMatches(resumeId: string) {
  return handleRes(await fetch(`${API}/matches?resume_id=${resumeId}`));
}

// ── Career Coach ───────────────────────────────────────────

export async function coachChat(message: string, history: any[] = []) {
  return handleRes(await fetch(`${API}/coach/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history }),
  }));
}

export async function reviewResume(resume_text: string, target_role = '') {
  return handleRes(await fetch(`${API}/coach/resume-review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ resume_text, target_role }),
  }));
}

export async function interviewPrep(job_title: string, job_description = '', resume_text = '') {
  return handleRes(await fetch(`${API}/coach/interview-prep`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_title, job_description, resume_text }),
  }));
}

export async function generateRoadmap(current_skills: string[], target_role: string, years_experience = 0) {
  return handleRes(await fetch(`${API}/coach/roadmap`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ current_skills, target_role, years_experience }),
  }));
}

export async function getATSScore(resume_text: string, job_description: string) {
  return handleRes(await fetch(`${API}/coach/ats-score`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ resume_text, job_description }),
  }));
}

// ── Apply Agent ────────────────────────────────────────────

export async function generateCoverLetter(data: {
  resume_text: string; job_title: string;
  company: string; job_description: string; tone?: string;
}) {
  return handleRes(await fetch(`${API}/apply/cover-letter`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }));
}

export async function generateATSResume(data: {
  resume_text: string; job_title: string; job_description: string;
}) {
  return handleRes(await fetch(`${API}/apply/ats-resume`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }));
}

export async function generateScreeningAnswers(data: {
  questions: string[]; resume_text: string;
  job_title: string; company?: string;
}) {
  return handleRes(await fetch(`${API}/apply/screening-answers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }));
}

// ── System ─────────────────────────────────────────────────

export async function healthCheck() {
  return handleRes(await fetch('/health'));
}
