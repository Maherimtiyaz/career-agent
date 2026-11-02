"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getMe } from "@/lib/auth";
import api from "@/lib/api";
import type { User } from "@/types";

const fields = [
  { key: "full_name", label: "Full Name", placeholder: "Your name", type: "text" },
  { key: "college", label: "College / University", placeholder: "VGU, Jaipur", type: "text" },
  { key: "graduation_year", label: "Graduation Year", placeholder: "2028", type: "text" },
  { key: "location", label: "Location", placeholder: "Jaipur, India", type: "text" },
  { key: "github_url", label: "GitHub URL", placeholder: "https://github.com/username", type: "url" },
  { key: "linkedin_url", label: "LinkedIn URL", placeholder: "https://linkedin.com/in/username", type: "url" },
] as const;

export default function ProfilePage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [form, setForm] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem("access_token")) { router.push("/login"); return; }
    getMe().then(u => {
      setUser(u);
      setForm({
        full_name: u.full_name ?? "",
        bio: (u as unknown as Record<string,string>).bio ?? "",
        skills: (u as unknown as Record<string,string>).skills ?? "",
        target_roles: (u as unknown as Record<string,string>).target_roles ?? "",
        location: (u as unknown as Record<string,string>).location ?? "",
        github_url: (u as unknown as Record<string,string>).github_url ?? "",
        linkedin_url: (u as unknown as Record<string,string>).linkedin_url ?? "",
        college: (u as unknown as Record<string,string>).college ?? "",
        graduation_year: (u as unknown as Record<string,string>).graduation_year ?? "",
      });
    }).catch(() => router.push("/login"));
  }, [router]);

  async function handleSave() {
    setSaving(true);
    setSaved(false);
    try {
      await api.patch("/auth/me", form);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } finally {
      setSaving(false);
    }
  }

  const inputStyle = {
    width: "100%", padding: "9px 12px", borderRadius: 10,
    border: "1px solid var(--border)", background: "var(--bg-3)",
    color: "var(--text)", fontSize: 13, outline: "none", transition: "border-color 0.15s",
  };

  return (
    <div style={{ padding: "32px 40px", maxWidth: 640 }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, letterSpacing: "-0.02em" }}>Profile</h1>
        <p style={{ color: "var(--text-2)", fontSize: 13, marginTop: 4 }}>
          Your profile helps AI Picks match better opportunities to you
        </p>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 32, padding: "20px 24px", borderRadius: 14, border: "1px solid var(--border)", background: "var(--bg-2)" }}>
        <div style={{ width: 52, height: 52, borderRadius: 16, background: "linear-gradient(135deg, var(--primary), #a78bfa)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20, fontWeight: 700, color: "white", flexShrink: 0 }}>
          {(form.full_name || user?.email || "?")[0].toUpperCase()}
        </div>
        <div>
          <div style={{ fontWeight: 600, fontSize: 15 }}>{form.full_name || "No name set"}</div>
          <div style={{ fontSize: 12, color: "var(--text-2)", marginTop: 2 }}>{user?.email}</div>
          {form.college && <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 2 }}>{form.college}{form.graduation_year ? " · " + form.graduation_year : ""}</div>}
        </div>
      </div>

      <div style={{ background: "var(--bg-2)", border: "1px solid var(--border)", borderRadius: 16, padding: 24, marginBottom: 16 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-3)", letterSpacing: "0.05em", marginBottom: 16, textTransform: "uppercase" }}>Basic Info</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          {fields.map(f => (
            <div key={f.key}>
              <label style={{ display: "block", fontSize: 11, fontWeight: 500, color: "var(--text-2)", marginBottom: 5 }}>{f.label}</label>
              <input
                type={f.type}
                value={form[f.key] ?? ""}
                onChange={e => setForm(p => ({ ...p, [f.key]: e.target.value }))}
                placeholder={f.placeholder}
                style={inputStyle}
                onFocus={e => (e.target as HTMLInputElement).style.borderColor = "var(--primary)"}
                onBlur={e => (e.target as HTMLInputElement).style.borderColor = "var(--border)"}
              />
            </div>
          ))}
        </div>
      </div>

      <div style={{ background: "var(--bg-2)", border: "1px solid var(--border)", borderRadius: 16, padding: 24, marginBottom: 16 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-3)", letterSpacing: "0.05em", marginBottom: 16, textTransform: "uppercase" }}>Career Focus</div>
        <div style={{ display: "grid", gap: 12 }}>
          <div>
            <label style={{ display: "block", fontSize: 11, fontWeight: 500, color: "var(--text-2)", marginBottom: 5 }}>
              Skills <span style={{ color: "var(--text-3)" }}>· comma separated</span>
            </label>
            <input
              value={form.skills ?? ""}
              onChange={e => setForm(p => ({ ...p, skills: e.target.value }))}
              placeholder="Python, FastAPI, PostgreSQL, Docker, React"
              style={inputStyle}
              onFocus={e => (e.target as HTMLInputElement).style.borderColor = "var(--primary)"}
              onBlur={e => (e.target as HTMLInputElement).style.borderColor = "var(--border)"}
            />
            {form.skills && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 8 }}>
                {form.skills.split(",").map(s => s.trim()).filter(Boolean).map(s => (
                  <span key={s} style={{ fontSize: 10, padding: "2px 8px", borderRadius: 4, background: "var(--primary-dim)", color: "var(--primary)", border: "1px solid var(--primary-glow)" }}>{s}</span>
                ))}
              </div>
            )}
          </div>
          <div>
            <label style={{ display: "block", fontSize: 11, fontWeight: 500, color: "var(--text-2)", marginBottom: 5 }}>
              Target Roles <span style={{ color: "var(--text-3)" }}>· comma separated</span>
            </label>
            <input
              value={form.target_roles ?? ""}
              onChange={e => setForm(p => ({ ...p, target_roles: e.target.value }))}
              placeholder="Backend Intern, SWE Intern, Open Source Fellow"
              style={inputStyle}
              onFocus={e => (e.target as HTMLInputElement).style.borderColor = "var(--primary)"}
              onBlur={e => (e.target as HTMLInputElement).style.borderColor = "var(--border)"}
            />
          </div>
          <div>
            <label style={{ display: "block", fontSize: 11, fontWeight: 500, color: "var(--text-2)", marginBottom: 5 }}>Bio</label>
            <textarea
              value={form.bio ?? ""}
              onChange={e => setForm(p => ({ ...p, bio: e.target.value }))}
              placeholder="BCA student at VGU, Jaipur. Building open-source tools for students."
              rows={3}
              style={{ ...inputStyle, resize: "vertical", fontFamily: "inherit" }}
              onFocus={e => (e.target as HTMLTextAreaElement).style.borderColor = "var(--primary)"}
              onBlur={e => (e.target as HTMLTextAreaElement).style.borderColor = "var(--border)"}
            />
          </div>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <button
          onClick={handleSave}
          disabled={saving}
          style={{ padding: "10px 24px", borderRadius: 10, background: "var(--primary)", color: "white", fontSize: 13, fontWeight: 600, border: "none", cursor: saving ? "not-allowed" : "pointer", opacity: saving ? 0.7 : 1 }}>
          {saving ? "Saving..." : "Save Profile"}
        </button>
        {saved && <span style={{ fontSize: 12, color: "var(--success)" }}>✓ Profile saved</span>}
      </div>
    </div>
  );
}