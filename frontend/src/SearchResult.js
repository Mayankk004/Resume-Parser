import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { ArrowLeft, Loader2, Search, UploadCloud } from "lucide-react";
import { fetchResumeById } from "./api";
import CandidateProfile from "./components/CandidateProfile";

function SearchResult() {
  const { id } = useParams();
  const location = useLocation();
  const searchResponse = location.state?.searchResponse || null;

  const [selectedIndex, setSelectedIndex] = useState(0);
  const [singleResume, setSingleResume] = useState(location.state?.resume || null);
  const [loading, setLoading] = useState(Boolean(id && !location.state?.resume));
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    let active = true;
    setLoading(true);
    fetchResumeById(id)
      .then((data) => {
        if (active) {
          setSingleResume(data);
          setError("");
        }
      })
      .catch(() => {
        if (active) setError("Candidate profile could not be loaded.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [id]);

  if (id) {
    return (
      <div>
        <div className="page-header">
          <div>
            <Link to="/" className="btn btn-secondary" style={{ marginBottom: 12, padding: "6px 12px" }}>
              <ArrowLeft size={15} /> Back to Repository
            </Link>
            <h1 className="page-title">Candidate Profile</h1>
          </div>
        </div>

        {loading ? (
          <div className="card empty-state">
            <Loader2 size={28} className="spin" style={{ color: "var(--primary)" }} />
            <p>Loading candidate profile...</p>
          </div>
        ) : error ? (
          <div className="card empty-state">
            <p>{error}</p>
            <Link to="/" className="btn btn-primary">
              Back to Dashboard
            </Link>
          </div>
        ) : (
          <CandidateProfile resume={singleResume} />
        )}
      </div>
    );
  }

  const results = searchResponse?.results || [];
  const activeMatch = results[selectedIndex] || null;

  return (
    <div>
      <div className="page-header">
        <div>
          <Link to="/search" className="btn btn-secondary" style={{ marginBottom: 12, padding: "6px 12px" }}>
            <ArrowLeft size={15} /> New Search
          </Link>
          <h1 className="page-title">Search Results</h1>
          {searchResponse?.query && (
            <p className="page-subtitle">
              Query: <strong>“{searchResponse.query}”</strong> — Evaluated{" "}
              {searchResponse.total_candidates} indexed candidate(s)
            </p>
          )}
        </div>
      </div>

      {results.length === 0 ? (
        <div className="card empty-state">
          <Search size={36} style={{ color: "var(--text-muted)", marginBottom: 10 }} />
          <h3 style={{ margin: "0 0 6px" }}>
            {searchResponse?.message || "No matching candidates found"}
          </h3>
          <p style={{ margin: "0 0 18px" }}>
            Upload candidate PDF resumes first or try a broader search prompt.
          </p>
          <div style={{ display: "flex", justifyContent: "center", gap: 10 }}>
            <Link to="/upload" className="btn btn-primary">
              <UploadCloud size={16} /> Upload Resumes
            </Link>
            <Link to="/search" className="btn btn-secondary">
              Try Another Query
            </Link>
          </div>
        </div>
      ) : (
        <div className="results-layout">
          <div className="card card-compact">
            <div style={{ fontWeight: 700, fontSize: "0.9rem", marginBottom: 12, color: "var(--text-secondary)" }}>
              RANKED MATCHES ({results.length})
            </div>
            <div className="rank-list">
              {results.map((item, idx) => (
                <button
                  type="button"
                  key={item.resume.id}
                  onClick={() => setSelectedIndex(idx)}
                  className={`rank-item ${selectedIndex === idx ? "active" : ""}`}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                    <span style={{ fontWeight: 700, fontSize: "0.95rem", color: "var(--text-primary)" }}>
                      #{idx + 1} {item.resume.name}
                    </span>
                    <span className="badge badge-green mono">{item.match_score}%</span>
                  </div>
                  <div className="candidate-meta" style={{ marginTop: 4 }}>
                    {item.resume.email || item.resume.file_name || "Candidate"}
                  </div>
                  <div className="candidate-meta" style={{ marginTop: 4, fontSize: "0.78rem" }}>
                    Semantic: {item.semantic_score}% · Matched skills: {item.matched_skills?.length || 0}
                  </div>
                </button>
              ))}
            </div>
          </div>

          <CandidateProfile
            resume={activeMatch?.resume}
            matchMeta={
              activeMatch
                ? {
                    match_score: activeMatch.match_score,
                    semantic_score: activeMatch.semantic_score,
                    matched_skills: activeMatch.matched_skills,
                    missing_skills: activeMatch.missing_skills,
                    matched_criteria: activeMatch.matched_criteria,
                  }
                : null
            }
          />
        </div>
      )}
    </div>
  );
}

export default SearchResult;
