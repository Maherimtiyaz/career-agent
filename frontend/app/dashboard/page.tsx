"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, BarChart3, BriefcaseBusiness, Compass, Sparkles } from "lucide-react";
import api from "@/lib/api";
import { getMe } from "@/lib/auth";
import type { Application } from "@/types";

interface AnalyticsSummary {
  total_applications: number;
  total_opportunities: number;
  response_rate: number;
  by_status: { status: string; count: number }[];
}

const statusClass: Record<string, string> = {
  applied: "status-blue",
  interviewing: "status-warning",
  offer: "status-success",
  rejected: "status-danger",
  saved: "status-neutral",
};

function StatCard({ label, value, icon: Icon, tone, href }: {
  label: string;
  value: number | string;
  icon: typeof Compass;
  tone: string;
  href: string;
}) {
  return (
    <Link className="stat-card" href={href}>
      <span className={`stat-icon ${tone}`}><Icon size={17} aria-hidden="true" /></span>
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
      <ArrowRight className="stat-arrow" size={14} aria-hidden="true" />
    </Link>
  );
}

export default function DashboardPage() {
  const userQuery = useQuery({ queryKey: ["me"], queryFn: getMe });
  const applicationsQuery = useQuery({
    queryKey: ["applications"],
    queryFn: async () => (await api.get<Application[]>("/applications")).data,
  });
  const summaryQuery = useQuery({
    queryKey: ["analytics"],
    queryFn: async () => (await api.get<AnalyticsSummary>("/analytics/summary")).data,
  });

  const user = userQuery.data;
  const applications = applicationsQuery.data ?? [];
  const summary = summaryQuery.data;
  const statusCount = (status: string) => summary?.by_status.find(item => item.status === status)?.count ?? 0;
  const loading = applicationsQuery.isLoading || summaryQuery.isLoading;
  const error = userQuery.isError || applicationsQuery.isError || summaryQuery.isError;
  const firstName = user?.full_name?.trim().split(/\s+/)[0];

  return (
    <div className="page-wrap">
      <header className="page-head">
        <div>
          <div className="eyebrow">Your workspace</div>
          <h1 className="page-title">{firstName ? `Good to see you, ${firstName}.` : "A little more focus. A lot more momentum."}</h1>
          <p className="page-description">Your career search, brought into view.</p>
        </div>
        <Link className="button button-secondary dashboard-analytics-link" href="/dashboard/analytics">
          <BarChart3 size={15} aria-hidden="true" /> View insights
        </Link>
      </header>

      {error && (
        <div className="alert alert-error dashboard-alert" role="alert">
          We couldn’t load all your workspace data. Refresh the page to try again.
        </div>
      )}

      <section className="stat-grid" aria-label="Career search summary">
        <StatCard label="Opportunities" value={loading ? "—" : (summary?.total_opportunities ?? 0).toLocaleString()} icon={Compass} tone="tone-green" href="/dashboard/opportunities" />
        <StatCard label="Applications" value={loading ? "—" : (summary?.total_applications ?? applications.length).toLocaleString()} icon={BriefcaseBusiness} tone="tone-blue" href="/dashboard/applications" />
        <StatCard label="Interviews" value={loading ? "—" : statusCount("interviewing")} icon={Sparkles} tone="tone-amber" href="/dashboard/applications" />
        <StatCard label="Offers" value={loading ? "—" : statusCount("offer")} icon={ArrowRight} tone="tone-violet" href="/dashboard/applications" />
      </section>

      <section className="dashboard-journeys" aria-label="Continue your career search">
        <Link className="journey-card journey-card-primary" href="/dashboard/ai">
          <span className="journey-icon"><Sparkles size={18} aria-hidden="true" /></span>
          <span className="journey-copy">
            <span className="journey-title">Find your next opportunity</span>
            <span className="journey-description">Explore roles matched to your interests and profile.</span>
          </span>
          <ArrowRight className="journey-arrow" size={16} aria-hidden="true" />
        </Link>
        <Link className="journey-card" href="/dashboard/applications">
          <span className="journey-icon journey-icon-neutral"><BriefcaseBusiness size={18} aria-hidden="true" /></span>
          <span className="journey-copy">
            <span className="journey-title">Keep your search moving</span>
            <span className="journey-description">Review applications and choose a clear next step.</span>
          </span>
          <ArrowRight className="journey-arrow" size={16} aria-hidden="true" />
        </Link>
      </section>

      <section className="panel recent-panel">
        <div className="panel-heading">
          <div><h2 className="section-title">Recent applications</h2><p className="section-caption">A quick look at the roles you’re pursuing.</p></div>
          <Link className="text-link" href="/dashboard/applications">View all <ArrowRight size={13} aria-hidden="true" /></Link>
        </div>
        {applicationsQuery.isLoading ? (
          <div className="recent-loading"><div className="skeleton" /><div className="skeleton" /><div className="skeleton" /></div>
        ) : applicationsQuery.isError ? (
          <div className="inline-empty"><p className="empty-copy">Your recent applications are temporarily unavailable.</p></div>
        ) : applications.length === 0 ? (
          <div className="inline-empty">
            <span className="empty-icon"><BriefcaseBusiness size={18} aria-hidden="true" /></span>
            <div><p className="empty-title">Your next application starts here.</p><p className="empty-copy">Save an opportunity to keep it close and start building your tracker.</p></div>
            <Link className="button button-secondary" href="/dashboard/opportunities">Explore roles</Link>
          </div>
        ) : (
          <div className="recent-list">
            {applications.slice(0, 5).map(application => (
              <div className="recent-row" key={application.id}>
                <span className="company-avatar">{application.company?.trim().slice(0, 1).toUpperCase() || "•"}</span>
                <div className="recent-role"><span className="recent-role-title">{application.role}</span><span className="recent-company">{application.company}</span></div>
                <span className={`status-pill ${statusClass[application.status] ?? "status-neutral"}`}>{application.status}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="dashboard-footer-card">
        <div className="dashboard-footer-mark"><Sparkles size={17} aria-hidden="true" /></div>
        <div><h2 className="section-title">Make the recommendations yours</h2><p className="section-caption">Add your skills and target roles to get more relevant AI Picks.</p></div>
        <Link className="button button-secondary" href="/dashboard/profile">Complete your profile <ArrowRight size={14} aria-hidden="true" /></Link>
      </section>
    </div>
  );
}
