import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertCircle, Loader2, Search, Sparkles } from "lucide-react";
import { searchResumes } from "./api";

const EXAMPLE_PROMPTS = [
  "Python backend developer with FastAPI, PostgreSQL, and Docker experience",
  "Frontend engineer skilled in React, TypeScript, and Next.js",
  "Machine learning engineer with PyTorch, NLP, and RAG experience",
];

function SearchPage() {
  const [userPrompt, setUserPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleSearch = async (e) => {
    if (e) e.preventDefault();
    const trimmed = userPrompt.trim();
    if (!trimmed) {
      setError("Please describe the candidate skills, experience, or background you are looking for.");
      return;
    }

    setError("");
    setLoading(true);
    try {
      const data = await searchResumes(trimmed, 5);
      navigate("/search-result", { state: { searchResponse: data } });
    } catch (err) {
      const detail =
        err.response?.data?.detail ||
        "Search failed. Ensure the backend server is reachable.";
      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Semantic Talent Search</h1>
          <p className="page-subtitle">
            Describe your ideal candidate in plain English — pgvector cosine similarity + Gemini criteria ranking finds the best fits.
          </p>
        </div>
      </div>

      <div className="card search-box-card">
        <form onSubmit={handleSearch}>
          <label
            htmlFor="talent-search-input"
            style={{ display: "block", fontWeight: 600, fontSize: "0.92rem" }}
          >
            Candidate Requirements Prompt
          </label>
          <div className="search-form-row">
            <div className="input-wrapper">
              <Search size={18} className="input-icon" />
              <input
                id="talent-search-input"
                type="text"
                placeholder="e.g., Senior Python & FastAPI engineer with PostgreSQL and Docker..."
                value={userPrompt}
                onChange={(e) => setUserPrompt(e.target.value)}
                className="text-input with-icon"
                disabled={loading}
              />
            </div>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={{ minWidth: 160 }}
            >
              {loading ? (
                <>
                  <Loader2 size={17} className="spin" /> Searching...
                </>
              ) : (
                <>
                  <Sparkles size={17} /> Find Candidates
                </>
              )}
            </button>
          </div>
        </form>

        <div className="example-chips">
          <span style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--text-muted)" }}>
            Try a sample query:
          </span>
          {EXAMPLE_PROMPTS.map((example, idx) => (
            <button
              key={idx}
              type="button"
              className="example-chip"
              onClick={() => setUserPrompt(example)}
            >
              {example}
            </button>
          ))}
        </div>

        {error && (
          <div className="alert alert-error">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default SearchPage;
