"use client";
import { useState } from "react";
import api from "@/lib/api";

export default function ImportPage() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ inserted: number; skipped: number } | null>(null);
  const [error, setError] = useState("");

  async function handleImport() {
    if (!url.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await api.post("/sheet/import", { sheet_url: url });
      setResult(res.data);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Import failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-8 max-w-2xl">
      <h1 className="text-2xl font-bold mb-1">Import from Google Sheet</h1>
      <p className="text-sm text-[hsl(var(--muted-foreground))] mb-8">
        Sync your personal opportunity tracker from a public Google Sheet. Your sheet must be shared as Anyone with the link can view.
      </p>

      <div className="p-6 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] mb-6">
        <h2 className="font-semibold text-sm mb-3">Required column headers</h2>
        <div className="grid grid-cols-2 gap-2 text-xs text-[hsl(var(--muted-foreground))]">
          {["company (required)", "role (required)", "job_link", "hr_contact", "status", "date_applied", "notes"].map(col => (
            <div key={col} className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[hsl(var(--primary))] flex-shrink-0" />
              {col}
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-3">
        <input
          value={url} onChange={e => setUrl(e.target.value)}
          placeholder="https://docs.google.com/spreadsheets/d/..."
          className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
        />
        <button onClick={handleImport} disabled={loading || !url.trim()}
          className="w-full py-2 rounded-lg bg-[hsl(var(--primary))] text-white text-sm font-medium hover:opacity-90 transition disabled:opacity-50">
          {loading ? "Importing..." : "Import Sheet"}
        </button>
      </div>

      {result && (
        <div className="mt-4 p-4 rounded-lg bg-green-50 border border-green-200 text-sm text-green-700">
          ✓ Import complete — {result.inserted} new rows added, {result.skipped} skipped (already exist)
        </div>
      )}
      {error && (
        <div className="mt-4 p-4 rounded-lg bg-red-50 border border-red-200 text-sm text-red-600">
          {error}
        </div>
      )}
    </div>
  );
}
