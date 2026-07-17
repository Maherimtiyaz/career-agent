"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Opportunity } from "@/types";

export default function OpportunitiesPage() {
  const [search, setSearch] = useState("");
  const [remote, setRemote] = useState<boolean | undefined>(undefined);
  const [source, setSource] = useState("");
  const [page, setPage] = useState(0);
  const limit = 20;

  const { data, isLoading } = useQuery({
    queryKey: ["opportunities", search, remote, source, page],
    queryFn: async () => {
      const params = new URLSearchParams({ limit: String(limit), skip: String(page * limit) });
      if (search) params.set("search", search);
      if (remote !== undefined) params.set("is_remote", String(remote));
      if (source) params.set("source", source);
      const res = await api.get<Opportunity[]>("/opportunities?" + params.toString());
      return res.data;
    },
  });

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Opportunities</h1>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">Browse and search all available positions</p>
      </div>

      <div className="flex gap-3 mb-6 flex-wrap">
        <input
          value={search} onChange={e => { setSearch(e.target.value); setPage(0); }}
          placeholder="Search by title or company..."
          className="flex-1 min-w-60 px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
        />
        <select
          value={source} onChange={e => { setSource(e.target.value); setPage(0); }}
          className="px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] text-sm focus:outline-none"
        >
          <option value="">All sources</option>
          <option value="remote_jobs">Remote Jobs</option>
          <option value="tech_jobs">Tech Jobs</option>
          <option value="curated">Curated</option>
          <option value="google_sheet">Google Sheet</option>
        </select>
        <select
          value={remote === undefined ? "" : String(remote)}
          onChange={e => { setRemote(e.target.value === "" ? undefined : e.target.value === "true"); setPage(0); }}
          className="px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] text-sm focus:outline-none"
        >
          <option value="">Remote + On-site</option>
          <option value="true">Remote only</option>
          <option value="false">On-site only</option>
        </select>
      </div>

      {isLoading ? (
        <div className="grid gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-20 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] animate-pulse" />
          ))}
        </div>
      ) : (
        <>
          <div className="text-xs text-[hsl(var(--muted-foreground))] mb-3">{data?.length ?? 0} results</div>
          <div className="grid gap-3">
            {data?.map(opp => (
              <div key={opp.id} className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] hover:shadow-sm transition">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <a href={opp.url} target="_blank" rel="noopener noreferrer"
                      className="font-medium text-sm hover:text-[hsl(var(--primary))] hover:underline transition line-clamp-1">
                      {opp.title}
                    </a>
                    <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">{opp.organization}</p>
                  </div>
                  <div className="flex flex-col items-end gap-1 flex-shrink-0">
                    {opp.stipend && <span className="text-xs text-green-600 font-medium">{opp.stipend}</span>}
                    {opp.is_remote && <span className="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 border border-blue-100">Remote</span>}
                  </div>
                </div>
                <div className="flex gap-2 mt-2 flex-wrap">
                  {opp.tags?.split(",").slice(0, 2).map(tag => tag.trim()).filter(t => t && !t.startsWith("email:")).map(tag => (
                    <span key={tag} className="text-xs px-2 py-0.5 rounded-full bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))]">{tag}</span>
                  ))}
                  {opp.location && <span className="text-xs text-[hsl(var(--muted-foreground))]">📍 {opp.location}</span>}
                </div>
              </div>
            ))}
          </div>
          <div className="flex justify-between mt-6">
            <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}
              className="px-4 py-2 rounded-lg border border-[hsl(var(--border))] text-sm disabled:opacity-40 hover:bg-[hsl(var(--accent))] transition">
              Previous
            </button>
            <span className="text-sm text-[hsl(var(--muted-foreground))] self-center">Page {page + 1}</span>
            <button onClick={() => setPage(p => p + 1)} disabled={(data?.length ?? 0) < limit}
              className="px-4 py-2 rounded-lg border border-[hsl(var(--border))] text-sm disabled:opacity-40 hover:bg-[hsl(var(--accent))] transition">
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
