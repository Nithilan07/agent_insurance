import React from "react";
import { Link, useLocation } from "react-router-dom";

export default function Navbar() {
  const location = useLocation();

  return (
    <div className="nav-root">
      {/* Logo */}
      <div className="nav-logo">🏥 Insurance Agency</div>

      {/* Links */}
      <div className="nav-links">
        <Link
          to="/dashboard"
          className={`nav-link ${
            location.pathname.startsWith("/dashboard") ? "active" : ""
          }`}
        >
          Dashboard
        </Link>
      </div>

      <style jsx>{`
        .nav-root {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 14px 28px;
          background: #0f172a;
          color: #e2e8f0;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.22);
          position: sticky;
          top: 0;
          z-index: 50;
        }

        .nav-logo {
          font-size: 20px;
          font-weight: 700;
          letter-spacing: 0.5px;
          color: #f8fafc;
        }

        .nav-links {
          display: flex;
          align-items: center;
          gap: 20px;
        }

        .nav-link {
          color: #a5b4fc;
          text-decoration: none;
          font-weight: 600;
          font-size: 15px;
          padding: 8px 12px;
          border-radius: 8px;
          transition: background 0.25s ease, color 0.25s ease;
        }

        .nav-link:hover {
          background: #1e293b;
          color: #c7d2fe;
        }

        .nav-link.active {
          background: #1e3a8a;
          color: white;
        }
      `}</style>
    </div>
  );
}
