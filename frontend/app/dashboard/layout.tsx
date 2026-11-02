"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { logout } from "@/lib/auth";

const nav = [
  { href: "/dashboard", label: "Overview", icon: "⬡", exact: true },
  { href: "/dashboard/ai", label: "AI Picks", icon: "✦", badge: "AI" },
  { href: "/dashboard/opportunities", label: "Opportunities", icon: "◈" },
  { href: "/dashboard/applications", label: "Applications", icon: "◎" },
  { href: "/dashboard/analytics", label: "Analytics", icon: "◑" },
  { href: "/dashboard/profile", label: "Profile", icon: "◉" },
  { href: "/dashboard/import", label: "Import", icon: "⤓" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "var(--bg)" }}>
      <aside style={{ width: 220, background: "var(--bg-2)", borderRight: "1px solid var(--border)", flexShrink: 0 }} className="flex flex-col">
        <div className="px-5 py-5" style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="flex items-center gap-2.5">
            <div style={{ width: 26, height: 26, borderRadius: 8, background: "linear-gradient(135deg, var(--primary), #a78bfa)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12 }}>✦</div>
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text)", letterSpacing: "-0.01em" }}>Career Agent</div>
              <div style={{ fontSize: 10, color: "var(--text-3)" }}>AI Career OS</div>
            </div>
          </div>
        </div>

        <nav className="flex-1 px-2 py-3 space-y-0.5">
          {nav.map(item => {
            const active = item.exact ? pathname === item.href : pathname.startsWith(item.href);
            return (
              <Link key={item.href} href={item.href} style={{
                display: "flex", alignItems: "center", gap: 10, padding: "7px 10px", borderRadius: 8,
                fontSize: 13, fontWeight: active ? 500 : 400, textDecoration: "none",
                background: active ? "var(--primary-dim)" : "transparent",
                color: active ? "var(--primary)" : "var(--text-2)",
                transition: "all 0.15s",
              }}
                onMouseEnter={e => { if (!active) (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.04)"; (e.currentTarget as HTMLElement).style.color = "var(--text)"; }}
                onMouseLeave={e => { if (!active) { (e.currentTarget as HTMLElement).style.background = "transparent"; (e.currentTarget as HTMLElement).style.color = "var(--text-2)"; } }}
              >
                <span style={{ fontSize: 14, opacity: 0.8 }}>{item.icon}</span>
                <span style={{ flex: 1 }}>{item.label}</span>
                {item.badge && (
                  <span style={{ fontSize: 9, fontWeight: 600, padding: "2px 5px", borderRadius: 4, background: "var(--primary-dim)", color: "var(--primary)", border: "1px solid var(--primary-glow)", letterSpacing: "0.05em" }}>
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        <div className="px-2 py-3" style={{ borderTop: "1px solid var(--border)" }}>
          <button onClick={() => { logout(); router.push("/login"); }} style={{
            width: "100%", display: "flex", alignItems: "center", gap: 10, padding: "7px 10px",
            borderRadius: 8, fontSize: 13, color: "var(--text-3)", background: "transparent",
            border: "none", cursor: "pointer", transition: "all 0.15s",
          }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = "var(--danger-dim)"; (e.currentTarget as HTMLElement).style.color = "var(--danger)"; }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = "transparent"; (e.currentTarget as HTMLElement).style.color = "var(--text-3)"; }}
          >
            <span>⎋</span> Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-auto" style={{ background: "var(--bg)" }}>
        {children}
      </main>
    </div>
  );
}
