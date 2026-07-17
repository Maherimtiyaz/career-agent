"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getMe } from "@/lib/auth";
import api from "@/lib/api";
import type { User } from "@/types";
import Link from "next/link";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [stats, setStats] = useState({ total: 0, applied: 0, interviewing: 0, opportunities: 0 });

  useEffect(() => {
    if (!localStorage.getItem("access_token")) { router.push("/login"); return; }
    getMe().then(setUser).catch(() => router.push("/login"));
    api.get("/applications").then(r => {
      const apps = r.data;
      setStats(s => ({
        ...s,
        total: apps.length,
        applied: apps.filter((a: { status: string }) => a.status === "applied").length,
        interviewing: apps.filter((a: { status: string }) => a.status === "interviewing").length,
      }));
    }).catch(() => {});
    api.get("/opportunities?limit=1").then(() => {
      api.get("/opportunities").then(r => setStats(s => ({ ...s, opportunities: r.data.length }))).catch(() => {});
    }).catch(() => {});
  }, [router]);

  const cards = [
    { label: "Opportunities", value: stats.opportunities, color: "bg-blue-500", href: "/dashboard/opportunities" },
    { label: "Applications", value: stats.total, color: "bg-purple-500", href: "/dashboard/applications" },
    { label: "Applied", value: stats.applied, color: "bg-yellow-500", href: "/dashboard/applications" },
    { label: "Interviewing", value: stats.interviewing, color: "bg-green-500", href: "/dashboard/applications" },
  ];

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold">
          Welcome back{user?.full_name ? ", " + user.full_name.split(" ")[0] : ""} 👋
        </h1>
        <p className="text-[hsl(var(--muted-foreground))] text-sm mt-1">Here is your career overview</p>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {cards.map(card => (
          <Link key={card.label} href={card.href}
            className="p-5 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] hover:shadow-md transition">
            <div className={"w-2 h-2 rounded-full mb-3 " + card.color} />
            <div className="text-3xl font-bold">{card.value}</div>
            <div className="text-sm text-[hsl(var(--muted-foreground))] mt-1">{card.label}</div>
          </Link>
        ))}
      </div>
      <div className="grid md:grid-cols-2 gap-4">
        <Link href="/dashboard/opportunities"
          className="p-6 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] hover:shadow-md transition">
          <h2 className="font-semibold mb-1">Browse Opportunities</h2>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">Search 2000+ remote jobs and internships</p>
        </Link>
        <Link href="/dashboard/import"
          className="p-6 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] hover:shadow-md transition">
          <h2 className="font-semibold mb-1">Import from Google Sheet</h2>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">Sync your personal opportunity tracker</p>
        </Link>
      </div>
    </div>
  );
}
