"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowRight, BriefcaseBusiness, Check, Compass, Sparkles } from "lucide-react";
import axios from "axios";
import { login } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (requestError: unknown) {
      setError(
        axios.isAxiosError(requestError) && !requestError.response
          ? "We couldn’t reach Career Agent. Check your connection and try again."
          : "We couldn’t sign you in with those details. Please try again.",
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
          <h1>Your next<br />chapter starts <span>here.</span></h1>
          <p>Turn the job search into a journey you can actually navigate. Find opportunities, keep your momentum, and stay ready for the right one.</p>
        </div>
        <div className="auth-proof">
          <span className="proof-pill"><Compass size={13} aria-hidden="true" /> Discover opportunities</span>
          <span className="proof-pill"><BriefcaseBusiness size={13} aria-hidden="true" /> Track your progress</span>
          <span className="proof-pill"><Check size={13} aria-hidden="true" /> Made for students</span>
        </div>
      </aside>

      <section className="auth-main">
        <div className="auth-card-wrap">
          <Link className="auth-mobile-brand" href="/">
            <span className="brand-icon"><Sparkles size={16} aria-hidden="true" /></span>
            Career Agent
          </Link>
          <h2 className="auth-heading">Welcome back</h2>
          <p className="auth-subheading">Sign in to pick up where your next chapter begins.</p>
          <div className="auth-card">
            {error && <div className="alert alert-error" role="alert">{error}</div>}
            <form className="auth-form" onSubmit={handleSubmit}>
              <div className="field-wrap">
                <label className="field-label" htmlFor="login-email">Email address</label>
                <input
                  autoComplete="email"
                  className="field"
                  id="login-email"
                  onChange={event => setEmail(event.target.value)}
                  placeholder="you@example.com"
                  required
                  type="email"
                  value={email}
                />
              </div>
              <div className="field-wrap">
                <label className="field-label" htmlFor="login-password">Password</label>
                <input
                  autoComplete="current-password"
                  className="field"
                  id="login-password"
                  onChange={event => setPassword(event.target.value)}
                  placeholder="Enter your password"
                  required
                  type="password"
                  value={password}
                />
              </div>
              <button className="button auth-submit" disabled={loading} type="submit">
                {loading ? "Signing you in…" : <>Sign in <ArrowRight size={15} aria-hidden="true" /></>}
              </button>
            </form>
          </div>
          <p className="auth-footnote">New to Career Agent? <Link href="/register">Create your free account</Link></p>
        </div>
      </section>
    </main>
  );
}
