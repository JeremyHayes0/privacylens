import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { createTarget, listTargets } from "../api/targets";
import { ApiError } from "../api/client";
import { Layout } from "../components/Layout";
import { useAuth } from "../context/AuthContext";
import { useAsync } from "../hooks/useAsync";

export function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { data: targets, error, isLoading, reload } = useAsync(listTargets);

  const canManageTargets = user?.role === "admin" || user?.role === "analyst";

  const [isFormOpen, setIsFormOpen] = useState(false);
  const [url, setUrl] = useState("");
  const [label, setLabel] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    setIsSubmitting(true);
    try {
      await createTarget({ url, label });
      setUrl("");
      setLabel("");
      setIsFormOpen(false);
      reload();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Could not add target.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Layout>
      <div className="page-header">
        <div>
          <h1>Targets</h1>
          <p className="page-subtitle">Websites your organization is monitoring.</p>
        </div>
        {canManageTargets && (
          <button className="btn btn-primary" onClick={() => setIsFormOpen((open) => !open)}>
            {isFormOpen ? "Cancel" : "Add target"}
          </button>
        )}
      </div>

      {isFormOpen && (
        <div className="panel panel-padded" style={{ marginBottom: 20 }}>
          <form onSubmit={handleCreate}>
            {formError && <div className="form-error">{formError}</div>}
            <div className="form-field">
              <label htmlFor="target-url">URL</label>
              <input
                id="target-url"
                type="text"
                placeholder="https://example.com"
                required
                value={url}
                onChange={(event) => setUrl(event.target.value)}
              />
            </div>
            <div className="form-field">
              <label htmlFor="target-label">Label</label>
              <input
                id="target-label"
                type="text"
                placeholder="Marketing site"
                required
                value={label}
                onChange={(event) => setLabel(event.target.value)}
              />
            </div>
            <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
              {isSubmitting ? "Adding…" : "Add target"}
            </button>
          </form>
        </div>
      )}

      <div className="panel">
        {isLoading && <div className="empty-state">Loading targets…</div>}
        {error && <div className="empty-state">{error}</div>}
        {targets && targets.length === 0 && (
          <div className="empty-state">
            No targets yet.{" "}
            {canManageTargets ? "Add a website above to start monitoring it." : "Ask an admin or analyst to add one."}
          </div>
        )}
        {targets && targets.length > 0 && (
          <table className="data-table">
            <thead>
              <tr>
                <th>Label</th>
                <th>URL</th>
                <th>Status</th>
                <th>Added</th>
              </tr>
            </thead>
            <tbody>
              {targets.map((target) => (
                <tr
                  key={target.id}
                  className="clickable"
                  onClick={() => navigate(`/targets/${target.id}`)}
                >
                  <td>{target.label}</td>
                  <td className="mono">{target.url}</td>
                  <td>{target.is_active ? "Active" : "Inactive"}</td>
                  <td className="mono">{new Date(target.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Layout>
  );
}
