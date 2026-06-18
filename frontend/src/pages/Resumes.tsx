import { useState, useRef, useEffect, useCallback } from 'react';
import { Upload, FileText, Trash2, Eye, Zap } from 'lucide-react';
import { uploadResume, listResumes, getResume, deleteResume, reEmbedResume } from '../api';

export default function Resumes() {
  const [resumes, setResumes] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [toast, setToast] = useState<{ msg: string; type: string } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(() => {
    listResumes()
      .then(setResumes)
      .catch(e => console.error('Failed to load resumes:', e));
  }, []);
  useEffect(() => { load(); }, [load]);

  const showToast = (msg: string, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  };

  const handleUpload = async (file: File) => {
    if (!file.name.endsWith('.pdf')) { showToast('Only PDF files accepted', 'error'); return; }
    setUploading(true);
    try {
      await uploadResume(file);
      showToast(`✅ "${file.name}" uploaded & parsed!`);
      load();
    } catch (e: any) {
      showToast(e.message || 'Upload failed', 'error');
    }
    setUploading(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteResume(id);
      showToast('Resume deleted');
      if (selected?.id === id) setSelected(null);
      load();
    } catch { showToast('Delete failed', 'error'); }
  };

  const viewResume = async (id: string) => {
    try {
      const data = await getResume(id);
      setSelected(data);
    } catch { showToast('Failed to load resume', 'error'); }
  };

  const handleEmbed = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    showToast('⏳ Generating embeddings...');
    try {
      await reEmbedResume(id);
      showToast('✅ Embeddings generated!');
      load();
    } catch (err: any) {
      showToast(err.message || 'Embedding failed', 'error');
    }
  };

  return (
    <div style={{ position: 'relative', zIndex: 1 }}>
      <div className="page-header">
        <h2>Resumes</h2>
        <p>Upload and manage your PDF resumes — they'll be parsed, sectioned, and embedded for AI matching</p>
      </div>

      {/* Upload Zone */}
      <div
        className={`upload-zone ${dragging ? 'dragging' : ''}`}
        onClick={() => fileRef.current?.click()}
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        style={{ marginBottom: 32 }}
      >
        {uploading ? (
          <>
            <div className="spinner" style={{ margin: '0 auto 16px' }} />
            <h3>Parsing your resume...</h3>
            <p>Extracting text, detecting sections, generating embeddings</p>
          </>
        ) : (
          <>
            <Upload size={40} />
            <h3>Drop your PDF resume here</h3>
            <p>or click to browse files — max 10MB</p>
          </>
        )}
        <input ref={fileRef} type="file" accept=".pdf" hidden onChange={e => {
          const f = e.target.files?.[0];
          if (f) handleUpload(f);
          e.target.value = '';
        }} />
      </div>

      {/* Resume List */}
      {resumes.length === 0 ? (
        <div className="empty-state">
          <FileText size={48} />
          <h3>No resumes yet</h3>
          <p>Upload a PDF resume above to get started</p>
        </div>
      ) : (
        <div className="jobs-list">
          {resumes.map((r: any) => (
            <div key={r.id} className="job-card" onClick={() => viewResume(r.id)}>
              <div className="job-icon">
                <FileText size={20} />
              </div>
              <div style={{ flex: 1 }}>
                <div className="job-title">{r.title}</div>
                <div className="job-company">{r.file_name}</div>
                <div className="job-meta">
                  <span>📝 {r.word_count} words</span>
                  <span>{r.has_embedding ? '🧠 Embedded' : '⏳ No embedding'}</span>
                  <span>📅 {new Date(r.created_at).toLocaleDateString()}</span>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                {!r.has_embedding && (
                  <button
                    className="btn btn-ghost"
                    style={{ padding: '5px 10px', fontSize: '0.7rem', color: 'var(--accent)' }}
                    title="Generate AI embeddings for matching"
                    onClick={e => handleEmbed(r.id, e)}
                  >
                    <Zap size={12} /> Embed
                  </button>
                )}
                <button className="btn btn-ghost" style={{ padding: '6px 10px' }} onClick={e => { e.stopPropagation(); viewResume(r.id); }}>
                  <Eye size={14} />
                </button>
                <button className="btn btn-ghost" style={{ padding: '6px 10px', color: 'var(--error)' }} onClick={e => { e.stopPropagation(); handleDelete(r.id); }}>
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Detail Panel */}
      {selected && (
        <>
          <div className="detail-panel-backdrop" onClick={() => setSelected(null)} />
          <div className="detail-panel">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
              <h3 style={{ fontWeight: 800, fontSize: '1.2rem' }}>{selected.title}</h3>
              <button className="btn btn-ghost" onClick={() => setSelected(null)} style={{ padding: '6px 12px', fontSize: '0.75rem' }}>✕ Close</button>
            </div>
            <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
              <span className="tag">📝 {selected.word_count} words</span>
              <span className="tag">{selected.has_embedding ? '🧠 Embedded' : '⏳ Pending'}</span>
              <span className="tag">📄 {selected.file_name}</span>
            </div>
            <div style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-muted)', marginBottom: 12, fontFamily: 'var(--font-mono)' }}>
              Parsed Sections ({selected.sections?.length || 0})
            </div>
            <div className="sections-list">
              {selected.sections?.map((sec: any, i: number) => (
                <div key={i} className="section-chip">
                  <div className="section-chip-header">{sec.section_type}</div>
                  <div className="section-chip-body">{sec.content}</div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {toast && <div className={`toast ${toast.type}`}>{toast.msg}</div>}
    </div>
  );
}
