import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { getScan, listScanFindings } from "../api/scans";
import type { Finding, Scan } from "../api/types";
import { categoryLabel, FindingCard } from "../components/FindingCard";
import { Layout } from "../components/Layout";
import { ScanStatusPill } from "../components/Pills";
import { ScopeBanner } from "../components/ScopeBanner";

const POLL_INTERVAL_MS = 3000;

export function ScanReportPage() {
  const { scanId } = useParams<{ scanId: string }>();
  const [scan, setScan] = useState<Scan | null>(null);
  const [findings, setFindings] = useState<Finding[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!scanId) return;
    let cancelled = false;
    let timeoutId: ReturnType<typeof setTimeout> | undefined;

    async function poll() {
      try {
        const [scanResult, findingsResult] = await Promise.all([
          getScan(scanId!),
          listScanFindings(scanId!),
        ]);
        if (cancelled) return;
        setScan(scanResult);
        setFindings(findingsResult);

        // Only queued/running scans need to keep polling -- a
        // completed or failed scan's state never changes again, so
        // stopping here avoids an indefinite background request loop
        // for every scan report page left open.
        if (scanResult.status === "queued" || scanResult.status === "running") {
          timeoutId = setTimeout(poll, POLL_INTERVAL_MS);
        }
      } catch {
        if (!cancelled) setError("Could not load this scan.");
      }
    }

    poll();

    return () => {
      cancelled = true;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [scanId]);

  const findingsByCategory = findings
    ? findings.reduce<Record<string, Finding[]>>((groups, finding) => {
        (groups[finding.category] ??= []).push(finding);
        return groups;
      }, {})
    : null;

  return (
    <Layout>
      {error && <div className="empty-state">{error}</div>}

      {!error && !scan && <div className="empty-state">Loading scan…</div>}

      {scan && (
        <>
          <div className="page-header">
            <div>
              <h1>Scan report</h1>
              <p className="page-subtitle mono">{scan.id}</p>
            </div>
            <ScanStatusPill status={scan.status} />
          </div>

          {scan.status === "failed" && scan.error_message && (
            <div className="form-error">{scan.error_message}</div>
          )}

          {(scan.status === "queued" || scan.status === "running") && (
            <div className="empty-state" style={{ marginBottom: 20 }}>
              {scan.status === "queued"
                ? "Waiting for the worker to pick this scan up…"
                : "Scan in progress — checking the target now…"}
            </div>
          )}

          {scan.status === "completed" && (
            <>
              <ScopeBanner />

              {findingsByCategory && Object.keys(findingsByCategory).length === 0 && (
                <div className="empty-state">No findings were produced by this scan.</div>
              )}

              {findingsByCategory &&
                Object.entries(findingsByCategory).map(([category, categoryFindings]) => (
                  <div className="finding-category-group" key={category}>
                    <h3 style={{ marginBottom: 8 }}>
                      {categoryLabel(category as Finding["category"])}
                    </h3>
                    {categoryFindings.map((finding) => (
                      <FindingCard key={finding.id} finding={finding} />
                    ))}
                  </div>
                ))}
            </>
          )}
        </>
      )}
    </Layout>
  );
}
