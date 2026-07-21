import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { createScan, listScansForTarget } from "../api/scans";
import { getTarget } from "../api/targets";
import { Layout } from "../components/Layout";
import { ScanStatusPill } from "../components/Pills";
import { useAuth } from "../context/AuthContext";
import { useAsync } from "../hooks/useAsync";

export function TargetDetailPage() {
  const { targetId } = useParams<{ targetId: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();

  const {
    data: target,
    error: targetError,
    isLoading: isTargetLoading,
  } = useAsync(() => getTarget(targetId!), [targetId]);

  const {
    data: scans,
    error: scansError,
    isLoading: areScansLoading,
    reload: reloadScans,
  } = useAsync(() => listScansForTarget(targetId!), [targetId]);

  const [isTriggering, setIsTriggering] = useState(false);
  const [triggerError, setTriggerError] = useState<string | null>(null);

  const canTriggerScan = user?.role === "admin" || user?.role === "analyst";

  async function handleTriggerScan() {
    setTriggerError(null);
    setIsTriggering(true);
    try {
      await createScan(targetId!);
      reloadScans();
    } catch (err) {
      setTriggerError(err instanceof ApiError ? err.message : "Could not start a scan.");
    } finally {
      setIsTriggering(false);
    }
  }

  return (
    <Layout>
      {isTargetLoading && <div className="empty-state">Loading target…</div>}
      {targetError && <div className="empty-state">{targetError}</div>}

      {target && (
        <>
          <div className="page-header">
            <div>
              <h1>{target.label}</h1>
              <p className="page-subtitle mono">{target.url}</p>
            </div>
            {canTriggerScan && (
              <button className="btn btn-primary" onClick={handleTriggerScan} disabled={isTriggering}>
                {isTriggering ? "Starting…" : "Scan now"}
              </button>
            )}
          </div>

          {triggerError && <div className="form-error">{triggerError}</div>}

          <h3 style={{ marginBottom: 8 }}>Scan history</h3>
          <div className="panel">
            {areScansLoading && <div className="empty-state">Loading scan history…</div>}
            {scansError && <div className="empty-state">{scansError}</div>}
            {scans && scans.length === 0 && (
              <div className="empty-state">
                No scans yet.{" "}
                {canTriggerScan ? "Run one above to see results here." : "Ask an admin or analyst to run one."}
              </div>
            )}
            {scans && scans.length > 0 && (
              <div className="ledger">
                {scans.map((scan) => (
                  <div
                    key={scan.id}
                    className="ledger-row"
                    style={{ cursor: "pointer" }}
                    onClick={() => navigate(`/scans/${scan.id}`)}
                  >
                    <span className="ledger-timestamp">
                      {new Date(scan.created_at).toLocaleString()}
                    </span>
                    <ScanStatusPill status={scan.status} />
                    <span className="ledger-target">
                      {scan.error_message ?? `scan ${scan.id.slice(0, 8)}`}
                    </span>
                    <span className="ledger-arrow">view →</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </Layout>
  );
}
