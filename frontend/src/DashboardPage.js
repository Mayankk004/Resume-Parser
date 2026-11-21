import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { RealtimeProvider, useLiveQuery } from "@neon/realtime-react";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Database,
  Eye,
  FileText,
  HardDrive,
  Loader2,
  Plus,
  Radio,
  Search,
  Trash2,
  Users,
} from "lucide-react";
import {
  deleteResumeById,
  fetchResumes,
  fetchSealedResumes,
  fetchSystemStatus,
} from "./api";
import { getRealtimeClient } from "./realtimeClient";

function extractSkillPreview(skills) {
  if (!skills) return [];
  if (Array.isArray(skills)) return skills.slice(0, 5).map(String);
  if (typeof skills === "object") {
    const collected = [];
    for (const val of Object.values(skills)) {
      if (Array.isArray(val)) {
        collected.push(...val.map(String));
      } else if (val) {
        collected.push(String(val));
      }
    }
    return collected.slice(0, 5);
  }
  return [];
}

function StatusBadge({ status }) {
  if (status === "completed") {
    return (
      <span className="badge badge-green">
        <CheckCircle2 size={12} /> Indexed
      </span>
    );
  }
  if (status === "processing") {
    return (
      <span className="badge badge-amber">
        <Loader2 size={12} className="spin" /> Processing
      </span>
    );
  }
  return (
    <span className="badge badge-red">
      <AlertCircle size={12} /> Failed
    </span>
  );
}

function LiveResumeSync({ sealedQuery, refreshQuery, onRows, onStatus }) {
  const { data, status } = useLiveQuery(sealedQuery, { refreshQuery });

  useEffect(() => {
    onStatus(status);
  }, [status, onStatus]);

  useEffect(() => {
    if (Array.isArray(data)) {
      onRows(data);
    }
  }, [data, onRows]);

  return null;
}

