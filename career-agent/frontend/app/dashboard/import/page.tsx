"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";

interface ScrapeResult {
  source: string;
  inserted: number;
  error?: string;
}

export default function ImportPage() {
  const qc = useQueryClient();
  const [url, setUrl] = useState("");
  const [sheetLoading, setSheetLoading] = useState(false);
  const [sheetResult, setSheetResult] = useState<{ inserted: number; skipped: number } | null>(null);
  const [sheetError, setSheetError] = useState("");
  const [scrapeResults, setScrapeResults] = useState<ScrapeResult[] | null>(null);

  const scrapeMutation = useMutation({
    mutationFn: () => api.post("/ingestion/run?source=all"),
    onSuccess: (res) => {
      setScrapeResults(res.data.results);
      qc.invalidateQueries({ queryKey: ["opportunities"] });
      qc.invalidateQueries({ queryKey: ["analytics"] });
      qc.invalidateQueries({ queryKey: ["ai-recommendations"] });
    },
  });

  async function handleSheetImport() {
    if (!url.trim()) return;
    setSheetLoading(true);
    setSheetError("");
    setSheetResult(null);
    try {
      const res = await api.post("/sheet/import", { sheet_url: url });
      setSheetResult(res.data);
      qc.invalidateQueries({ queryKey: ["applications"] });
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setSheetError(msg ?? "Import failed");
    } finally {
      setSheetLoading(false);
    }
  }

  const totalInserted = scrapeResults?.reduce((a, r) => a + (r.inserted ?? 0), 0) ?? 0;

  return (
    <div style={{ padding: "32px 40px", maxWidth: 720 }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, letterSpacing: "-0.02em" }}>Data Sources</h1>
        <p style={{ color: "var(--text-2)", fontSize: 13, marginTop: 4 }}>Refresh live data or import your personal tracker</p>
      </div>

      <div style={{ background: "var(--bg-2)", border: "1px solid var(--border)", borderRadius: 16, padding: 24, marginBottom: 16 }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16 }}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 6 }}>Live Platform Scrapers</div>
            <p style={{ fontSize: 12, color: "var(--text-2)", margin: 0, lineHeight: 1.6 }}>
              Fetch fresh opportunities from GSoC, YC Jobs (HN Who's Hiring), MLH Fellowship and Devfolio.
              Runs automatically every 24 hours. Click to trigger manually.
            </p>
            <div style={{ display: "flex", gap: 6, marginTop: 12, flexWrap: "wrap" }}>
              {["GSoC", "YC Jobs", "MLH", "Devfolio"].map(s => (
                <span key={s} style={{ fontSize: 10, padding: "3px 8px", borderRadius: 4, background: "var(--primary-dim)", color: "var(--primary)", border: "1px solid var(--primary-glow)" }}>{s}</span>
              ))}
            </div>
          </div>
          <button
            onClick={() => { setScrapeResults(null); scrapeMutation.mutate(); }}
            disabled={scrapeMutation.isPending}
            style={{ padding: "9px 18px", borderRadius: 10, background: "var(--primary)", color: "white", fontSize: 13, fontWeight: 500, border: "none", cursor: scrapeMutation.isPending ? "not-allowed" : "pointer", opacity: scrapeMutation.isPending ? 0.7 : 1, whiteSpace: "nowrap", flexShrink: 0 }}>
            {scrapeMutation.isPending ? "Scraping..." : "↻ Refresh Now"}
          </button>
        </div>

        {scrapeResults && (
          <div style={{ marginTop: 16, padding: "12px 16px", borderRadius: 10, background: totalInserted > 0 ? "var(--success-dim)" : "var(--bg-3)", border: "1px solid " + (totalInserted > 0 ? "rgba(52,211,153,0.2)" : "var(--border)") }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: totalInserted > 0 ? "var(--success)" : "var(--text-2)", marginBottom: 8 }}>
              {totalInserted > 0 ? ✓ Added  new opportunities : "✓ All sources up to date"}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 6 }}>
              {scrapeResults.map(r => (
                <div key={r.source} style={{ fontSize: 11, color: "var(--text-2)", display: "flex", justifyContent: "space-between", padding: "4px 8px", borderRadius: 6, background: "rgba(255,255,255,0.04)" }}>
                  <span>{r.source}</span>
                  <span style={{ color: r.error ? "var(--danger)" : r.inserted > 0 ? "var(--success)" : "var(--text-3)" }}>
                    {r.error ? "error" : "+" + r.inserted}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div style={{ background: "var(--bg-2)", border: "1px solid var(--border)", borderRadius: 16, padding: 24 }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 6 }}>Import from Google Sheet</div>
        <p style={{ fontSize: 12, color: "var(--text-2)", margin: "0 0 16px", lineHeight: 1.6 }}>
          Sync your personal application tracker. Sheet must be shared as Anyone with the link can view.
          Required columns: <strong style={{ color: "var(--text)" }}>company</strong>, <strong style={{ color: "var(--text)" }}>role</strong>.
          Optional: job_link, hr_contact, status, date_applied, notes.
        </p>

        <div style={{ display: "flex", gap: 8 }}>
          <input
            value={url} onChange={e => setUrl(e.target.value)}
            placeholder="https://docs.google.com/spreadsheets/d/..."
            style={{ flex: 1, padding: "9px 14px", borderRadius: 10, border: "1px solid var(--border)", background: "var(--bg-3)", color: "var(--text)", fontSize: 13, outline: "none" }}
            onFocus={e => (e.target as HTMLInputElement).style.borderColor = "var(--primary)"}
            onBlur={e => (e.target as HTMLInputElement).style.borderColor = "var(--border)"} />
          <button
            onClick={handleSheetImport}
            disabled={sheetLoading || !url.trim()}
            style={{ padding: "9px 18px", borderRadius: 10, background: "var(--primary)", color: "white", fontSize: 13, fontWeight: 500, border: "none", cursor: sheetLoading || !url.trim() ? "not-allowed" : "pointer", opacity: sheetLoading || !url.trim() ? 0.6 : 1, whiteSpace: "nowrap" }}>
            {sheetLoading ? "Importing..." : "Import"}
          </button>
        </div>

        {sheetResult && (
          <div style={{ marginTop: 12, padding: "10px 14px", borderRadius: 8, background: "var(--success-dim)", border: "1px solid rgba(52,211,153,0.2)", fontSize: 12, color: "var(--success)" }}>
            ✓ {sheetResult.inserted} rows added, {sheetResult.skipped} skipped
          </div>
        )}
        {sheetError && (
          <div style={{ marginTop: 12, padding: "10px 14px", borderRadius: 8, background: "var(--danger-dim)", border: "1px solid rgba(248,113,113,0.2)", fontSize: 12, color: "var(--danger)" }}>
            {sheetError}
          </div>
        )}
      </div>
    </div>
  );
}
