"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { BarChart3, BriefcaseBusiness, Compass, Percent, Sparkles } from "lucide-react";
import api from "@/lib/api";

interface AnalyticsData {
  total_applications: number;
  total_opportunities: number;
  response_rate: number;
  by_status: { status: string; count: number }[];
  by_source: { source: string; count: number }[];
  timeline: { month: string; count: number }[];
  remote_split: { remote: boolean; count: number }[];
}

const STATUS_COLORS: Record<string, string> = {
  applied: "#8bc4ef",
  interviewing: "#edc979",
  offer: "#82d9a2",
  rejected: "#f08a82",
  saved: "#859187",
};
const SOURCE_COLORS = ["#c4f06b", "#8bc4ef", "#82d9a2", "#edc979", "#c5a5ef", "#f08a82"];
const tooltipStyle = { background: "#18201b", border: "1px solid rgba(224,240,228,.14)", borderRadius: 10, color: "#eef4ed", fontSize: 11 };

function StatCard({ label, value, icon: Icon, tone }: {
  label: string;
  value: string | number;
  icon: typeof BriefcaseBusiness;
  tone: string;
}) {
  return (
    <article className="analytics-stat">
      <span className={`stat-icon ${tone}`}><Icon size={16} aria-hidden="true" /></span>
      <span className="analytics-stat-value">{value}</span>
      <span className="analytics-stat-label">{label}</span>
    </article>
  );
}

function ChartEmpty({ children }: { children: string }) {
  return <div className="chart-empty"><span className="empty-icon"><BarChart3 size={17} aria-hidden="true" /></span><span>{children}</span></div>;
}