function DashboardPage() {
  const [resumes, setResumes] = useState([]);
  const [sysStatus, setSysStatus] = useState(null);
  const [sealedPayload, setSealedPayload] = useState(null);
  const [realtimeStatus, setRealtimeStatus] = useState("idle");
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deletingId, setDeletingId] = useState(null);

  const loadData = useCallback(async () => {
    try {
      const [resumeList, statusData] = await Promise.all([
        fetchResumes(),
        fetchSystemStatus(),
      ]);
      setResumes(resumeList);
      setSysStatus(statusData);
      setError("");

      if (statusData?.realtime_configured) {
        try {
          const liveRes = await fetchSealedResumes();
          setSealedPayload(liveRes);
        } catch {
          // Non-fatal: dashboard continues with REST data
        }
      }
    } catch (err) {
      setError("Unable to reach backend API.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const refreshSealedQuery = useCallback(async () => {
    const res = await fetchSealedResumes();
    return res.sealedQuery;
  }, []);

  const handleLiveRows = useCallback((rows) => {
    setResumes(rows);
  }, []);

  const handleDelete = async (id) => {
    setDeletingId(id);
    try {
      await deleteResumeById(id);
      setResumes((prev) => prev.filter((r) => r.id !== id));
    } catch (err) {
      setError("Failed to delete candidate resume.");
    } finally {
      setDeletingId(null);
    }
  };

  const filtered = resumes.filter((r) => {
    if (!filter.trim()) return true;
    const q = filter.toLowerCase();
    const skillText = extractSkillPreview(r.skills).join(" ").toLowerCase();
    return (
      (r.name || "").toLowerCase().includes(q) ||
      (r.email || "").toLowerCase().includes(q) ||
      (r.file_name || "").toLowerCase().includes(q) ||
      skillText.includes(q)
    );
  });

  const completedCount = resumes.filter((r) => r.status === "completed").length;
  const processingCount = sysStatus?.processing_resumes || 0;
  const rtUrl = sealedPayload?.realtimeUrl || sysStatus?.realtime_url;
  const rtClient = rtUrl ? getRealtimeClient(rtUrl) : null;

  return (
    <div>
      {rtClient && sealedPayload?.sealedQuery && (
        <RealtimeProvider client={rtClient}>
          <LiveResumeSync
            sealedQuery={sealedPayload.sealedQuery}
            refreshQuery={refreshSealedQuery}
            onRows={handleLiveRows}
            onStatus={setRealtimeStatus}
          />
        </RealtimeProvider>
      )}

      <div className="page-header">
        <div>
          <h1 className="page-title">Talent Repository</h1>
          <p className="page-subtitle">
            Batch upload PDF resumes to Neon Object Storage, index with Gemini + pgvector, and sync live with Neon Realtime.
          </p>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <Link to="/search" className="btn btn-secondary">
            <Search size={16} /> Search Talent
          </Link>
          <Link to="/upload" className="btn btn-primary">
            <Plus size={16} /> Upload Resumes
          </Link>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div>
            <div className="stat-label">Total Candidates</div>
            <div className="stat-value">{resumes.length}</div>
          </div>
          <div className="stat-icon">
            <Users size={20} />
          </div>
        </div>
        <div className="stat-card">
          <div>
            <div className="stat-label">Indexed & Searchable</div>
            <div className="stat-value">{completedCount}</div>
          </div>
          <div className="stat-icon" style={{ background: "var(--success-bg)", color: "var(--success)" }}>
            <CheckCircle2 size={20} />
          </div>
        </div>
        <div className="stat-card">
          <div>
            <div className="stat-label">Processing Queue</div>
            <div className="stat-value">{processingCount}</div>
          </div>
          <div className="stat-icon" style={{ background: "var(--warning-bg)", color: "var(--warning)" }}>
            <Clock size={20} />
          </div>
        </div>
        <div className="stat-card">
          <div>
            <div className="stat-label">Vector Engine</div>
            <div className="stat-value" style={{ fontSize: "1.1rem" }}>
              {sysStatus?.vector_backend === "pgvector" ? "pgvector HNSW" : "SQLite Local"}
            </div>
          </div>
          <div className="stat-icon">
            <Database size={20} />
          </div>
        </div>
      </div>

      {sysStatus && (
        <div className="engine-strip">
          <span className="engine-strip-label">Active Neon Stack:</span>
          <span className={`badge ${sysStatus.database === "postgresql" ? "badge-green" : "badge-slate"}`}>
            DB: {sysStatus.database === "postgresql" ? "Lakebase Postgres + pgvector" : "SQLite (Fallback)"}
          </span>
          <span className={`badge ${sysStatus.storage_configured ? "badge-green" : "badge-slate"}`}>
            <HardDrive size={12} />
            Storage: {sysStatus.storage_configured ? `Neon S3 (${sysStatus.storage_bucket})` : "Not Configured"}
          </span>
          <span
            className={`badge ${
              realtimeStatus === "live"
                ? "badge-green"
                : sysStatus.realtime_configured
                ? "badge-amber"
                : "badge-slate"
            }`}
          >
            <Radio size={12} />
            Realtime:{" "}
            {realtimeStatus === "live"
              ? "Live Sync"
              : sysStatus.realtime_configured
              ? realtimeStatus
              : "Off"}
          </span>
          <span className={`badge ${sysStatus.gemini_configured ? "badge-blue" : "badge-red"}`}>
            AI: {sysStatus.gemini_configured ? `Gemini (${sysStatus.gemini_model})` : "Key Missing"}
          </span>
        </div>
      )}

      {error && (
        <div className="alert alert-error" style={{ marginBottom: 20 }}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      <div className="card">
        <div className="toolbar">
          <div className="input-wrapper">
            <Search size={16} className="input-icon" />
            <input
              type="text"
              className="text-input with-icon"
              placeholder="Filter candidates by name, email, skill, or filename..."
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
          </div>
          <span className="candidate-meta">
            Showing {filtered.length} of {resumes.length}
          </span>
        </div>

        {loading ? (
          <div className="empty-state">
            <Loader2 size={28} className="spin" style={{ color: "var(--primary)" }} />
            <p>Loading candidate repository...</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="empty-state">
            <FileText size={38} style={{ color: "var(--text-muted)", marginBottom: 10 }} />
            <h3 style={{ margin: "0 0 6px" }}>
              {resumes.length === 0 ? "No resumes uploaded yet" : "No matching candidates"}
            </h3>
            <p style={{ margin: "0 0 18px" }}>
              {resumes.length === 0
                ? "Upload PDF resumes to extract structured skills, experience, store PDFs in Neon Object Storage, and index for pgvector search."
                : "Try clearing your filter query."}
            </p>
            {resumes.length === 0 && (
              <Link to="/upload" className="btn btn-primary">
                <Plus size={16} /> Upload Resumes
              </Link>
            )}
          </div>
        ) : (
          <div className="candidate-grid">
            {filtered.map((resume) => {
              const skills = extractSkillPreview(resume.skills);
              return (
                <div className="candidate-card" key={resume.id}>
                  <div className="candidate-card-header">
                    <div>
                      <h3 className="candidate-name">{resume.name}</h3>
                      <div className="candidate-meta">
                        {resume.email || resume.file_name || "No email"}
                      </div>
                    </div>
                    <StatusBadge status={resume.status} />
                  </div>

                  {skills.length > 0 && (
                    <div className="skill-tags">
                      {skills.map((skill, idx) => (
                        <span className="skill-tag" key={idx}>
                          {skill}
                        </span>
                      ))}
                    </div>
                  )}

                  <div className="candidate-card-footer">
                    <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                      <span className="badge badge-slate mono">{resume.model_type || "gemini"}</span>
                      {resume.storage_key && (
                        <span className="badge badge-blue" title="Stored in Neon Object Storage">
                          PDF Stored
                        </span>
                      )}
                    </div>
                    <div style={{ display: "flex", gap: 6 }}>
                      <Link
                        to={`/resume/${resume.id}`}
                        className="btn btn-secondary"
                        style={{ padding: "6px 12px", fontSize: "0.82rem" }}
                      >
                        <Eye size={14} /> View
                      </Link>
                      <button
                        type="button"
                        className="btn btn-danger-ghost"
                        onClick={() => handleDelete(resume.id)}
                        disabled={deletingId === resume.id}
                        aria-label={`Delete ${resume.name}`}
                      >
                        {deletingId === resume.id ? (
                          <Loader2 size={15} className="spin" />
                        ) : (
                          <Trash2 size={15} />
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default DashboardPage;
