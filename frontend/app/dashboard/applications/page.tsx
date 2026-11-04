"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, BriefcaseBusiness, Mail, Plus, Trash2, X } from "lucide-react";
import api from "@/lib/api";
import type { Application } from "@/types";

interface Draft {
  subject: string;
  body: string;
  to: string | null;
}

const statuses = ["applied", "interviewing", "offer", "rejected", "saved"] as const;
const initialForm = { company: "", role: "", job_link: "", hr_contact: "", status: "applied", notes: "" };

function EmailModal({ draft, onClose }: { draft: Draft; onClose: () => void }) {
  const [copied, setCopied] = useState(false);
  const [body, setBody] = useState(draft.body);
  const [copyError, setCopyError] = useState("");

  async function copyAll() {
    try {
      await navigator.clipboard.writeText(`To: ${draft.to || "HR Contact"}\nSubject: ${draft.subject}\n\n${body}`);
      setCopied(true);
      setCopyError("");
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopyError("Clipboard access isn’t available. Select and copy the message instead.");
    }
  }

  function openMailto() {
    const mailto = `mailto:${draft.to || ""}?subject=${encodeURIComponent(draft.subject)}&body=${encodeURIComponent(body)}`;
    window.location.href = mailto;
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <section
        aria-labelledby="email-modal-title"
        aria-modal="true"
        className="email-modal panel"
        onClick={event => event.stopPropagation()}
        onKeyDown={event => { if (event.key === "Escape") onClose(); }}
        role="dialog"
        tabIndex={-1}
      >
        <header className="modal-header">
          <div>
            <span className="eyebrow">Outreach</span>
            <h2 className="section-title" id="email-modal-title">Your email draft</h2>
            {draft.to && <p className="section-caption">To: {draft.to}</p>}
          </div>
          <button aria-label="Close email draft" className="icon-button" onClick={onClose} type="button"><X size={17} /></button>
        </header>
        <div className="modal-content">
          <label className="field-wrap">
            <span className="field-label">Subject</span>
            <input className="field" readOnly value={draft.subject} />
          </label>
          <label className="field-wrap">
            <span className="field-label">Message</span>
            <textarea className="field email-body" onChange={event => setBody(event.target.value)} rows={11} value={body} />
          </label>
          {copyError && <div className="alert alert-error" role="alert">{copyError}</div>}
          <div className="modal-actions">
            <button className="button" onClick={openMailto} type="button"><Mail size={14} aria-hidden="true" /> Open in mail app</button>
            <button className="button button-secondary" onClick={copyAll} type="button">{copied ? "Copied" : "Copy draft"}</button>
          </div>
          <p className="modal-footnote">Review and personalise this draft before sending.</p>
        </div>
      </section>
    </div>
  );
}

