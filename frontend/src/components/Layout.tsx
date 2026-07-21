import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

export function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();

  return (
    <div className="app-shell">
      <nav className="nav-rail">
        <div className="nav-brand">
          <span className="nav-brand-mark">◈</span>
          PrivacyLens
        </div>
        <div className="nav-links">
          <NavLink to="/" end className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
            Targets
          </NavLink>
        </div>
        <div className="nav-footer">
          {user && (
            <>
              <div className="mono" style={{ marginBottom: 8, wordBreak: "break-all" }}>
                {user.email}
              </div>
              <button onClick={logout}>Sign out</button>
            </>
          )}
        </div>
      </nav>
      <main className="main-content">{children}</main>
    </div>
  );
}
