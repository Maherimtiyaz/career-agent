"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Application } from "@/types";

const STATUS_COLORS: Record<string, string> = {
  applied: "#60a5fa",
  interviewing: "#fbbf24",
  offer: "#34d399",
  rejected: "#f87171",
  saved: "#9090a8",
};

interface Draft {
  subject: string;
  body: string;
  to: string | null;
}

function EmailModal({ draft, onClose }: { draft: Draft; onClose: () => void }) {
  const [copied, setCopied] = useState(false);

  function copyAll() {
    const text = `To: ${draft.to || "HR Contact"}\nSubject: ${draft.subject}\n\n${draft.body}`;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function openMailto() {
    const mailto = `mailto:${draft.to || ""}?subject=${encodeURIComponent(draft.subject)}&body=${encodeURIComponent(draft.body)}`;
    window.open(mailto);
  }

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50, padding: 24 }}>
      <div style={{ background: "var(--bg-2)", border: "1px solid var(--border)", borderRadius: 16, width: "100%", maxWidth: 560, maxHeight: "85vh", overflow: "auto" }}>
        <div style={{ padding: "20px 24px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 600 }}>AI-drafted cold email</div>
            {draft.to && <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 2 }}>To: {draft.to}</div>}
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", color: "var(--text-3)", cursor: "pointer", fontSize: 18, lineHeight: 1 }}>×</button>
        </div>
        <div style={{ padding: "20px 24px" }}>
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 11, fontWeight: 500, color: "var(--text-3)", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em" }}>Subject</div>
            <div style={{ fontSize: 13, padding: "10px 12px", borderRadius: 8, background: "var(--bg-3)", border: "1px solid var(--border)", color: "var(--text)" }}>{draft.subject}</div>
          </div>
          <div>
            <div style={{ fontSize: 11, fontWeight: 500, color: "var(--text-3)", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em" }}>Body</div>
            <textarea
              defaultValue={draft.body}
              rows={12}
              style={{ width: "100%", padding: "10px 12px", borderRadius: 8, background: "var(--bg-3)", border: "1px solid var(--border)", color: "var(--text)", fontSize: 13, resize: "vertical", fontFamily: "inherit", outline: "none", lineHeight: 1.6 }}
            />
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
            <button onClick={openMailto} style={{ flex: 1, padding: "9px", borderRadius: 10, background: "var(--primary)", color: "white", fontSize: 13, fontWeight: 500, border: "none", cursor: "pointer" }}>
              Open in Mail App
            </button>
            <button onClick={copyAll} style={{ padding: "9px 16px", borderRadius: 10, border: "1px solid var(--border)", background: "transparent", color: "var(--text-2)", fontSize: 13, cursor: "pointer" }}>
              {copied ? "Copied!" : "Copy All"}
            </button>
          </div>
          <p style={{ fontSize: 11, color: "var(--text-3)", marginTop: 12, textAlign: "center" }}>
            Review and edit before sending. AI-generated — always personalise.
          </p>
        </div>
      </div>
    </div>
  );
}

