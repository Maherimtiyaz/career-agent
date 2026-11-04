"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowDownToLine, ArrowRight, BriefcaseBusiness, MapPin, Sparkles } from "lucide-react";
import api from "@/lib/api";
import type { Opportunity } from "@/types";

export default function AIPage() {
  const qc = useQueryClient();
  const [saving, setSaving] = useState<string | null>(null);
  const [feedback, setFeedback] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["ai-recommendations"],
    queryFn: async () => (await api.get<Opportunity[]>("/ai/recommendations?limit=20")).data,
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
    setFeedback("");
    setErrorMessage("");
    try {
      await applyMutation.mutateAsync({ opportunity, status });
      setFeedback(`“${opportunity.title}” added to your ${status === "saved" ? "saved roles" : "applications"}.`);
    } catch {
      setErrorMessage("That role couldn’t be added. It may already be in your tracker—check Applications and try again.");
    } finally {
      setSaving(null);
    }
  }

  return (
    <div className="page-wrap">
      <header className="page-head">
        <div>
          <div className="eyebrow">A better-fit starting point</div>
          <h1 className="page-title">AI Picks</h1>
          <p className="page-description">Opportunities ranked by how well they line up with your interests.</p>
        </div>
        <Link className="button button-secondary" href="/dashboard/profile"><Sparkles size={14} aria-hidden="true" /> Tune your profile</Link>
      </header>

      <div className="alert alert-info scoring-note">
        <Sparkles size={15} aria-hidden="true" />
        <span><strong>How these picks work:</strong> a local semantic model compares your skills, interests, and experience with each opportunity. Your profile stays in your Career Agent deployment. Add target roles and skills to make your recommendations more personal.</span>
      </div>

      {feedback && <div className="alert alert-success action-alert" role="status">{feedback}</div>}
      {errorMessage && <div className="alert alert-error action-alert" role="alert">{errorMessage}</div>}

      {isLoading ? (
        <div className="opportunity-list" aria-label="Loading recommendations">
          {Array.from({ length: 5 }, (_, index) => <div className="skeleton opportunity-skeleton" key={index} />)}
        </div>
      ) : isError ? (
        <div className="panel empty-state">
          <div><span className="empty-icon"><Sparkles size={18} aria-hidden="true" /></span><p className="empty-title">Your picks aren’t available right now.</p><p className="empty-copy">Check your connection and try again.</p><button className="button button-secondary empty-action" onClick={() => refetch()}>Try again</button></div>
        </div>
      ) : data?.length ? (
        <div className="opportunity-list">
          {data.map((opportunity, index) => (
            <article className={`opportunity-card ai-opportunity${index < 3 ? " ai-opportunity-featured" : ""}`} key={opportunity.id} style={{ animationDelay: `${Math.min(index, 7) * 35}ms` }}>
              <span className={`rank-number${index < 3 ? " rank-highlight" : ""}`}>{String(index + 1).padStart(2, "0")}</span>
              <div className="opportunity-mark" aria-hidden="true">{opportunity.organization.trim().slice(0, 1).toUpperCase() || <BriefcaseBusiness size={16} />}</div>
              <div className="opportunity-main">
                <div className="opportunity-title-line">
                  <a className="opportunity-title" href={opportunity.url} rel="noreferrer noopener" target="_blank">{opportunity.title}</a>
                  {index < 3 && <span className="tag tag-green">Strong match</span>}
                  {opportunity.is_remote && <span className="tag">Remote</span>}
                </div>
                <div className="opportunity-details">
                  <span>{opportunity.organization}</span>
                  {opportunity.location && <span><MapPin size={11} aria-hidden="true" /> {opportunity.location}</span>}
                  {opportunity.stipend && <span className="opportunity-stipend">{opportunity.stipend}</span>}
                  {opportunity.deadline && <span className="tag tag-amber">Deadline {opportunity.deadline}</span>}
                </div>
              </div>
              <div className="opportunity-actions">
                <button className="button button-quiet" disabled={saving === opportunity.id + "saved"} onClick={() => handleAction(opportunity, "saved")} type="button">
                  <ArrowDownToLine size={14} aria-hidden="true" /> {saving === opportunity.id + "saved" ? "Saving…" : "Save"}
                </button>
                <button className="button" disabled={saving === opportunity.id + "applied"} onClick={() => handleAction(opportunity, "applied")} type="button">
                  {saving === opportunity.id + "applied" ? "Adding…" : "Track role"}
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="panel empty-state">
          <div>
            <span className="empty-icon"><Sparkles size={18} aria-hidden="true" /></span>
            <p className="empty-title">Your next match starts with your profile.</p>
            <p className="empty-copy">Add skills and target roles so Career Agent can surface opportunities that better fit your direction.</p>
            <Link className="button button-secondary empty-action" href="/dashboard/profile">Add your interests <ArrowRight size={14} aria-hidden="true" /></Link>
          </div>
        </div>
      )}
    </div>
  );
}
