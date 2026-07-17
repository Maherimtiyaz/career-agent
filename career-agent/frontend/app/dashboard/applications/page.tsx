"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Application } from "@/types";

const STATUS_COLORS: Record<string, string> = {
  applied: "bg-blue-50 text-blue-600 border-blue-100",
  interviewing: "bg-yellow-50 text-yellow-600 border-yellow-100",
  offer: "bg-green-50 text-green-600 border-green-100",
  rejected: "bg-red-50 text-red-600 border-red-100",
  saved: "bg-gray-50 text-gray-600 border-gray-100",
};

export default function ApplicationsPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ company: "", role: "", job_link: "", hr_contact: "", status: "applied", notes: "" });

  const { data: apps, isLoading } = useQuery({
    queryKey: ["applications"],
    queryFn: async () => (await api.get<Application[]>("/applications")).data,
  });

  const addMutation = useMutation({
    mutationFn: (body: typeof form) => api.post("/applications", body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["applications"] }); setShowForm(false); setForm({ company: "", role: "", job_link: "", hr_contact: "", status: "applied", notes: "" }); },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => api.patch("/applications/" + id, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["applications"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete("/applications/" + id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["applications"] }),
  });

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">My Applications</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">Track your job applications</p>
        </div>
        <button onClick={() => setShowForm(true)}
          className="px-4 py-2 rounded-lg bg-[hsl(var(--primary))] text-white text-sm font-medium hover:opacity-90 transition">
          + Add Application
        </button>
      </div>

      {showForm && (
        <div className="mb-6 p-5 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))]">
          <h2 className="font-semibold mb-4 text-sm">New Application</h2>
          <div className="grid grid-cols-2 gap-3">
            {(["company", "role", "job_link", "hr_contact"] as const).map(f => (
              <input key={f} placeholder={f.replace("_", " ")} value={form[f]}
                onChange={e => setForm(p => ({ ...p, [f]: e.target.value }))}
                className="px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
              />
            ))}
            <select value={form.status} onChange={e => setForm(p => ({ ...p, status: e.target.value }))}
              className="px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-sm">
              {["applied","interviewing","offer","rejected","saved"].map(s => <option key={s}>{s}</option>)}
            </select>
            <input placeholder="notes" value={form.notes} onChange={e => setForm(p => ({ ...p, notes: e.target.value }))}
              className="px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
            />
          </div>
          <div className="flex gap-2 mt-3">
            <button onClick={() => addMutation.mutate(form)}
              className="px-4 py-2 rounded-lg bg-[hsl(var(--primary))] text-white text-sm font-medium hover:opacity-90 transition">
              Save
            </button>
            <button onClick={() => setShowForm(false)}
              className="px-4 py-2 rounded-lg border border-[hsl(var(--border))] text-sm hover:bg-[hsl(var(--accent))] transition">
              Cancel
            </button>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-16 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] animate-pulse" />)}
        </div>
      ) : apps?.length === 0 ? (
        <div className="text-center py-16 text-[hsl(var(--muted-foreground))]">
          <p className="text-lg mb-2">No applications yet</p>
          <p className="text-sm">Add your first application above or import from Google Sheets</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-[hsl(var(--border))]">
          <table className="w-full text-sm">
            <thead className="bg-[hsl(var(--muted))] border-b border-[hsl(var(--border))]">
              <tr>{["Company","Role","Status","HR Contact","Date Applied","Actions"].map(h => (
                <th key={h} className="px-4 py-3 text-left text-xs font-medium text-[hsl(var(--muted-foreground))]">{h}</th>
              ))}</tr>
            </thead>
            <tbody className="divide-y divide-[hsl(var(--border))] bg-[hsl(var(--card))]">
              {apps?.map(app => (
                <tr key={app.id} className="hover:bg-[hsl(var(--accent))] transition">
                  <td className="px-4 py-3 font-medium">{app.company}</td>
                  <td className="px-4 py-3 text-[hsl(var(--muted-foreground))]">
                    {app.job_link ? <a href={app.job_link} target="_blank" className="hover:underline text-[hsl(var(--primary))]">{app.role}</a> : app.role}
                  </td>
                  <td className="px-4 py-3">
                    <select value={app.status}
                      onChange={e => updateMutation.mutate({ id: app.id, status: e.target.value })}
                      className={"text-xs px-2 py-1 rounded-full border font-medium " + (STATUS_COLORS[app.status] ?? "bg-gray-50 text-gray-600 border-gray-100")}>
                      {["applied","interviewing","offer","rejected","saved"].map(s => <option key={s}>{s}</option>)}
                    </select>
                  </td>
                  <td className="px-4 py-3 text-[hsl(var(--muted-foreground))]">{app.hr_contact ?? "—"}</td>
                  <td className="px-4 py-3 text-[hsl(var(--muted-foreground))]">{app.date_applied ?? "—"}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => deleteMutation.mutate(app.id)}
                      className="text-xs text-red-500 hover:text-red-700 transition">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
