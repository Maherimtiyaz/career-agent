"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowRight, BriefcaseBusiness, Check, Compass, Sparkles } from "lucide-react";
import axios from "axios";
import { login, register } from "@/lib/auth";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await register(email, password, fullName);
      await login(email, password);
      router.push("/dashboard");
    } catch (requestError: unknown) {
      const detail = axios.isAxiosError(requestError)
        ? requestError.response?.data?.detail
        : undefined;
      setError(
        typeof detail === "string"
          ? detail
          : axios.isAxiosError(requestError) && !requestError.response
            ? "We couldn’t reach Career Agent. Check your connection and try again."
            : "We couldn’t create your account. Please check your details and try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-layout">
      <aside className="auth-aside">
        <Link className="auth-brand" href="/" aria-label="Career Agent home">
          <span className="brand-icon"><Sparkles size={17} aria-hidden="true" /></span>
          <span>Career Agent</span>
        </Link>
        <div className="auth-copy">
          <div className="eyebrow">A workspace for what&apos;s next</div>
          <h1>Make your<br />next move<br /><span>your own.</span></h1>
          <p>Bring your search into focus with one calm, clear place for discovering roles and building your momentum.</p>
        </div>
        <div className="auth-proof">
          <span className="proof-pill"><Compass size={13} aria-hidden="true" /> Discover opportunities</span>
          <span className="proof-pill"><BriefcaseBusiness size={13} aria-hidden="true" /> Track your progress</span>
          <span className="proof-pill"><Check size={13} aria-hidden="true" /> Free for students</span>
        </div>
      </aside>

      <section className="auth-main">
        <div className="auth-card-wrap">
          <Link className="auth-mobile-brand" href="/">
            <span className="brand-icon"><Sparkles size={16} aria-hidden="true" /></span>
            Career Agent
          </Link>
          <h2 className="auth-heading">Create your account</h2>
          <p className="auth-subheading">A little setup now. A clearer career search from here on.</p>
          <div className="auth-card">
            {error && <div className="alert alert-error" role="alert">{error}</div>}
            <form className="auth-form" onSubmit={handleSubmit}>
              <div className="field-wrap">
                <label className="field-label" htmlFor="register-name">Full name <span style={{ color: "var(--text-3)", fontWeight: 400 }}>· optional</span></label>
                <input
                  autoComplete="name"
                  className="field"
                  id="register-name"
                  onChange={event => setFullName(event.target.value)}
                  placeholder="How should we address you?"
                  type="text"
                  value={fullName}
                />
              </div>
              <div className="field-wrap">
                <label className="field-label" htmlFor="register-email">Email address</label>
                <input
                  autoComplete="email"
                  className="field"
                  id="register-email"
                  onChange={event => setEmail(event.target.value)}
                  placeholder="you@example.com"
                  required
                  type="email"
                  value={email}
                />
              </div>
              <div className="field-wrap">
                <label className="field-label" htmlFor="register-password">Password</label>
                <input
                  autoComplete="new-password"
                  className="field"
                  id="register-password"
                  onChange={event => setPassword(event.target.value)}
                  placeholder="Choose a password"
                  required
                  type="password"
                  value={password}
                />
              </div>
              <button className="button auth-submit" disabled={loading} type="submit">
                {loading ? "Creating your account…" : <>Create account <ArrowRight size={15} aria-hidden="true" /></>}
              </button>
            </form>
          </div>
          <p className="auth-footnote">Already have an account? <Link href="/login">Sign in</Link></p>
        </div>
      </section>
    </main>
  );
}
