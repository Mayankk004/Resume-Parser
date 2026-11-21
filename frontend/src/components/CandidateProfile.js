import {
  AlertCircle,
  Award,
  Briefcase,
  CheckCircle2,
  Cpu,
  ExternalLink,
  FileText,
  FolderGit2,
  GraduationCap,
  Mail,
  Phone,
  Sparkles,
} from "lucide-react";

function formatValue(val) {
  if (val === null || val === undefined || val === "") return "—";
  if (Array.isArray(val)) return val.map(formatValue).join(", ");
  if (typeof val === "object") {
    return Object.entries(val)
      .map(([k, v]) => `${k}: ${formatValue(v)}`)
      .join(" | ");
  }
  return String(val);
}

function renderEntryList(items, emptyText = "None listed") {
  if (!Array.isArray(items) || items.length === 0) {
    return <p className="candidate-meta">{emptyText}</p>;
  }
  return (
    <div className="entry-list">
      {items.map((item, idx) => {
        if (typeof item === "string" || typeof item === "number") {
          return (
            <div className="entry-card" key={idx}>
              <p className="entry-kv">{item}</p>
            </div>
          );
        }
        if (item && typeof item === "object") {
          const entries = Object.entries(item).filter(
            ([, v]) => v !== null && v !== undefined && v !== ""
          );
          if (entries.length === 0) return null;
          return (
            <div className="entry-card" key={idx}>
              {entries.map(([key, value]) => (
                <p className="entry-kv" key={key}>
                  <strong>{key}:</strong>
                  <span>{formatValue(value)}</span>
                </p>
              ))}
            </div>
          );
        }
        return null;
      })}
    </div>
  );
}

function renderSkills(skills) {
  if (!skills) return <p className="candidate-meta">No skills extracted</p>;

  if (Array.isArray(skills)) {
    if (skills.length === 0) return <p className="candidate-meta">No skills extracted</p>;
    return (
      <div className="skill-tags">
        {skills.map((s, idx) => (
          <span className="skill-tag" key={idx}>
            {formatValue(s)}
          </span>
        ))}
      </div>
    );
  }

  if (typeof skills === "object") {
    const entries = Object.entries(skills).filter(([, v]) =>
      Array.isArray(v) ? v.length > 0 : Boolean(v)
    );
    if (entries.length === 0) {
      return <p className="candidate-meta">No skills extracted</p>;
    }
    return (
      <div className="entry-list">
        {entries.map(([category, items]) => (
          <div className="entry-card" key={category}>
            <div
              style={{
                fontSize: "0.8rem",
                fontWeight: 700,
                color: "var(--text-secondary)",
                marginBottom: 8,
              }}
            >
              {category}
            </div>
            <div className="skill-tags">
              {Array.isArray(items) ? (
                items.map((item, idx) => (
                  <span className="skill-tag" key={idx}>
                    {formatValue(item)}
                  </span>
                ))
              ) : (
                <span className="skill-tag">{formatValue(items)}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    );
  }

  return <p className="candidate-meta">{String(skills)}</p>;
}

function CandidateProfile({ resume, matchMeta = null }) {
  if (!resume) {
    return (
      <div className="card empty-state">
        <p>No candidate profile selected.</p>
      </div>
    );
  }

  const matchedSkills = matchMeta?.matched_skills || [];
  const missingSkills = matchMeta?.missing_skills || [];
  const matchedCriteria = matchMeta?.matched_criteria || [];

  return (
    <div className="card">
      <div className="profile-header">
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <h2 style={{ margin: 0, fontSize: "1.45rem", fontWeight: 700 }}>
              {resume.name || "Unknown Candidate"}
            </h2>
            {matchMeta && (
              <span className="badge badge-green mono">
                {matchMeta.match_score}% Match
              </span>
            )}
          </div>

          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 16,
              marginTop: 10,
              fontSize: "0.88rem",
              color: "var(--text-secondary)",
            }}
          >
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <Mail size={15} />
              {resume.email || "No email extracted"}
            </span>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <Phone size={15} />
              {resume.phone_number || "No phone extracted"}
            </span>
            {resume.file_name && (
              <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                <FileText size={15} />
                {resume.file_name}
              </span>
            )}
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <span className="badge badge-blue">
            <Cpu size={13} />
            {resume.model_type || "gemini"}
          </span>
          {resume.gpa && resume.gpa !== "0" && (
            <span className="badge badge-slate mono">GPA: {resume.gpa}</span>
          )}
          {resume.pdf_url && (
            <a
              href={resume.pdf_url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-secondary"
              style={{ padding: "5px 11px", fontSize: "0.78rem" }}
            >
              <ExternalLink size={13} /> Original PDF
            </a>
          )}
        </div>
      </div>

      {matchMeta && (
        <div
          className="alert alert-info"
          style={{ marginTop: 0, marginBottom: 22, flexDirection: "column", gap: 10 }}
        >
          <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
            <Sparkles size={15} />
            Match Breakdown ({matchMeta.semantic_score}% semantic similarity)
          </div>

          {matchedSkills.length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 6 }}>
              <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--success)" }}>
                Matched Skills:
              </span>
              {matchedSkills.map((skill, i) => (
                <span className="badge badge-green" key={i}>
                  <CheckCircle2 size={12} /> {skill}
                </span>
              ))}
            </div>
          )}

          {missingSkills.length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 6 }}>
              <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--danger)" }}>
                Missing Skills:
              </span>
              {missingSkills.map((skill, i) => (
                <span className="badge badge-red" key={i}>
                  <AlertCircle size={12} /> {skill}
                </span>
              ))}
            </div>
          )}

          {matchedSkills.length === 0 && matchedCriteria.length > 0 && (
            <div className="skill-tags">
              {matchedCriteria.map((crit, i) => (
                <span className="badge badge-blue" key={i}>
                  {crit}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="profile-section">
        <h3 className="profile-section-title">
          <Sparkles size={16} /> Skills
        </h3>
        {renderSkills(resume.skills)}
      </div>

      <div className="profile-section">
        <h3 className="profile-section-title">
          <Briefcase size={16} /> Work Experience
        </h3>
        {renderEntryList(resume.work_experience, "No work experience listed")}
      </div>

      <div className="profile-section">
        <h3 className="profile-section-title">
          <GraduationCap size={16} /> Education
        </h3>
        {renderEntryList(resume.education, "No education history listed")}
      </div>

      <div className="profile-section">
        <h3 className="profile-section-title">
          <FolderGit2 size={16} /> Projects
        </h3>
        {renderEntryList(resume.projects, "No projects listed")}
      </div>

      <div className="profile-section">
        <h3 className="profile-section-title">
          <Award size={16} /> Certifications
        </h3>
        {renderEntryList(resume.certifications, "No certifications listed")}
      </div>
    </div>
  );
}

export default CandidateProfile;