export default function ApplicationsPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ company: "", role: "", job_link: "", hr_contact: "", status: "applied", notes: "" });
  const [draft, setDraft] = useState<Draft | null>(null);
  const [draftLoading, setDraftLoading] = useState<string | null>(null);

  const { data: apps, isLoading } = useQuery({
    queryKey: ["applications"],
    queryFn: async () => (await api.get<Application[]>("/applications")).data,
  });

  const addMutation = useMutation({
    mutationFn: (body: typeof form) => api.post("/applications", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["applications"] });
      setShowForm(false);
      setForm({ company: "", role: "", job_link: "", hr_contact: "", status: "applied", notes: "" });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => api.patch("/applications/" + id, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["applications"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete("/applications/" + id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["applications"] }),
  });

  async function handleDraftEmail(appId: string) {
    setDraftLoading(appId);
    try {
      const res = await api.post("/outreach/draft", { application_id: appId });
      setDraft(res.data);
    } catch {
      alert("Could not generate email. Make sure your profile has skills and bio filled in.");
    } finally {
      setDraftLoading(null);
    }
  }

  return (
    <div style={{ padding: "32px 40px" }}>
      {draft && <EmailModal draft={draft} onClose={() => setDraft(null)} />}

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, letterSpacing: "-0.02em" }}>My Applications</h1>
          <p style={{ color: "var(--text-2)", fontSize: 13, marginTop: 4 }}>Track and manage your job applications</p>
        </div>
        <button onClick={() => setShowForm(true)}
          style={{ padding: "9px 18px", borderRadius: 10, background: "var(--primary)", color: "white", fontSize: 13, fontWeight: 500, border: "none", cursor: "pointer" }}>
          + Add
        </button>
      </div>

      {showForm && (
        <div style={{ marginBottom: 20, padding: 20, borderRadius: 14, border: "1px solid var(--border)", background: "var(--bg-2)" }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 14 }}>New Application</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            {(["company", "role", "job_link", "hr_contact"] as const).map(f => (
              <input key={f} placeholder={f.replace("_", " ")} value={form[f]}
                onChange={e => setForm(p => ({ ...p, [f]: e.target.value }))}
                style={{ padding: "9px 12px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--bg-3)", color: "var(--text)", fontSize: 13, outline: "none" }}
              />
            ))}
            <select value={form.status} onChange={e => setForm(p => ({ ...p, status: e.target.value }))}
              style={{ padding: "9px 12px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--bg-3)", color: "var(--text)", fontSize: 13 }}>
              {["applied","interviewing","offer","rejected","saved"].map(s => <option key={s}>{s}</option>)}
            </select>
            <input placeholder="notes" value={form.notes} onChange={e => setForm(p => ({ ...p, notes: e.target.value }))}
              style={{ padding: "9px 12px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--bg-3)", color: "var(--text)", fontSize: 13, outline: "none" }}
            />
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            <button onClick={() => addMutation.mutate(form)}
              style={{ padding: "8px 18px", borderRadius: 8, background: "var(--primary)", color: "white", fontSize: 13, fontWeight: 500, border: "none", cursor: "pointer" }}>
              Save
            </button>
            <button onClick={() => setShowForm(false)}
              style={{ padding: "8px 14px", borderRadius: 8, border: "1px solid var(--border)", background: "transparent", color: "var(--text-2)", fontSize: 13, cursor: "pointer" }}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {isLoading ? (
        <div style={{ display: "grid", gap: 8 }}>
          {Array.from({ length: 4 }).map((_, i) => <div key={i} style={{ height: 52, borderRadius: 10, background: "var(--bg-2)", border: "1px solid var(--border)" }} />)}
        </div>
      ) : apps?.length === 0 ? (
        <div style={{ textAlign: "center", padding: "64px 0", color: "var(--text-3)" }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>◎</div>
          <div style={{ fontSize: 14, marginBottom: 4 }}>No applications yet</div>
          <div style={{ fontSize: 12 }}>Add one above or use Save/Applied on the Opportunities page</div>
        </div>
      ) : (
        <div style={{ borderRadius: 14, border: "1px solid var(--border)", overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "var(--bg-3)", borderBottom: "1px solid var(--border)" }}>
                {["Company","Role","Status","HR Contact","Actions"].map(h => (
                  <th key={h} style={{ padding: "10px 16px", textAlign: "left", fontSize: 11, fontWeight: 500, color: "var(--text-3)", letterSpacing: "0.03em" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {apps?.map((app, i) => (
                <tr key={app.id} style={{ borderBottom: i < (apps.length - 1) ? "1px solid var(--border)" : "none", background: "var(--bg-2)" }}
                  onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = "var(--bg-3)"}
                  onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = "var(--bg-2)"}>
                  <td style={{ padding: "12px 16px", fontWeight: 500 }}>{app.company}</td>
                  <td style={{ padding: "12px 16px", color: "var(--text-2)" }}>
                    {app.job_link
                      ? <a href={app.job_link} target="_blank" style={{ color: "var(--primary)", textDecoration: "none" }}>{app.role}</a>
                      : app.role}
                  </td>
                  <td style={{ padding: "12px 16px" }}>
                    <select value={app.status}
                      onChange={e => updateMutation.mutate({ id: app.id, status: e.target.value })}
                      style={{ fontSize: 11, fontWeight: 500, padding: "3px 8px", borderRadius: 6, border: "1px solid", background: "transparent", color: STATUS_COLORS[app.status] ?? "var(--text-2)", borderColor: STATUS_COLORS[app.status] ?? "var(--border)", cursor: "pointer" }}>
                      {["applied","interviewing","offer","rejected","saved"].map(s => <option key={s} style={{ background: "var(--bg-2)", color: "var(--text)" }}>{s}</option>)}
                    </select>
                  </td>
                  <td style={{ padding: "12px 16px", color: "var(--text-3)", fontSize: 12 }}>{app.hr_contact || "—"}</td>
                  <td style={{ padding: "12px 16px" }}>
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      <button
                        onClick={() => handleDraftEmail(app.id)}
                        disabled={draftLoading === app.id}
                        style={{ fontSize: 11, padding: "4px 10px", borderRadius: 6, border: "1px solid var(--primary-glow)", background: "var(--primary-dim)", color: "var(--primary)", cursor: "pointer", opacity: draftLoading === app.id ? 0.6 : 1 }}>
                        {draftLoading === app.id ? "..." : "✉ Draft Email"}
                      </button>
                      <button onClick={() => deleteMutation.mutate(app.id)}
                        style={{ fontSize: 11, color: "var(--text-3)", background: "none", border: "none", cursor: "pointer" }}
                        onMouseEnter={e => (e.currentTarget as HTMLElement).style.color = "var(--danger)"}
                        onMouseLeave={e => (e.currentTarget as HTMLElement).style.color = "var(--text-3)"}>
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}