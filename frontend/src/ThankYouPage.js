import { Link } from "react-router-dom";
import { CheckCircle2, Home, Search, UploadCloud } from "lucide-react";

function ThankYouPage() {
  return (
    <div className="card empty-state" style={{ maxWidth: 540, margin: "40px auto" }}>
      <div
        style={{
          width: 56,
          height: 56,
          borderRadius: "50%",
          background: "var(--success-bg)",
          color: "var(--success)",
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          marginBottom: 14,
        }}
      >
        <CheckCircle2 size={28} />
      </div>
      <h2 style={{ margin: "0 0 8px" }}>Resume Submitted</h2>
      <p style={{ margin: "0 0 24px", color: "var(--text-secondary)" }}>
        Your PDF resume has been queued for structured extraction and vector indexing.
      </p>
      <div style={{ display: "flex", justifyContent: "center", gap: 10, flexWrap: "wrap" }}>
        <Link to="/" className="btn btn-primary">
          <Home size={16} /> Go to Dashboard
        </Link>
        <Link to="/upload" className="btn btn-secondary">
          <UploadCloud size={16} /> Upload Another
        </Link>
        <Link to="/search" className="btn btn-secondary">
          <Search size={16} /> Search Talent
        </Link>
      </div>
    </div>
  );
}

export default ThankYouPage;
