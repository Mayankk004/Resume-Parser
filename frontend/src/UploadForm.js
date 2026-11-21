import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Clock,
  Cpu,
  FileText,
  Loader2,
  Search,
  Sparkles,
  UploadCloud,
  X,
} from "lucide-react";
import { fetchBatchStatus, uploadResumesBatch } from "./api";

const MAX_FILES = 10;
const MAX_FILE_BYTES = 5 * 1024 * 1024;

function StatusBadge({ status }) {
  if (status === "completed") {
    return (
      <span className="badge badge-green">
        <CheckCircle2 size={12} /> Done
      </span>
    );
  }
  if (status === "processing") {
    return (
      <span className="badge badge-blue">
        <Loader2 size={12} className="spin" /> Processing
      </span>
    );
  }
  if (status === "queued") {
    return (
      <span className="badge badge-amber">
        <Clock size={12} /> Queued
      </span>
    );
  }
  return (
    <span className="badge badge-red">
      <AlertCircle size={12} /> Failed
    </span>
  );
}

function UploadForm() {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [dragActive, setDragActive] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [batchJob, setBatchJob] = useState(null); // { batch_id, files: [...] }
  const [error, setError] = useState("");
  const fileInputRef = useRef(null);

  const isBatchRunning = Boolean(
    batchJob?.files?.some((f) => f.status === "queued" || f.status === "processing")
  );

  useEffect(() => {
    if (!batchJob?.batch_id || !isBatchRunning) return;
    const interval = setInterval(async () => {
      try {
        const updated = await fetchBatchStatus(batchJob.batch_id);
        setBatchJob(updated);
      } catch {
        // Ignore transient poll errors
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [batchJob, isBatchRunning]);

  const addFiles = (incomingList) => {
    const incoming = Array.from(incomingList || []);
    if (incoming.length === 0) return;

    const validationErrors = [];
    const validNew = [];

    for (const file of incoming) {
      const isPdf =
        file.name.toLowerCase().endsWith(".pdf") ||
        file.type === "application/pdf";
      if (!isPdf) {
        validationErrors.push(`"${file.name}" is not a PDF file.`);
        continue;
      }
      if (file.size > MAX_FILE_BYTES) {
        validationErrors.push(`"${file.name}" exceeds the 5 MB limit.`);
        continue;
      }
      if (file.size === 0) {
        validationErrors.push(`"${file.name}" is empty.`);
        continue;
      }
      validNew.push(file);
    }

    setSelectedFiles((prev) => {
      const existingNames = new Set(prev.map((f) => `${f.name}_${f.size}`));
      const deduped = validNew.filter((f) => !existingNames.has(`${f.name}_${f.size}`));
      const combined = [...prev, ...deduped];
      if (combined.length > MAX_FILES) {
        validationErrors.push(`Maximum ${MAX_FILES} PDFs allowed per batch.`);
        return combined.slice(0, MAX_FILES);
      }
      return combined;
    });

    setError(validationErrors.join(" "));
  };

  const removeFile = (index) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    addFiles(e.dataTransfer.files);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (selectedFiles.length === 0) {
      setError("Please select at least one PDF resume.");
      return;
    }

    setError("");
    setSubmitting(true);
    try {
      const response = await uploadResumesBatch(selectedFiles);
      setBatchJob(response);
      setSelectedFiles([]);
    } catch (err) {
      const detail =
        err.response?.data?.detail ||
        "Upload failed. Ensure the backend server is reachable.";
      setError(detail);
    } finally {
      setSubmitting(false);
    }
  };

  const completedCount =
    batchJob?.files?.filter((f) => f.status === "completed").length || 0;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Batch Upload & Parse Resumes</h1>
          <p className="page-subtitle">
            Upload up to {MAX_FILES} PDF resumes at once (max 5 MB each) for Gemini extraction & pgvector indexing.
          </p>
        </div>
      </div>

      <div className="upload-layout">
        <div className="card">
          <form onSubmit={handleSubmit}>
            <div
              className={`dropzone ${dragActive ? "drag-active" : ""}`}
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => {
                e.preventDefault();
                setDragActive(true);
              }}
              onDragLeave={() => setDragActive(false)}
              onDrop={handleDrop}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  fileInputRef.current?.click();
                }
              }}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept="application/pdf,.pdf"
                onChange={(e) => {
                  addFiles(e.target.files);
                  e.target.value = "";
                }}
                style={{ display: "none" }}
              />
              <div className="dropzone-icon">
                <UploadCloud size={26} />
              </div>
              <div style={{ fontWeight: 600, fontSize: "1rem", marginBottom: 4 }}>
                Drop PDF resumes here, or click to browse
              </div>
              <div className="candidate-meta">
                Up to {MAX_FILES} PDF files per batch · Max 5 MB per file
              </div>
            </div>

            {selectedFiles.length > 0 && (
              <div style={{ marginTop: 18 }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 10,
                    fontSize: "0.88rem",
                    fontWeight: 600,
                  }}
                >
                  <span>Selected Resumes ({selectedFiles.length}/{MAX_FILES})</span>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ padding: "4px 10px", fontSize: "0.78rem" }}
                    onClick={() => setSelectedFiles([])}
                  >
                    Clear All
                  </button>
                </div>

                <div className="entry-list">
                  {selectedFiles.map((file, idx) => (
                    <div
                      className="entry-card"
                      key={`${file.name}-${idx}`}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: 12,
                        padding: "10px 14px",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
                        <FileText size={16} style={{ color: "var(--primary)", flexShrink: 0 }} />
                        <div style={{ minWidth: 0 }}>
                          <div
                            style={{
                              fontWeight: 600,
                              fontSize: "0.9rem",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {file.name}
                          </div>
                          <div className="candidate-meta">
                            {(file.size / 1024).toFixed(1)} KB
                          </div>
                        </div>
                      </div>
                      <button
                        type="button"
                        className="btn btn-danger-ghost"
                        onClick={() => removeFile(idx)}
                        aria-label={`Remove ${file.name}`}
                      >
                        <X size={16} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {error && (
              <div className="alert alert-error">
                <AlertCircle size={18} />
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: "100%", padding: "12px 18px", marginTop: 18 }}
              disabled={submitting || selectedFiles.length === 0}
            >
              {submitting ? (
                <>
                  <Loader2 size={18} className="spin" /> Uploading Batch...
                </>
              ) : (
                <>
                  <Sparkles size={18} /> Extract & Index{" "}
                  {selectedFiles.length > 0 ? `${selectedFiles.length} Resume(s)` : "Resumes"}
                </>
              )}
            </button>
          </form>

          {batchJob && (
            <div style={{ marginTop: 24, paddingTop: 20, borderTop: "1px solid var(--border)" }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: 10,
                  marginBottom: 12,
                }}
              >
                <div style={{ fontWeight: 700, fontSize: "0.96rem" }}>
                  Batch Processing Status ({completedCount}/{batchJob.files.length} done)
                </div>
                {!isBatchRunning && completedCount > 0 && (
                  <Link to="/search" className="btn btn-primary" style={{ padding: "7px 14px", fontSize: "0.85rem" }}>
                    <Search size={15} /> Go to Talent Search <ArrowRight size={15} />
                  </Link>
                )}
              </div>

              <div className="entry-list">
                {batchJob.files.map((item, idx) => (
                  <div
                    key={`${item.file_name}-${idx}`}
                    className="entry-card"
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: 12,
                      flexWrap: "wrap",
                    }}
                  >
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>
                        {item.candidate_name || item.file_name}
                      </div>
                      <div className="candidate-meta">
                        {item.candidate_name ? item.file_name : "Waiting in extraction queue"}
                      </div>
                      {item.error && (
                        <div style={{ color: "var(--danger)", fontSize: "0.82rem", marginTop: 4 }}>
                          {item.error}
                        </div>
                      )}
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <StatusBadge status={item.status} />
                      {item.status === "completed" && item.resume_id && (
                        <Link
                          to={`/resume/${item.resume_id}`}
                          className="btn btn-secondary"
                          style={{ padding: "5px 10px", fontSize: "0.78rem" }}
                        >
                          View Profile
                        </Link>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="card">
          <h3 style={{ margin: "0 0 14px", fontSize: "1.05rem", display: "flex", alignItems: "center", gap: 8 }}>
            <Cpu size={18} style={{ color: "var(--primary)" }} /> Gemini + pgvector Pipeline
          </h3>
          <div className="entry-list">
            <div className="entry-card">
              <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>1. Direct PDF Understanding</div>
              <div className="candidate-meta">
                PDF bytes are sent directly to Google Gemini Structured Outputs—supporting both digital and scanned PDFs without disk storage.
              </div>
            </div>
            <div className="entry-card">
              <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>2. 768-Dim Document Embeddings</div>
              <div className="candidate-meta">
                Generates L2-normalized vectors with gemini-embedding-001 (RETRIEVAL_DOCUMENT).
              </div>
            </div>
            <div className="entry-card">
              <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>3. Atomic Postgres + HNSW Upsert</div>
              <div className="candidate-meta">
                Saves structured metadata and vector embeddings together in one PostgreSQL transaction.
              </div>
            </div>
          </div>

          <div style={{ marginTop: 18, paddingTop: 16, borderTop: "1px solid var(--border)" }}>
            <Link to="/" className="btn btn-secondary" style={{ width: "100%" }}>
              <FileText size={16} /> Browse All Candidates
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default UploadForm;
