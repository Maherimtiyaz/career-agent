"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Opportunity } from "@/types";

export default function OpportunitiesPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [source, setSource] = useState("");
  const [page, setPage] = useState(0);
  const [saving, setSaving] = useState<string | null>(null);
  const limit = 20;

  const { data, isLoading } = useQuery({
    queryKey: ["opportunities", search, source, page],
    queryFn: async () => {
      const p = new URLSearchParams({ limit: String(limit), skip: String(page * limit) });
      if (search) p.set("search", search);
      if (source) p.set("source", source);
      const r = await api.get<Opportunity[]>("/opportunities?" + p.toString());
      return r.data;
    },
  });

  const applyMutation = useMutation({
    mutationFn: ({ opp, status }: { opp: Opportunity; status: string }) =>
      api.post("/applications", { company: opp.organization, role: opp.title, job_link: opp.url, status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["applications"] }),
  });

  async function handleAction(opp: Opportunity, status: string) {
    setSaving(opp.id + status);
    try { await applyMutation.mutateAsync({ opp, status }); }
    catch { /* already tracked */ }
    finally { setSaving(null); }
  }

  const tagBadge = (tag: string) => (
    <span key={tag} style={{ fontSize: 10, padding: "2px 7px", borderRadius: 4, background: "rgba(255,255,255,0.06)", color: "var(--text-3)", border: "1px solid var(--border)" }}>{tag}</span>
  );

  return (
    <div style={{ padding: "32px 40px" }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, letterSpacing: "-0.02em" }}>Opportunities</h1>
        <p style={{ color: "var(--text-2)", fontSize: 13, marginTop: 4 }}>Browse and apply to 2000+ remote positions</p>
      </div>

      <div style={{ display: "flex", gap: 10, marginBottom: 20 }}>
        <input value={search} onChange={e => { setSearch(e.target.value); setPage(0); }} placeholder="Search roles, companies..."
          style={{ flex: 1, padding: "9px 14px", borderRadius: 10, border: "1px solid var(--border)", background: "var(--bg-2)", color: "var(--text)", fontSize: 13, outline: "none" }}
          onFocus={e => (e.target as HTMLInputElement).style.borderColor = "var(--primary)"}
          onBlur={e => (e.target as HTMLInputElement).style.borderColor = "var(--border)"} />
        <select value={source} onChange={e => { setSource(e.target.value); setPage(0); }}
          style={{ padding: "9px 12px", borderRadius: 10, border: "1px solid var(--border)", background: "var(--bg-2)", color: "var(--text-2)", fontSize: 13, outline: "none" }}>
          <option value="">All sources</option>
          <option value="remote_jobs">Remote Jobs</option>
          <option value="curated">Curated</option>
          <option value="google_sheet">Google Sheet</option>
        </select>
      </div>

      {isLoading ? (
        <div style={{ display: "grid", gap: 8 }}>
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} style={{ height: 76, borderRadius: 12, background: "var(--bg-2)", border: "1px solid var(--border)", animation: "pulse 1.5s infinite" }} />
          ))}
        </div>
      ) : (
        <>
          <div style={{ fontSize: 11, color: "var(--text-3)", marginBottom: 12 }}>{data?.length ?? 0} results · page {page + 1}</div>
          <div style={{ display: "grid", gap: 6 }}>
            {data?.map(opp => (
              <div key={opp.id} style={{ padding: "14px 18px", borderRadius: 12, border: "1px solid var(--border)", background: "var(--bg-2)", display: "flex", alignItems: "center", gap: 16, transition: "border-color 0.15s" }}
                onMouseEnter={e => (e.currentTarget as HTMLElement).style.borderColor = "var(--border-hover)"}
                onMouseLeave={e => (e.currentTarget as HTMLElement).style.borderColor = "var(--border)"}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                    <a href={opp.url} target="_blank" rel="noopener noreferrer"
                      style={{ fontSize: 13, fontWeight: 500, color: "var(--text)", textDecoration: "none" }}
                      onMouseEnter={e => (e.currentTarget as HTMLElement).style.color = "var(--primary)"}
                      onMouseLeave={e => (e.currentTarget as HTMLElement).style.color = "var(--text)"}>
                      {opp.title}
                    </a>
                    {opp.is_remote && <span style={{ fontSize: 10, padding: "1px 6px", borderRadius: 4, background: "var(--primary-dim)", color: "var(--primary)", border: "1px solid var(--primary-glow)" }}>Remote</span>}
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 12, color: "var(--text-2)" }}>{opp.organization}</span>
                    {opp.stipend && <span style={{ fontSize: 11, color: "var(--success)" }}>· {opp.stipend}</span>}
                    {opp.location && <span style={{ fontSize: 11, color: "var(--text-3)" }}>· {opp.location}</span>}
                    <div style={{ display: "flex", gap: 4 }}>
                      {opp.tags?.split(",").slice(0, 2).map(t => t.trim()).filter(t => t && !t.startsWith("email:")).map(tagBadge)}
                    </div>
                  </div>
                </div>
                <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
                  <button onClick={() => handleAction(opp, "saved")} disabled={saving === opp.id + "saved"}
                    style={{ padding: "6px 12px", borderRadius: 8, border: "1px solid var(--border)", background: "transparent", color: "var(--text-2)", fontSize: 12, cursor: "pointer", transition: "all 0.15s" }}
                    onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = "var(--primary)"; (e.currentTarget as HTMLElement).style.color = "var(--primary)"; }}
                    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border)"; (e.currentTarget as HTMLElement).style.color = "var(--text-2)"; }}>
                    {saving === opp.id + "saved" ? "..." : "Save"}
                  </button>
                  <button onClick={() => handleAction(opp, "applied")} disabled={saving === opp.id + "applied"}
                    style={{ padding: "6px 12px", borderRadius: 8, border: "none", background: "var(--primary)", color: "white", fontSize: 12, cursor: "pointer", fontWeight: 500, transition: "opacity 0.15s" }}
                    onMouseEnter={e => (e.currentTarget as HTMLElement).style.opacity = "0.85"}
                    onMouseLeave={e => (e.currentTarget as HTMLElement).style.opacity = "1"}>
                    {saving === opp.id + "applied" ? "..." : "Applied ✓"}
                  </button>
                </div>
              </div>
            ))}
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 20 }}>
            <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}
              style={{ padding: "8px 16px", borderRadius: 8, border: "1px solid var(--border)", background: "transparent", color: "var(--text-2)", fontSize: 13, cursor: page === 0 ? "not-allowed" : "pointer", opacity: page === 0 ? 0.4 : 1 }}>
              ← Previous
            </button>
            <button onClick={() => setPage(p => p + 1)} disabled={(data?.length ?? 0) < limit}
              style={{ padding: "8px 16px", borderRadius: 8, border: "1px solid var(--border)", background: "transparent", color: "var(--text-2)", fontSize: 13, cursor: (data?.length ?? 0) < limit ? "not-allowed" : "pointer", opacity: (data?.length ?? 0) < limit ? 0.4 : 1 }}>
              Next →
            </button>
          </div>
        </>
      )}
    </div>
  );
}