export default function AnalyticsPage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["analytics"],
    queryFn: async () => (await api.get<AnalyticsData>("/analytics/summary")).data,
  });

  if (isLoading) {
    return <div className="page-wrap"><div className="page-head"><div><div className="eyebrow">Your progress</div><h1 className="page-title">Analytics</h1></div></div><div className="stat-grid">{Array.from({ length: 4 }, (_, index) => <div className="skeleton analytics-skeleton" key={index} />)}</div><div className="split-grid analytics-skeleton-grid"><div className="skeleton chart-skeleton" /><div className="skeleton chart-skeleton" /></div></div>;
  }

  if (isError || !data) {
    return <div className="page-wrap"><header className="page-head"><div><div className="eyebrow">Your progress</div><h1 className="page-title">Analytics</h1><p className="page-description">A clear view of your search over time.</p></div></header><div className="panel empty-state"><div><span className="empty-icon"><BarChart3 size={18} aria-hidden="true" /></span><p className="empty-title">Your analytics couldn’t load.</p><p className="empty-copy">Check your connection and try again.</p><button className="button button-secondary empty-action" onClick={() => refetch()}>Try again</button></div></div></div>;
  }

  const byStatus = data.by_status ?? [];
  const bySource = data.by_source ?? [];
  const timeline = data.timeline ?? [];
  const remoteSplit = data.remote_split ?? [];
  const remoteCount = remoteSplit.find(item => item.remote)?.count ?? 0;
  const onsiteCount = remoteSplit.find(item => !item.remote)?.count ?? 0;
  const remoteData = [{ name: "Remote", value: remoteCount }, { name: "On-site", value: onsiteCount }];
  const hasRemoteData = remoteData.some(item => item.value > 0);

  return (
    <div className="page-wrap">
      <header className="page-head">
        <div><div className="eyebrow">Your progress</div><h1 className="page-title">Analytics</h1><p className="page-description">A clearer view of where your career search is going.</p></div>
        <span className="page-context"><Sparkles size={14} aria-hidden="true" /> Your activity, at a glance</span>
      </header>

      <section className="stat-grid analytics-stat-grid" aria-label="Career search metrics">
        <StatCard label="Applications" value={data.total_applications.toLocaleString()} icon={BriefcaseBusiness} tone="tone-blue" />
        <StatCard label="Response rate" value={`${data.response_rate}%`} icon={Percent} tone="tone-green" />
        <StatCard label="Opportunities" value={data.total_opportunities.toLocaleString()} icon={Compass} tone="tone-violet" />
        <StatCard label="Offers" value={(byStatus.find(item => item.status === "offer")?.count ?? 0).toLocaleString()} icon={Sparkles} tone="tone-amber" />
      </section>

      <section className="analytics-grid">
        <article className="panel chart-panel">
          <div className="chart-heading"><div><h2 className="section-title">Applications by status</h2><p className="section-caption">See how each opportunity is progressing.</p></div></div>
          {byStatus.length === 0 ? <ChartEmpty>Track an application to see your progress here.</ChartEmpty> : (
            <div className="chart-frame">
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={byStatus} dataKey="count" nameKey="status" cx="50%" cy="50%" innerRadius={56} outerRadius={83} paddingAngle={3} stroke="none">
                    {byStatus.map(item => <Cell key={item.status} fill={STATUS_COLORS[item.status] ?? "#859187"} />)}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} formatter={(value, name) => [value, name]} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
          {byStatus.length > 0 && <div className="chart-legend">{byStatus.map(item => <span className="legend-item" key={item.status}><i style={{ background: STATUS_COLORS[item.status] ?? "#859187" }} />{item.status}<strong>{item.count}</strong></span>)}</div>}
        </article>

        <article className="panel chart-panel">
          <div className="chart-heading"><div><h2 className="section-title">Opportunities by source</h2><p className="section-caption">Where the roles in your workspace come from.</p></div></div>
          {bySource.length === 0 ? <ChartEmpty>Opportunity sources will appear once data is available.</ChartEmpty> : (
            <div className="chart-frame">
              <ResponsiveContainer width="100%" height={235}>
                <BarChart data={bySource} layout="vertical" margin={{ left: 10, right: 12, top: 4, bottom: 4 }}>
                  <XAxis type="number" tick={{ fill: "#829085", fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis type="category" dataKey="source" tick={{ fill: "#a0ada2", fontSize: 10 }} axisLine={false} tickLine={false} width={90} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Bar dataKey="count" radius={[0, 6, 6, 0]} barSize={15}>{bySource.map((item, index) => <Cell key={item.source} fill={SOURCE_COLORS[index % SOURCE_COLORS.length]} />)}</Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </article>

        <article className="panel chart-panel chart-panel-wide">
          <div className="chart-heading"><div><h2 className="section-title">Application activity</h2><p className="section-caption">Your application activity over time.</p></div></div>
          {timeline.length === 0 ? <ChartEmpty>Your activity timeline will take shape as you track applications.</ChartEmpty> : (
            <div className="chart-frame">
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={timeline} margin={{ left: -16, right: 12, top: 10, bottom: 2 }}>
                  <CartesianGrid stroke="rgba(224,240,228,.08)" strokeDasharray="4 5" vertical={false} />
                  <XAxis dataKey="month" tick={{ fill: "#829085", fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: "#829085", fontSize: 10 }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Line activeDot={{ r: 5, fill: "#c4f06b", stroke: "#18201b" }} dataKey="count" dot={{ r: 3, fill: "#c4f06b", stroke: "#18201b", strokeWidth: 2 }} stroke="#c4f06b" strokeWidth={2} type="monotone" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </article>

        <article className="panel chart-panel">
          <div className="chart-heading"><div><h2 className="section-title">Remote vs on-site</h2><p className="section-caption">How opportunity formats break down.</p></div></div>
          {!hasRemoteData ? <ChartEmpty>No location data is available yet.</ChartEmpty> : (
            <>
              <div className="chart-frame">
                <ResponsiveContainer width="100%" height={210}>
                  <PieChart>
                    <Pie data={remoteData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={54} outerRadius={79} paddingAngle={3} stroke="none">
                      <Cell fill="#c4f06b" /><Cell fill="#354039" />
                    </Pie>
                    <Tooltip contentStyle={tooltipStyle} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="remote-legend"><span><i className="legend-remote" />Remote<strong>{remoteCount.toLocaleString()}</strong></span><span><i className="legend-onsite" />On-site<strong>{onsiteCount.toLocaleString()}</strong></span></div>
            </>
          )}
        </article>
      </section>
    </div>
  );
}