export default function ApplicationsPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(initialForm);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [draftLoading, setDraftLoading] = useState<string | null>(null);
  const [draftError, setDraftError] = useState("");

  const applicationsQuery = useQuery({
    queryKey: ["applications"],
    queryFn: async () => (await api.get<Application[]>("/applications")).data,
  });

  const addMutation = useMutation({
    mutationFn: (body: typeof form) => api.post("/applications", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["applications"] });
      qc.invalidateQueries({ queryKey: ["analytics"] });
      setShowForm(false);
      setForm(initialForm);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => api.patch("/applications/" + id, { status }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["applications"] });
      qc.invalidateQueries({ queryKey: ["analytics"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete("/applications/" + id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["applications"] });
      qc.invalidateQueries({ queryKey: ["analytics"] });
    },
  });

  async function handleDraftEmail(applicationId: string) {
    setDraftLoading(applicationId);
    setDraftError("");
    try {
      const response = await api.post<Draft>("/outreach/draft", { application_id: applicationId });
      setDraft(response.data);
    } catch {
      setDraftError("We couldn’t create an email draft. Check your connection and try again.");
    } finally {
      setDraftLoading(null);
    }
  }

  const applications = applicationsQuery.data ?? [];
  const mutationError = addMutation.isError
    ? "This application couldn’t be added. Check the required fields and try again."
    : updateMutation.isError
      ? "The status couldn’t be updated. Please try again."
      : deleteMutation.isError
        ? "This application couldn’t be deleted. Please try again."
        : "";

  return (
    <div className="page-wrap">
      {draft && <EmailModal draft={draft} onClose={() => setDraft(null)} />}
      <header className="page-head">
        <div>
          <div className="eyebrow">Keep your momentum</div>
          <h1 className="page-title">Applications</h1>
          <p className="page-description">Every role you’re pursuing, and the next step for each.</p>
        </div>
        <button className="button" onClick={() => setShowForm(value => !value)} type="button">
          <Plus size={15} aria-hidden="true" /> {showForm ? "Close form" : "Add application"}
        </button>
      </header>

      {showForm && (
        <form className="panel application-form" onSubmit={event => { event.preventDefault(); addMutation.mutate(form); }}>
          <div className="form-heading"><div><h2 className="section-title">Add an application</h2><p className="section-caption">Keep the important details and follow-ups together.</p></div></div>
          <div className="form-grid">
            <label className="field-wrap"><span className="field-label">Company <span className="required-mark">*</span></span><input className="field" onChange={event => setForm(value => ({ ...value, company: event.target.value }))} placeholder="Company name" required value={form.company} /></label>
            <label className="field-wrap"><span className="field-label">Role <span className="required-mark">*</span></span><input className="field" onChange={event => setForm(value => ({ ...value, role: event.target.value }))} placeholder="Role or program" required value={form.role} /></label>
            <label className="field-wrap"><span className="field-label">Job link</span><input className="field" onChange={event => setForm(value => ({ ...value, job_link: event.target.value }))} placeholder="https://" type="url" value={form.job_link} /></label>
            <label className="field-wrap"><span className="field-label">Contact email</span><input className="field" onChange={event => setForm(value => ({ ...value, hr_contact: event.target.value }))} placeholder="name@company.com" type="email" value={form.hr_contact} /></label>
            <label className="field-wrap"><span className="field-label">Current status</span><select className="field" onChange={event => setForm(value => ({ ...value, status: event.target.value }))} value={form.status}>{statuses.map(status => <option key={status} value={status}>{status}</option>)}</select></label>
            <label className="field-wrap"><span className="field-label">Notes</span><input className="field" onChange={event => setForm(value => ({ ...value, notes: event.target.value }))} placeholder="A detail to remember" value={form.notes} /></label>
          </div>
          <div className="form-actions">
            <button className="button" disabled={addMutation.isPending} type="submit">{addMutation.isPending ? "Adding…" : "Save application"}</button>
            <button className="button button-quiet" onClick={() => { setShowForm(false); addMutation.reset(); }} type="button">Cancel</button>
          </div>
        </form>
      )}

      {mutationError && <div className="alert alert-error action-alert" role="alert">{mutationError}</div>}
      {draftError && <div className="alert alert-error action-alert" role="alert">{draftError}</div>}

      {applicationsQuery.isLoading ? (
        <div className="application-loading" aria-label="Loading applications">{Array.from({ length: 4 }, (_, index) => <div className="skeleton" key={index} />)}</div>
      ) : applicationsQuery.isError ? (
        <div className="panel empty-state"><div><span className="empty-icon"><BriefcaseBusiness size={18} aria-hidden="true" /></span><p className="empty-title">Your applications couldn’t load.</p><p className="empty-copy">Check your connection and try again.</p><button className="button button-secondary empty-action" onClick={() => applicationsQuery.refetch()}>Try again</button></div></div>
      ) : applications.length === 0 ? (
        <div className="panel empty-state">
          <div>
            <span className="empty-icon"><BriefcaseBusiness size={18} aria-hidden="true" /></span>
            <p className="empty-title">Your tracker starts with one role.</p>
            <p className="empty-copy">Add an application or save a role from Opportunities to keep your next steps in one place.</p>
            <div className="empty-actions"><button className="button" onClick={() => setShowForm(true)} type="button"><Plus size={14} /> Add an application</button><Link className="button button-secondary" href="/dashboard/opportunities">Explore roles <ArrowRight size={14} /></Link></div>
          </div>
        </div>
      ) : (
        <section className="table-wrap">
          <table className="data-table applications-table">
            <caption className="sr-only">Your tracked job applications</caption>
            <thead><tr>{["Company", "Role", "Status", "Contact", "Actions"].map(heading => <th key={heading} scope="col">{heading}</th>)}</tr></thead>
            <tbody>
              {applications.map(application => (
                <tr key={application.id}>
                  <td><span className="table-company"><span className="company-avatar">{application.company?.trim().slice(0, 1).toUpperCase() || "•"}</span><strong>{application.company}</strong></span></td>
                  <td>{application.job_link ? <a className="table-link" href={application.job_link} rel="noreferrer noopener" target="_blank">{application.role}</a> : application.role}</td>
                  <td><select aria-label={`Status for ${application.role} at ${application.company}`} className={`status-select status-${application.status}`} disabled={updateMutation.isPending} onChange={event => updateMutation.mutate({ id: application.id, status: event.target.value })} value={application.status}>{statuses.map(status => <option key={status} value={status}>{status}</option>)}</select></td>
                  <td>{application.hr_contact || <span className="muted-value">Not added</span>}</td>
                  <td>
                    <div className="table-actions">
                      <button className="table-action-email" disabled={draftLoading === application.id} onClick={() => handleDraftEmail(application.id)} type="button"><Mail size={13} aria-hidden="true" /> {draftLoading === application.id ? "Drafting…" : "Draft email"}</button>
                      <button aria-label={`Delete ${application.role} at ${application.company}`} className="table-action-delete" disabled={deleteMutation.isPending} onClick={() => { if (window.confirm(`Delete your ${application.role} application at ${application.company}?`)) deleteMutation.mutate(application.id); }} type="button"><Trash2 size={13} aria-hidden="true" /><span className="sr-only">Delete</span></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
      {!applicationsQuery.isLoading && applications.length > 0 && <p className="table-count">{applications.length} {applications.length === 1 ? "application" : "applications"} in your tracker</p>}
    </div>
  );
}
