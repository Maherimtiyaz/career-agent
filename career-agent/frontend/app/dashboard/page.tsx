"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getMe } from "@/lib/auth";
import api from "@/lib/api";
import type { User, Application } from "@/types";
import Link from "next/link";

const STATUS_COLOR: Record<string, string> = {
  applied: "var(--blue)", interviewing: "var(--warning)", offer: "var(--success)", rejected: "var(--danger)", saved: "var(--text-3)",
};

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [apps, setApps] = useState<Application[]>([]);
  const [oppCount, setOppCount] = useState(0);

  useEffect(() => {
    if (!localStorage.getItem("access_token")) { router.push("/login"); return; }
    getMe().then(setUser).catch(() => router.push("/login"));
    api.get<Application[]>("/applications").then(r => setApps(r.data)).catch(() => {});
    api.get("/opportunities?limit=200").then(r => setOppCount(r.data.length)).catch(() => {});
  }, [router]);

  const byStatus = (s: string) => apps.filter(a => a.status === s).length;

  const stats = [
    { label: "Opportunities", value: oppCount, icon: "◈", color: "var(--primary)", dim: "var(--primary-dim)", href: "/dashboard/opportunities" },
    { label: "Applications", value: apps.length, icon: "◎", color: "var(--blue)", dim: "var(--blue-dim)", href: "/dashboard/applications" },
    { label: "Interviewing", value: byStatus("interviewing"), icon: "◑", color: "var(--warning)", dim: "var(--warning-dim)", href: "/dashboard/applications" },
    { label: "Offers", value: byStatus("offer"), icon: "✦", color: "var(--success)", dim: "var(--success-dim)", href: "/dashboard/applications" },
  ];

  const recent = apps.slice(0, 5);

  return (
    <div style={{ padding: "32px 40px", maxWidth: 900 }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0, letterSpacing: "-0.02em" }}>
          {user?.full_name ? "Hey, " + user.full_name.split(" ")[0] + " 👋" : "Dashboard"}
        </h1>
        <p style={{ color: "var(--text-2)", fontSize: 14, marginTop: 4 }}>Your career at a glance</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 32 }}>
        {stats.map(s => (
          <Link key={s.label} href={s.href} style={{ textDecoration: "none", display: "block", padding: "18px 20px", borderRadius: 14, border: "1px solid var(--border)", background: "var(--bg-2)", transition: "border-color 0.15s, background 0.15s" }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = s.color; (e.currentTarget as HTMLElement).style.background = s.dim; }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border)"; (e.currentTarget as HTMLElement).style.background = "var(--bg-2)"; }}>
            <div style={{ fontSize: 20, marginBottom: 12, color: s.color }}>{s.icon}</div>
            <div style={{ fontSize: 28, fontWeight: 700, color: "var(--text)", letterSpacing: "-0.02em" }}>{s.value}</div>
            <div style={{ fontSize: 12, color: "var(--text-2)", marginTop: 2 }}>{s.label}</div>
          </Link>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 24 }}>
        <Link href="/dashboard/ai" style={{ textDecoration: "none", padding: "20px 22px", borderRadius: 14, border: "1px solid var(--primary-glow)", background: "var(--primary-dim)", display: "block", transition: "opacity 0.15s" }}
          onMouseEnter={e => (e.currentTarget as HTMLElement).style.opacity = "0.8"}
          onMouseLeave={e => (e.currentTarget as HTMLElement).style.opacity = "1"}>
          <div style={{ fontSize: 18, marginBottom: 8 }}>✦</div>
          <div style={{ fontWeight: 600, fontSize: 14, color: "var(--text)" }}>AI Recommendations</div>
          <div style={{ fontSize: 12, color: "var(--text-2)", marginTop: 4 }}>Personalized picks based on your profile</div>
        </Link>
        <Link href="/dashboard/import" style={{ textDecoration: "none", padding: "20px 22px", borderRadius: 14, border: "1px solid var(--border)", background: "var(--bg-2)", display: "block", transition: "border-color 0.15s" }}
          onMouseEnter={e => (e.currentTarget as HTMLElement).style.borderColor = "var(--border-hover)"}
          onMouseLeave={e => (e.currentTarget as HTMLElement).style.borderColor = "var(--border)"}>
          <div style={{ fontSize: 18, marginBottom: 8 }}>⤓</div>
          <div style={{ fontWeight: 600, fontSize: 14, color: "var(--text)" }}>Import Google Sheet</div>
          <div style={{ fontSize: 12, color: "var(--text-2)", marginTop: 4 }}>Sync your personal tracker</div>
        </Link>
      </div>

      {recent.length > 0 && (
        <div style={{ background: "var(--bg-2)", border: "1px solid var(--border)", borderRadius: 14, overflow: "hidden" }}>
          <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 13, fontWeight: 600 }}>Recent Applications</span>
            <Link href="/dashboard/applications" style={{ fontSize: 12, color: "var(--primary)", textDecoration: "none" }}>View all →</Link>
          </div>
          {recent.map((app, i) => (
            <div key={app.id} style={{ padding: "12px 20px", borderBottom: i < recent.length - 1 ? "1px solid var(--border)" : "none", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 500 }}>{app.role}</div>
                <div style={{ fontSize: 12, color: "var(--text-2)", marginTop: 1 }}>{app.company}</div>
              </div>
              <span style={{ fontSize: 11, fontWeight: 500, padding: "3px 8px", borderRadius: 6, background: "rgba(255,255,255,0.06)", color: STATUS_COLOR[app.status] ?? "var(--text-2)" }}>
                {app.status}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
