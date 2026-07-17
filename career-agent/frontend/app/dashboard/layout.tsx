"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { logout } from "@/lib/auth";

const nav = [
  { href: "/dashboard", label: "Dashboard", icon: "▦" },
  { href: "/dashboard/opportunities", label: "Opportunities", icon: "🔍" },
  { href: "/dashboard/applications", label: "My Applications", icon: "📋" },
  { href: "/dashboard/import", label: "Import Sheet", icon: "📊" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  function handleLogout() {
    logout();
    router.push("/login");
  }

  return (
    <div className="flex h-screen bg-[hsl(var(--background))]">
      <aside className="w-60 flex-shrink-0 bg-[hsl(var(--sidebar))] text-[hsl(var(--sidebar-foreground))] flex flex-col">
        <div className="px-6 py-5 border-b border-white/10">
          <h1 className="text-lg font-bold tracking-tight">Career Agent</h1>
          <p className="text-xs opacity-50 mt-0.5">v6 — Career OS</p>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {nav.map(item => (
            <Link
              key={item.href} href={item.href}
              className={"flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition " +
                (pathname === item.href
                  ? "bg-white/15 text-white font-medium"
                  : "text-white/60 hover:bg-white/10 hover:text-white")}
            >
              <span className="text-base">{item.icon}</span>
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="px-3 py-4 border-t border-white/10">
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-white/60 hover:bg-white/10 hover:text-white transition"
          >
            <span>⎋</span> Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  );
}
