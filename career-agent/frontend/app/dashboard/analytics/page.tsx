"use client";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, CartesianGrid } from "recharts";

const STATUS_COLORS: Record<string, string> = {
  applied: "#60a5fa",
  interviewing: "#fbbf24",
  offer: "#34d399",
  rejected: "#f87171",
  saved: "#9090a8",
};

const SOURCE_COLORS = ["#7c6fff", "#60a5fa", "#34d399", "#fbbf24", "#f87171", "#a78bfa"];

function StatCard({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div style={{ padding: "20px 24px", borderRadius: 14, border: "1px solid var(--border)", background: "var(--bg-2)" }}>
      <div style={{ fontSize: 28, fontWeight: 700, color: color ?? "var(--text)", letterSpacing: "-0.02em" }}>{value}</div>
      <div style={{ fontSize: 13, color: "var(--text-2)", marginTop: 4 }}>{label}</div>
      {sub && <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

const tooltipStyle = { background: "var(--bg-3)", border: "1px solid var(--border)", borderRadius: 8, color: "var(--text)", fontSize: 12 };

export default function AnalyticsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["analytics"],
    queryFn: async () => (await api.get("/analytics/summary")).data,
  });

  if (isLoading) return (
    <div style={{ padding: "32px 40px" }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, margin: "0 0 24px", letterSpacing: "-0.02em" }}>Analytics</h1>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12, marginBottom: 24 }}>
        {Array.from({ length: 4 }).map((_, i) => <div key={i} style={{ height: 90, borderRadius: 14, background: "var(--bg-2)", border: "1px solid var(--border)" }} />)}
      </div>
    </div>
  );

  const byStatus: { status: string; count: number }[] = data?.by_status ?? [];
  const bySource: { source: string; count: number }[] = data?.by_source ?? [];
  const timeline: { month: string; count: number }[] = data?.timeline ?? [];
  const remoteSplit: { remote: boolean; count: number }[] = data?.remote_split ?? [];

  const remoteCount = remoteSplit.find(r => r.remote)?.count ?? 0;
  const onsiteCount = remoteSplit.find(r => !r.remote)?.count ?? 0;
  const remoteData = [
    { name: "Remote", value: remoteCount },
    { name: "On-site", value: onsiteCount },
  ];

  return (
    <div style={{ padding: "32px 40px", maxWidth: 1000 }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, letterSpacing: "-0.02em" }}>Analytics</h1>
        <p style={{ color: "var(--text-2)", fontSize: 13, marginTop: 4 }}>Your career activity at a glance</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12, marginBottom: 28 }}>
        <StatCard label="Total Applications" value={data?.total_applications ?? 0} color="var(--blue)" />
        <StatCard label="Response Rate" value={(data?.response_rate ?? 0) + "%"} sub="Interviewing + Offers / Total" color="var(--success)" />
        <StatCard label="Opportunities" value={(data?.total_opportunities ?? 0).toLocaleString()} color="var(--primary)" />
        <StatCard label="Offers" value={byStatus.find(s => s.status === "offer")?.count ?? 0} color="var(--warning)" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>

        <div style={{ padding: "20px 24px", borderRadius: 14, border: "1px solid var(--border)", background: "var(--bg-2)" }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 20 }}>Applications by Status</div>
          {byStatus.length === 0 ? (
            <div style={{ textAlign: "center", color: "var(--text-3)", fontSize: 13, padding: "32px 0" }}>No applications yet</div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={byStatus} dataKey="count" nameKey="status" cx="50%" cy="50%" outerRadius={75} innerRadius={45}>
                  {byStatus.map(entry => (
                    <Cell key={entry.status} fill={STATUS_COLORS[entry.status] ?? "#666"} />
                  ))}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} formatter={(v, n) => [v, n]} />
              </PieChart>
            </ResponsiveContainer>
          )}
          <div style={{ display: "flex", flexWrap: "wrap", gap: "8px 16px", marginTop: 12 }}>
            {byStatus.map(s => (
              <div key={s.status} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-2)" }}>
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: STATUS_COLORS[s.status] ?? "#666" }} />
                {s.status} ({s.count})
              </div>
            ))}
          </div>
        </div>

        <div style={{ padding: "20px 24px", borderRadius: 14, border: "1px solid var(--border)", background: "var(--bg-2)" }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 20 }}>Opportunities by Source</div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={bySource} layout="vertical" margin={{ left: 20, right: 20 }}>
              <XAxis type="number" tick={{ fill: "var(--text-3)", fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="source" tick={{ fill: "var(--text-2)", fontSize: 11 }} axisLine={false} tickLine={false} width={80} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="count" radius={[0, 6, 6, 0]}>
                {bySource.map((_, i) => <Cell key={i} fill={SOURCE_COLORS[i % SOURCE_COLORS.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

      </div>

      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16 }}>

        <div style={{ padding: "20px 24px", borderRadius: 14, border: "1px solid var(--border)", background: "var(--bg-2)" }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 20 }}>Application Activity Over Time</div>
          {timeline.length === 0 ? (
            <div style={{ textAlign: "center", color: "var(--text-3)", fontSize: 13, padding: "32px 0" }}>No data yet — start tracking applications</div>
          ) : (
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={timeline}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="month" tick={{ fill: "var(--text-3)", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "var(--text-3)", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={tooltipStyle} />
                <Line type="monotone" dataKey="count" stroke="var(--primary)" strokeWidth={2} dot={{ fill: "var(--primary)", r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        <div style={{ padding: "20px 24px", borderRadius: 14, border: "1px solid var(--border)", background: "var(--bg-2)" }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 20 }}>Remote vs On-site</div>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie data={remoteData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} innerRadius={40}>
                <Cell fill="var(--primary)" />
                <Cell fill="var(--bg-4, #2a2a38)" />
              </Pie>
              <Tooltip contentStyle={tooltipStyle} />
            </PieChart>
          </ResponsiveContainer>
          <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "var(--text-2)" }}>
              <span style={{ display: "flex", alignItems: "center", gap: 6 }}><span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--primary)", display: "inline-block" }} />Remote</span>
              <span>{remoteCount.toLocaleString()}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "var(--text-2)" }}>
              <span style={{ display: "flex", alignItems: "center", gap: 6 }}><span style={{ width: 8, height: 8, borderRadius: "50%", background: "#2a2a38", border: "1px solid var(--border)", display: "inline-block" }} />On-site</span>
              <span>{onsiteCount.toLocaleString()}</span>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
