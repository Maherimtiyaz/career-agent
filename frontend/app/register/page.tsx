"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { register, login } from "@/lib/auth";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true); setError("");
    try { await register(email, password, fullName); await login(email, password); router.push("/dashboard"); }
    catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Registration failed");
    } finally { setLoading(false); }
  }

  const inputStyle = { width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid var(--border)", background: "var(--bg-3)", color: "var(--text)", fontSize: 14, outline: "none", transition: "border-color 0.15s" };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--bg)" }}>
      <div style={{ position: "absolute", inset: 0, background: "radial-gradient(ellipse at 50% 0%, rgba(124,111,255,0.08) 0%, transparent 70%)", pointerEvents: "none" }} />
      <div style={{ width: "100%", maxWidth: 400, padding: "0 24px", position: "relative" }}>
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div style={{ width: 44, height: 44, borderRadius: 14, background: "linear-gradient(135deg, var(--primary), #a78bfa)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20, margin: "0 auto 16px" }}>✦</div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text)", margin: 0, letterSpacing: "-0.02em" }}>Create your account</h1>
          <p style={{ color: "var(--text-2)", fontSize: 14, marginTop: 6 }}>Free for students forever</p>
        </div>
        <div style={{ background: "var(--bg-2)", border: "1px solid var(--border)", borderRadius: 16, padding: 28 }}>
          {error && <div style={{ marginBottom: 16, padding: "10px 12px", borderRadius: 8, background: "var(--danger-dim)", color: "var(--danger)", fontSize: 13, border: "1px solid rgba(248,113,113,0.2)" }}>{error}</div>}
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {[{ label: "Full name", type: "text", value: fullName, set: setFullName, ph: "Your name", req: false },
              { label: "Email", type: "email", value: email, set: setEmail, ph: "you@example.com", req: true },
              { label: "Password", type: "password", value: password, set: setPassword, ph: "Min 6 characters", req: true }
            ].map(f => (
              <div key={f.label}>
                <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "var(--text-2)", marginBottom: 6 }}>{f.label}</label>
                <input type={f.type} value={f.value} onChange={e => f.set(e.target.value)} style={inputStyle} placeholder={f.ph} required={f.req}
                  onFocus={e => (e.target as HTMLInputElement).style.borderColor = "var(--primary)"}
                  onBlur={e => (e.target as HTMLInputElement).style.borderColor = "var(--border)"} />
              </div>
            ))}
            <button type="submit" disabled={loading} style={{ padding: "11px", borderRadius: 10, background: "var(--primary)", color: "white", fontSize: 14, fontWeight: 600, border: "none", cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.7 : 1, marginTop: 4, transition: "opacity 0.15s" }}>
              {loading ? "Creating account..." : "Get started →"}
            </button>
          </form>
        </div>
        <p style={{ textAlign: "center", fontSize: 13, color: "var(--text-3)", marginTop: 20 }}>
          Already have an account?{" "}<Link href="/login" style={{ color: "var(--primary)", textDecoration: "none" }}>Sign in</Link>
        </p>
      </div>
    </div>
  );
}
