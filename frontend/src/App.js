import { useEffect, useState } from "react";
import { BrowserRouter as Router, NavLink, Route, Routes } from "react-router-dom";
import { Clock, FileSearch, LayoutDashboard, Search, UploadCloud } from "lucide-react";
import { fetchSystemStatus, subscribeSlowBackend, wakeBackend } from "./api";
import DashboardPage from "./DashboardPage";
import SearchPage from "./SearchPage";
import SearchResult from "./SearchResult";
import ThankYouPage from "./ThankYouPage";
import UploadForm from "./UploadForm";
import "./index.css";

function App() {
  const [backendOnline, setBackendOnline] = useState(null);
  const [wakingUp, setWakingUp] = useState(false);

  useEffect(() => {
    const unsubscribe = subscribeSlowBackend(setWakingUp);
    return unsubscribe;
  }, []);

  useEffect(() => {
    let mounted = true;
    // Silent initial wake-up ping for Render free-tier cold start
    wakeBackend()
      .then(() => {
        if (mounted) setBackendOnline(true);
      })
      .catch(() => {
        if (mounted) setBackendOnline(false);
      });

    const check = () => {
      fetchSystemStatus()
        .then(() => {
          if (mounted) setBackendOnline(true);
        })
        .catch(() => {
          if (mounted) setBackendOnline(false);
        });
    };
    const timer = setInterval(check, 20000);
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  return (
    <Router>
      <div className="app-shell">
        <header className="navbar">
          <div className="navbar-inner">
            <NavLink to="/" className="brand">
              <span className="brand-mark">
                <FileSearch size={20} />
              </span>
              <span>ResumeParserAI</span>
            </NavLink>

            <nav className="nav-links" aria-label="Main navigation">
              <NavLink
                to="/"
                end
                className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
              >
                <LayoutDashboard size={16} />
                <span>Candidates</span>
              </NavLink>
              <NavLink
                to="/upload"
                className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
              >
                <UploadCloud size={16} />
                <span>Upload</span>
              </NavLink>
              <NavLink
                to="/search"
                className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
              >
                <Search size={16} />
                <span>Search</span>
              </NavLink>
            </nav>

            <div
              className={`status-pill ${
                backendOnline === true
                  ? "online"
                  : backendOnline === false
                  ? "offline"
                  : ""
              }`}
            >
              <span className="status-dot" />
              <span>
                {backendOnline === true
                  ? "API Connected"
                  : backendOnline === false
                  ? "API Offline"
                  : "Connecting..."}
              </span>
            </div>
          </div>
        </header>

        {wakingUp && (
          <div
            style={{
              background: "var(--warning-bg)",
              color: "var(--warning)",
              borderBottom: "1px solid #fde68a",
              padding: "8px 20px",
              fontSize: "0.86rem",
              fontWeight: 500,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
            }}
          >
            <Clock size={15} />
            <span>Waking up backend server (free-tier cold start, ~30s)...</span>
          </div>
        )}

        <main className="main-content">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/upload" element={<UploadForm />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/search-result" element={<SearchResult />} />
            <Route path="/resume/:id" element={<SearchResult />} />
            <Route path="/thank-you" element={<ThankYouPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
