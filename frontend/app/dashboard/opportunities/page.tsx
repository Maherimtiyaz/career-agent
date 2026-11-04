"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowDownToLine, ArrowLeft, ArrowRight, BriefcaseBusiness, MapPin, Search, Sparkles } from "lucide-react";
import api from "@/lib/api";
import type { Opportunity } from "@/types";

export default function OpportunitiesPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [source, setSource] = useState("");
  const [page, setPage] = useState(0);
  const [saving, setSaving] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState("");
  const [actionError, setActionError] = useState("");
  const limit = 20;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["opportunities", search, source, page],
    queryFn: async () => {
      const params = new URLSearchParams({ limit: String(limit), skip: String(page * limit) });
      if (search) params.set("search", search);
      if (source) params.set("source", source);
      return (await api.get<Opportunity[]>("/opportunities?" + params.toString())).data;
    },
  });

  const applyMutation = useMutation({
    mutationFn: ({ opportunity, status }: { opportunity: Opportunity; status: string }) =>
      api.post("/applications", {
        company: opportunity.organization,
        role: opportunity.title,
        job_link: opportunity.url,
        status,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["applications"] });
      qc.invalidateQueries({ queryKey: ["analytics"] });
    },
  });

  async function handleAction(opportunity: Opportunity, status: string) {
    setSaving(opportunity.id + status);
    setActionError("");
    setActionMessage("");
    try {
      await applyMutation.mutateAsync({ opportunity, status });
      setActionMessage(`“${opportunity.title}” added to your ${status === "saved" ? "saved roles" : "applications"}.`);
    } catch {
      setActionError("That role couldn’t be added. It may already be in your tracker—check Applications and try again.");
    } finally {
      setSaving(null);
    }
  }

  const formatSource = (value: string) => value.replaceAll("_", " ");

  return (
    <div className="page-wrap">
      <header className="page-head">
        <div>
          <div className="eyebrow">Explore</div>
          <h1 className="page-title">Opportunities</h1>
          <p className="page-description">Find a role or program that feels like your next step.</p>
        </div>
        <span className="page-context"><Sparkles size={14} aria-hidden="true" /> Curated across trusted sources</span>
      </header>

      <section className="search-panel panel">
        <label className="search-box">
          <Search size={16} aria-hidden="true" />
          <span className="sr-only">Search opportunities</span>
          <input
            aria-label="Search roles and organizations"
            className="search-input"
            onChange={event => { setSearch(event.target.value); setPage(0); }}
            placeholder="Search roles, companies, and programs"
            value={search}
          />
        </label>
        <label className="filter-select">
          <span className="sr-only">Filter by source</span>
          <select aria-label="Filter by source" className="field" onChange={event => { setSource(event.target.value); setPage(0); }} value={source}>
            <option value="">All sources</option>
            <option value="remote_jobs">Remote Jobs</option>
            <option value="curated">Curated</option>
            <option value="google_sheet">Google Sheet</option>
          </select>
        </label>
      </section>

      {actionMessage && <div className="alert alert-success action-alert" role="status">{actionMessage}</div>}
      {actionError && <div className="alert alert-error action-alert" role="alert">{actionError}</div>}

      {isLoading ? (
        <div className="opportunity-list" aria-label="Loading opportunities">
          {Array.from({ length: 6 }, (_, index) => <div className="skeleton opportunity-skeleton" key={index} />)}
        </div>
      ) : isError ? (
        <div className="panel empty-state">
          <div><span className="empty-icon"><CompassIcon /></span><p className="empty-title">We couldn’t load opportunities.</p><p className="empty-copy">Check your connection and try again.</p><button className="button button-secondary empty-action" onClick={() => refetch()}>Try again</button></div>
        </div>
      ) : data?.length ? (
        <>
          <div className="results-meta"><span>{data.length} {data.length === 1 ? "opportunity" : "opportunities"} on this page</span><span>Page {page + 1}</span></div>
          <div className="opportunity-list">
            {data.map((opportunity, index) => (
              <article className="opportunity-card" key={opportunity.id} style={{ animationDelay: `${Math.min(index, 7) * 35}ms` }}>
                <div className="opportunity-mark" aria-hidden="true">{opportunity.organization.trim().slice(0, 1).toUpperCase() || <BriefcaseBusiness size={16} />}</div>
                <div className="opportunity-main">
                  <div className="opportunity-title-line">
                    <a className="opportunity-title" href={opportunity.url} rel="noreferrer noopener" target="_blank">{opportunity.title}</a>
                    {opportunity.is_remote && <span className="tag tag-green">Remote</span>}
                    {opportunity.deadline && <span className="tag tag-amber">Deadline {opportunity.deadline}</span>}
                  </div>
                  <div className="opportunity-details">
                    <span>{opportunity.organization}</span>
                    {opportunity.location && <span><MapPin size={11} aria-hidden="true" /> {opportunity.location}</span>}
                    {opportunity.stipend && <span className="opportunity-stipend">{opportunity.stipend}</span>}
                    <span className="source-tag">{formatSource(opportunity.source)}</span>
                  </div>
                  {!!opportunity.tags && (
                    <div className="opportunity-tags">
                      {opportunity.tags.split(",").map(tag => tag.trim()).filter(tag => tag && !tag.startsWith("email:")).slice(0, 3).map(tag => <span className="tag" key={tag}>{tag}</span>)}
                    </div>
                  )}
                </div>
                <div className="opportunity-actions">
                  <button className="button button-quiet" disabled={saving === opportunity.id + "saved"} onClick={() => handleAction(opportunity, "saved")} type="button">
                    <ArrowDownToLine size={14} aria-hidden="true" /> {saving === opportunity.id + "saved" ? "Saving…" : "Save"}
                  </button>
                  <button className="button" disabled={saving === opportunity.id + "applied"} onClick={() => handleAction(opportunity, "applied")} type="button">
                    {saving === opportunity.id + "applied" ? "Adding…" : "Track application"}
                  </button>
                </div>
              </article>
            ))}
          </div>
          <nav className="pagination" aria-label="Opportunity pages">
            <button className="button button-secondary" disabled={page === 0} onClick={() => setPage(current => Math.max(0, current - 1))} type="button"><ArrowLeft size={14} aria-hidden="true" /> Previous</button>
            <span>Page {page + 1}</span>
            <button className="button button-secondary" disabled={data.length < limit} onClick={() => setPage(current => current + 1)} type="button">Next <ArrowRight size={14} aria-hidden="true" /></button>
          </nav>
        </>
      ) : (
        <div className="panel empty-state">
          <div>
            <span className="empty-icon"><Search size={18} aria-hidden="true" /></span>
            <p className="empty-title">{search || source ? "No opportunities match this search." : "A fresh start."}</p>
            <p className="empty-copy">{search || source ? "Try a broader keyword or clear the source filter." : "New opportunities will show up here as soon as they’re available."}</p>
            {(search || source) && <button className="button button-secondary empty-action" onClick={() => { setSearch(""); setSource(""); setPage(0); }}>Clear filters</button>}
          </div>
        </div>
      )}
    </div>
  );
}

function CompassIcon() {
  return <Search size={18} aria-hidden="true" />;
}
