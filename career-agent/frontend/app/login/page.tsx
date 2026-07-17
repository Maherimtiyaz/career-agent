"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { login } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true); setError("");
    try { await login(email, password); router.push("/dashboard"); }
    catch { setError("Invalid email or password"); }
    finally { setLoading(false); }
  }

  const inputStyle = { width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid var(--border)", background: "var(--bg-3)", color: "var(--text)", fontSize: 14, outline: "none", transition: "border-color 0.15s" };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--bg)" }}>
      <div style={{ position: "absolute", inset: 0, background: "radial-gradient(ellipse at 50% 0%, rgba(124,111,255,0.08) 0%, transparent 70%)", pointerEvents: "none" }} />
      <div style={{ width: "100%", maxWidth: 400, padding: "0 24px", position: "relative" }}>
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div style={{ width: 44, height: 44, borderRadius: 14, background: "linear-gradient(135deg, var(--primary), #a78bfa)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20, margin: "0 auto 16px" }}>✦</div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text)", margin: 0, letterSpacing: "-0.02em" }}>Welcome back</h1>
          <p style={{ color: "var(--text-2)", fontSize: 14, marginTop: 6 }}>Sign in to Career Agent</p>
        </div>
        <div style={{ background: "var(--bg-2)", border: "1px solid var(--border)", borderRadius: 16, padding: 28 }}>
          {error && <div style={{ marginBottom: 16, padding: "10px 12px", borderRadius: 8, background: "var(--danger-dim)", color: "var(--danger)", fontSize: 13, border: "1px solid rgba(248,113,113,0.2)" }}>{error}</div>}
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "var(--text-2)", marginBottom: 6 }}>Email</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)} style={inputStyle} placeholder="you@example.com" required
                onFocus={e => (e.target as HTMLInputElement).style.borderColor = "var(--primary)"}
                onBlur={e => (e.target as HTMLInputElement).style.borderColor = "var(--border)"} />
            </div>
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "var(--text-2)", marginBottom: 6 }}>Password</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} style={inputStyle} placeholder="••••••••" required
                onFocus={e => (e.target as HTMLInputElement).style.borderColor = "var(--primary)"}
                onBlur={e => (e.target as HTMLInputElement).style.borderColor = "var(--border)"} />
            </div>
            <button type="submit" disabled={loading} style={{ padding: "11px", borderRadius: 10, background: "var(--primary)", color: "white", fontSize: 14, fontWeight: 600, border: "none", cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.7 : 1, marginTop: 4, transition: "opacity 0.15s", letterSpacing: "-0.01em" }}>
              {loading ? "Signing in..." : "Sign in →"}
            </button>
          </form>
        </div>
        <p style={{ textAlign: "center", fontSize: 13, color: "var(--text-3)", marginTop: 20 }}>
          No account?{" "}<Link href="/register" style={{ color: "var(--primary)", textDecoration: "none" }}>Create one free</Link>
        </p>
      </div>
    </div>
  );
}
