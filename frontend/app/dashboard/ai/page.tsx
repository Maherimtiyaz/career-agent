"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Opportunity } from "@/types";

export default function AIPage() {
  const qc = useQueryClient();
  const [saving, setSaving] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["ai-recommendations"],
    queryFn: async () => (await api.get<Opportunity[]>("/ai/recommendations?limit=20")).data,
  });

  const applyMutation = useMutation({
    mutationFn: ({ opp, status }: { opp: Opportunity; status: string }) =>
      api.post("/applications", { company: opp.organization, role: opp.title, job_link: opp.url, status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["applications"] }),
  });

  async function handleAction(opp: Opportunity, status: string) {
    setSaving(opp.id + status);
    try { await applyMutation.mutateAsync({ opp, status }); }
    catch { }
    finally { setSaving(null); }
  }

  return (
    <div style={{ padding: "32px 40px", maxWidth: 860 }}>
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
          <div style={{ width: 32, height: 32, borderRadius: 10, background: "var(--primary-dim)", border: "1px solid var(--primary-glow)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--primary)", fontSize: 14 }}>✦</div>
          <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, letterSpacing: "-0.02em" }}>AI Picks</h1>
        </div>
        <p style={{ color: "var(--text-2)", fontSize: 13 }}>
          Top opportunities matched to a student tech profile · keyword scoring · embeddings coming in Phase 11
        </p>
      </div>

      <div style={{ padding: "12px 16px", borderRadius: 10, border: "1px solid var(--primary-glow)", background: "var(--primary-dim)", marginBottom: 24, fontSize: 12, color: "var(--text-2)", display: "flex", gap: 10, alignItems: "flex-start" }}>
        <span style={{ color: "var(--primary)", fontSize: 14, marginTop: 1 }}>ℹ</span>
        <div>
          <strong style={{ color: "var(--primary)" }}>How scoring works:</strong> Each opportunity is scored by matching keywords like python, backend, intern, remote, fellowship, open source against the title, organization and tags. Curated sources and paid stipends get bonus points.
          Full semantic AI matching with your actual resume and skills profile is coming in Phase 11.
        </div>
      </div>

      {isLoading ? (
        <div style={{ display: "grid", gap: 8 }}>
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} style={{ height: 80, borderRadius: 12, background: "var(--bg-2)", border: "1px solid var(--border)", opacity: 1 - i * 0.1 }} />
          ))}
        </div>
      ) : (
        <div style={{ display: "grid", gap: 6 }}>
          {data?.map((opp, idx) => (
            <div key={opp.id} style={{ padding: "14px 18px", borderRadius: 12, border: idx < 3 ? "1px solid var(--primary-glow)" : "1px solid var(--border)", background: idx < 3 ? "rgba(124,111,255,0.04)" : "var(--bg-2)", display: "flex", alignItems: "center", gap: 16, transition: "border-color 0.15s" }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: idx < 3 ? "var(--primary)" : "var(--text-3)", width: 20, textAlign: "center", flexShrink: 0 }}>#{idx + 1}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                  <a href={opp.url} target="_blank" rel="noopener noreferrer"
                    style={{ fontSize: 13, fontWeight: 500, color: "var(--text)", textDecoration: "none" }}
                    onMouseEnter={e => (e.currentTarget as HTMLElement).style.color = "var(--primary)"}
                    onMouseLeave={e => (e.currentTarget as HTMLElement).style.color = "var(--text)"}>
                    {opp.title}
                  </a>
                  {opp.is_remote && <span style={{ fontSize: 10, padding: "1px 6px", borderRadius: 4, background: "var(--primary-dim)", color: "var(--primary)", border: "1px solid var(--primary-glow)" }}>Remote</span>}
                  {idx < 3 && <span style={{ fontSize: 10, padding: "1px 6px", borderRadius: 4, background: "var(--success-dim)", color: "var(--success)", border: "1px solid rgba(52,211,153,0.2)" }}>Top Pick</span>}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 12, color: "var(--text-2)" }}>{opp.organization}</span>
                  {opp.stipend && <span style={{ fontSize: 11, color: "var(--success)" }}>· {opp.stipend}</span>}
                  {opp.deadline && <span style={{ fontSize: 11, color: "var(--warning)" }}>· Deadline: {opp.deadline}</span>}
                </div>
              </div>
              <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
                <button onClick={() => handleAction(opp, "saved")} disabled={saving === opp.id + "saved"}
                  style={{ padding: "6px 12px", borderRadius: 8, border: "1px solid var(--border)", background: "transparent", color: "var(--text-2)", fontSize: 12, cursor: "pointer" }}>
                  {saving === opp.id + "saved" ? "..." : "Save"}
                </button>
                <button onClick={() => handleAction(opp, "applied")} disabled={saving === opp.id + "applied"}
                  style={{ padding: "6px 12px", borderRadius: 8, border: "none", background: "var(--primary)", color: "white", fontSize: 12, cursor: "pointer", fontWeight: 500 }}>
                  {saving === opp.id + "applied" ? "..." : "Applied ✓"}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
