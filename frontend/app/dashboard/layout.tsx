"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  BarChart3,
  BriefcaseBusiness,
  Compass,
  LayoutDashboard,
  LogOut,
  Sparkles,
  Upload,
  UserRound,
} from "lucide-react";
import { isLoggedIn, logout } from "@/lib/auth";

const nav = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard, exact: true },
  { href: "/dashboard/ai", label: "AI Picks", icon: Sparkles, badge: "MATCHED" },
  { href: "/dashboard/opportunities", label: "Opportunities", icon: Compass },
  { href: "/dashboard/applications", label: "Applications", icon: BriefcaseBusiness },
  { href: "/dashboard/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/dashboard/profile", label: "Profile", icon: UserRound },
  { href: "/dashboard/import", label: "Data sources", icon: Upload },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [authorized, setAuthorized] = useState(false);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login");
      return;
    }
    setAuthorized(true);
  }, [router]);

  if (!authorized) {
    return <main className="main-content" aria-label="Loading workspace"><div className="page-wrap"><div className="skeleton" style={{ height: 150 }} /></div></main>;
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link className="brand-row" href="/dashboard" style={{ color: "inherit", textDecoration: "none" }}>
          <span className="brand-icon"><Sparkles size={17} aria-hidden="true" /></span>
          <span>
            <span className="brand-name" style={{ display: "block" }}>Career Agent</span>
            <span className="brand-caption" style={{ display: "block" }}>Your career workspace</span>
          </span>
        </Link>

        <div className="sidebar-caption">Workspace</div>
        <nav className="sidebar-nav" aria-label="Workspace navigation">
          {nav.map(({ href, label, icon: Icon, exact, badge }) => {
            const active = exact ? pathname === href : pathname.startsWith(href);
            return (
              <Link
                aria-current={active ? "page" : undefined}
                className={`nav-link${active ? " nav-link-active" : ""}`}
                href={href}
                key={href}
              >
                <span className="nav-ico"><Icon size={16} aria-hidden="true" /></span>
                <span>{label}</span>
                {badge && <span className="nav-badge">{badge}</span>}
              </Link>
            );
          })}
        </nav>

        <div className="sidebar-bottom">
          <Link className="profile-chip" href="/dashboard/profile" style={{ textDecoration: "none" }}>
            <span className="profile-avatar">CA</span>
            <span style={{ minWidth: 0 }}>
              <span className="profile-chip-name" style={{ display: "block" }}>Your workspace</span>
              <span className="profile-chip-caption" style={{ display: "block" }}>Profile & preferences</span>
            </span>
          </Link>
          <button className="signout-btn" onClick={logout} type="button">
            <LogOut size={15} aria-hidden="true" /> Sign out
          </button>
        </div>
      </aside>
      <main className="main-content">{children}</main>
    </div>
  );
}
