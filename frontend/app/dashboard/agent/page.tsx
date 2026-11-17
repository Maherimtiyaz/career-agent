"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowUpRight,
  Bot,
  CheckCircle2,
  CircleDot,
  Clock,
  ExternalLink,
  Loader2,
  Mail,
  PenLine,
  Search,
  ShieldCheck,
  Sparkles,
  UserRound,
  XCircle,
  Zap,
} from "lucide-react";
import api from "@/lib/api";

// ---------- Types (mirror backend/app/agents/schemas.py) ----------

type RunStatus = "pending" | "planning" | "executing" | "awaiting_approval" | "completed" | "failed" | "cancelled";
type StepStatus = "pending" | "running" | "ok" | "failed" | "skipped";
type ContactSource = "job_posting" | "crustdata" | "crustdata_simulated";

interface StepResult {
  tool: string;
  ok: boolean;
  data: unknown;
  error?: string | null;
  duration_ms?: number | null;
  credits_spent?: number;
}

interface AgentStep {
  index: number;
  call: { tool: string; args: Record<string, unknown>; rationale?: string | null };
  status: StepStatus;
  result: StepResult | null;
}

interface ApprovalRequest {
  recipient_email: string;
  recipient_name?: string | null;
  contact_title?: string | null;
  contact_source?: ContactSource | null;
  company?: string | null;
  role?: string | null;
  opportunity_url?: string | null;
  subject: string;
  body: string;
}

interface AgentRun {
  id: string;
  goal: { prompt: string; max_steps: number; credit_budget: number; dry_run: boolean };
  status: RunStatus;
  plan: AgentStep[];
  credits_used: number;
  error?: string | null;
  pending_approval: ApprovalRequest | null;
  final_email: ApprovalRequest | null;
}

interface OutreachLead {
  id: string;
  company?: string | null;
  role?: string | null;
  opportunity_url?: string | null;
  contact_name?: string | null;
  contact_title?: string | null;
  contact_email?: string | null;
  contact_source?: ContactSource | null;
  status: string;
  error_message?: string | null;
  email_subject?: string | null;
  credit_cost: number;
  created_at?: string | null;
}

// ---------- Display helpers ----------

const PRESET_GOALS = [
  "Find an ML internship that fits my skills and draft a personalized email to someone on the hiring team.",
  "Find a remote backend engineering role and reach out to an engineering manager there.",
  "Find an entry-level security role and draft outreach to the recruiter.",
];

const TOOL_META: Record<string, { label: string; Icon: typeof Bot }> = {
  db_search_opportunities: { label: "Search opportunities", Icon: Search },
  crustdata_person_search: { label: "Find hiring contacts", Icon: UserRound },
  crustdata_person_enrich: { label: "Enrich contact", Icon: Sparkles },
  draft_email: { label: "Draft personalized email", Icon: PenLine },
  request_approval: { label: "Request your approval", Icon: ShieldCheck },
  send_email: { label: "Send email", Icon: Mail },
};

const RUN_STATUS: Record<RunStatus, { label: string; cls: string }> = {
  pending: { label: "Starting", cls: "status-blue" },
  planning: { label: "Planning", cls: "status-blue" },
  executing: { label: "Working", cls: "status-blue" },
  awaiting_approval: { label: "Waiting for you", cls: "status-warning" },
  completed: { label: "Completed", cls: "status-success" },
  failed: { label: "Failed", cls: "status-danger" },
  cancelled: { label: "Rejected", cls: "status-neutral" },
};

const LEAD_STATUS: Record<string, { label: string; cls: string }> = {
  pending_approval: { label: "Awaiting approval", cls: "status-warning" },
  approved: { label: "Approved", cls: "status-blue" },
  sent: { label: "Sent", cls: "status-success" },
  failed: { label: "Delivery failed", cls: "status-danger" },
  skipped: { label: "Rejected", cls: "status-neutral" },
};

const SOURCE_META: Record<ContactSource, { label: string; cls: string; hint: string }> = {
  job_posting: { label: "From job posting", cls: "tag-green", hint: "Application email published on the listing" },
  crustdata: { label: "Crustdata · live", cls: "tag-green", hint: "Found and enriched via Crustdata people data" },
  crustdata_simulated: {
    label: "Simulated contact",
    cls: "tag-amber",
    hint: "Crustdata dry-run mode: placeholder person, not a real contact",
  },
};

function SourceTag({ source }: { source?: ContactSource | null }) {
  if (!source) return null;
  const meta = SOURCE_META[source];
  return (
    <span className={`tag ${meta.cls}`} title={meta.hint}>
      {meta.label}
    </span>
  );
}

function extractError(err: unknown, fallback: string): string {
  const e = err as { response?: { data?: { detail?: unknown } } };
  const detail = e?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (err instanceof Error) return err.message;
  return fallback;
}

function summarize(step: AgentStep): string | null {
  const r = step.result;
  if (!r) return null;
  if (!r.ok) return r.error ?? "Failed";
  const d = r.data as Record<string, unknown> | Record<string, unknown>[] | null;
  switch (step.call.tool) {
    case "db_search_opportunities": {
      const rows = (d as Record<string, unknown>[]) ?? [];
      if (!rows.length) return `No matches for “${String(step.call.args.query ?? "")}”`;
      return `${rows.length} match${rows.length > 1 ? "es" : ""} · top: ${rows[0].title} @ ${rows[0].company}`;
    }
    case "crustdata_person_search": {
      const rows = (d as Record<string, unknown>[]) ?? [];
      return rows.length
        ? `${rows.length} people · ${rows.slice(0, 3).map((p) => `${p.name} (${p.title ?? "?"})`).join(", ")}`
        : "No people found";
    }
    case "crustdata_person_enrich": {
      const p = d as Record<string, unknown>;
      return p?.email ? `${p.name ?? "Contact"} · ${p.email}` : "No email on this profile";
    }
    case "draft_email":
      return `“${(d as Record<string, unknown>)?.subject ?? ""}”`;
    case "request_approval":
      return "Lead saved. Paused for your review.";
    case "send_email":
      return String((d as Record<string, unknown>)?.note ?? "Sent");
    default:
      return null;
  }
}

type StageState = "todo" | "active" | "done" | "failed";

function computeStages(run: AgentRun | null): { label: string; state: StageState }[] {
  const ok = (tool: string) => run?.plan.some((s) => s.call.tool === tool && s.status === "ok") ?? false;
  const foundRoles =
    run?.plan.some(
      (s) => s.call.tool === "db_search_opportunities" && s.status === "ok" && Array.isArray(s.result?.data) && (s.result?.data as unknown[]).length > 0
    ) ?? false;
  const done = [
    foundRoles,
    ok("crustdata_person_enrich") || ok("draft_email"),
    ok("draft_email"),
    run ? ["completed", "cancelled"].includes(run.status) || ok("send_email") : false,
    ok("send_email"),
  ];
  const labels = ["Discover", "Contact", "Personalize", "Approve", "Send"];
  const firstOpen = done.findIndex((d) => !d);
  return labels.map((label, i) => {
    let state: StageState = done[i] ? "done" : "todo";
    if (run && i === firstOpen) {
      if (run.status === "failed") state = "failed";
      else if (run.status === "executing" || run.status === "awaiting_approval") state = "active";
    }
    if (run?.status === "cancelled" && i === 3) state = "failed";
    return { label, state };
  });
}

// ---------- Page ----------

export default function AgentPage() {
  const queryClient = useQueryClient();
  const [prompt, setPrompt] = useState(PRESET_GOALS[0]);
  const [runId, setRunId] = useState<string | null>(null);
  const [editedSubject, setEditedSubject] = useState("");
  const [editedBody, setEditedBody] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  const leadsQuery = useQuery({
    queryKey: ["agent-leads"],
    queryFn: async () => (await api.get<OutreachLead[]>("/agent/leads")).data,
  });

  const runQuery = useQuery({
    queryKey: ["agent-run", runId],
    enabled: !!runId,
    queryFn: async () => (await api.get<AgentRun>(`/agent/run/${runId}`)).data,
    refetchInterval: (q) => (q.state.data?.status === "executing" || !q.state.data ? 1000 : false),
  });
  const run = runId ? runQuery.data ?? null : null;

  // Prefill the editable draft when the agent pauses for approval.
  const pending = run?.pending_approval ?? null;
  useEffect(() => {
    if (pending) {
      setEditedSubject(pending.subject);
      setEditedBody(pending.body);
      queryClient.invalidateQueries({ queryKey: ["agent-leads"] });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run?.id, pending?.subject, pending?.body]);

  const startRun = useMutation({
    mutationFn: async () =>
      (await api.post<AgentRun>("/agent/run", { prompt, max_steps: 10, credit_budget: 20, dry_run: true })).data,
    onMutate: () => setActionError(null),
    onSuccess: (newRun) => {
      queryClient.setQueryData(["agent-run", newRun.id], newRun);
      setRunId(newRun.id);
    },
    onError: (err) => setActionError(extractError(err, "Could not start the agent")),
  });

  const decide = useMutation({
    mutationFn: async (approved: boolean) =>
      (
        await api.post<AgentRun>(`/agent/run/${runId}/approve`, {
          approved,
          edited_subject: approved ? editedSubject : null,
          edited_body: approved ? editedBody : null,
        })
      ).data,
    onMutate: () => setActionError(null),
    onSuccess: (updated) => {
      queryClient.setQueryData(["agent-run", updated.id], updated);
      queryClient.invalidateQueries({ queryKey: ["agent-leads"] });
    },
    onError: (err) => setActionError(extractError(err, "Could not record your decision")),
  });

  const busy = startRun.isPending || run?.status === "executing";
  const stages = computeStages(run);
  const leads = leadsQuery.data ?? [];
  const lastStep = run?.plan[run.plan.length - 1];
  const thinking = run?.status === "executing" && lastStep?.status !== "running";
  const finalEmail = run?.final_email ?? null;

  return (
    <div className="page-wrap">
      <header className="page-head">
        <div>
          <div className="eyebrow">Outreach agent</div>
          <h1 className="page-title">Tell the agent what you want next.</h1>
          <p className="page-description">
            It finds a matching opportunity, identifies who to contact, and writes a personalized email.
            Nothing is sent until you approve it.
          </p>
        </div>
        <span className="page-context" title="Emails are simulated. Nothing is delivered.">
          <ShieldCheck size={13} aria-hidden="true" /> Demo mode · no real emails
        </span>
      </header>

      {/* Goal input */}
      <section className="panel panel-pad agent-goal">
        <label className="field-label" htmlFor="agent-goal">
          Your goal
        </label>
        <textarea
          id="agent-goal"
          className="field agent-textarea"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          disabled={busy}
          placeholder="e.g. Find a data science internship and reach out to the hiring manager"
        />
        <div className="agent-presets">
          {PRESET_GOALS.map((g) => (
            <button key={g} type="button" className="agent-chip" disabled={busy} onClick={() => setPrompt(g)}>
              {g.split(" and ")[0]}
            </button>
          ))}
        </div>
        <div className="agent-goal-footer">
          <span className="section-caption">Uses your profile for personalization · up to 10 steps · 20-credit budget</span>
          <button className="button" onClick={() => startRun.mutate()} disabled={busy || prompt.trim().length < 5}>
            {busy ? <Loader2 size={15} className="spin" /> : <Bot size={15} />}
            {busy ? "Agent working…" : "Run agent"}
          </button>
        </div>
        {actionError && <div className="alert alert-error">{actionError}</div>}
      </section>

      {/* Journey stages */}
      {run && (
        <ol className="agent-stages" aria-label="Agent progress">
          {stages.map((s, i) => (
            <li key={s.label} className={`agent-stage agent-stage-${s.state}`}>
              <span className="agent-stage-dot">
                {s.state === "done" ? <CheckCircle2 size={14} /> : s.state === "failed" ? <XCircle size={14} /> : s.state === "active" ? <Loader2 size={14} className="spin" /> : i + 1}
              </span>
              {s.label}
            </li>
          ))}
        </ol>
      )}

      {run && (
        <div className="agent-grid">
          {/* Live trace */}
          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2 className="section-title">Agent trace</h2>
                <p className="section-caption">Each decision the agent made, live</p>
              </div>
              <div className="agent-trace-meta">
                <span className={`status-pill ${RUN_STATUS[run.status].cls}`}>{RUN_STATUS[run.status].label}</span>
                <span className="agent-credits" title="Crustdata credits spent this run">
                  <Zap size={12} /> {run.credits_used.toFixed(2)} credits
                </span>
              </div>
            </div>
            <ol className="agent-trace">
              {run.plan.map((step) => {
                const meta = TOOL_META[step.call.tool] ?? { label: step.call.tool, Icon: CircleDot };
                const summary = summarize(step);
                return (
                  <li key={step.index} className={`agent-step agent-step-${step.status}`}>
                    <span className="agent-step-icon">
                      {step.status === "running" ? <Loader2 size={15} className="spin" /> : step.status === "ok" ? <CheckCircle2 size={15} /> : step.status === "failed" ? <XCircle size={15} /> : <CircleDot size={15} />}
                    </span>
                    <div className="agent-step-body">
                      <div className="agent-step-title">
                        <meta.Icon size={13} aria-hidden="true" /> {meta.label}
                        {step.result?.duration_ms != null && <span className="agent-step-time">{(step.result.duration_ms / 1000).toFixed(1)}s</span>}
                        {!!step.result?.credits_spent && <span className="agent-step-time">{step.result.credits_spent.toFixed(2)} cr</span>}
                      </div>
                      {step.call.rationale && <p className="agent-step-why">{step.call.rationale}</p>}
                      {summary && <p className={step.result?.ok === false ? "agent-step-out agent-step-err" : "agent-step-out"}>{summary}</p>}
                    </div>
                  </li>
                );
              })}
              {(thinking || (startRun.isPending && !run.plan.length)) && (
                <li className="agent-step agent-step-running">
                  <span className="agent-step-icon"><Loader2 size={15} className="spin" /></span>
                  <div className="agent-step-body"><div className="agent-step-title">Thinking about the next step…</div></div>
                </li>
              )}
            </ol>
            {run.status === "failed" && run.error && <div className="alert alert-error agent-inline-alert">{run.error}</div>}
          </section>

          {/* Result: opportunity + contact */}
          <section className="panel panel-pad agent-result">
            <h2 className="section-title">What the agent found</h2>
            {finalEmail ? (
              <>
                <div className="agent-fact">
                  <span className="agent-fact-label">Opportunity</span>
                  <span className="agent-fact-value">{finalEmail.role ?? "—"}</span>
                  <span className="agent-fact-sub">
                    {finalEmail.company}
                    {finalEmail.opportunity_url && (
                      <a className="text-link agent-posting-link" href={finalEmail.opportunity_url} target="_blank" rel="noreferrer">
                        View posting <ExternalLink size={11} />
                      </a>
                    )}
                  </span>
                </div>
                <div className="agent-fact">
                  <span className="agent-fact-label">Contact</span>
                  <span className="agent-fact-value">{finalEmail.recipient_name || "Hiring team"}</span>
                  <span className="agent-fact-sub">
                    {finalEmail.contact_title ? `${finalEmail.contact_title} · ` : ""}
                    {finalEmail.recipient_email}
                  </span>
                  <SourceTag source={finalEmail.contact_source} />
                </div>
              </>
            ) : (
              <p className="section-caption">
                {run.status === "executing" ? "Results appear here as the agent works." : "No draft was produced in this run."}
              </p>
            )}
          </section>
        </div>
      )}

      {/* Human approval */}
      {run?.status === "awaiting_approval" && pending && (
        <section className="panel panel-pad agent-approval">
          <div className="agent-approval-head">
            <Clock size={17} aria-hidden="true" />
            <div>
              <h2 className="section-title">Your approval is required</h2>
              <p className="section-caption">
                Review and edit the draft. The agent cannot send on its own. Only your click sends exactly what you see here.
              </p>
            </div>
          </div>
          <div className="agent-to">
            <span className="field-label">To</span>
            <span>
              {pending.recipient_name ? `${pending.recipient_name} ` : ""}&lt;{pending.recipient_email}&gt;
            </span>
            <SourceTag source={pending.contact_source} />
          </div>
          <label className="field-label" htmlFor="agent-subject">Subject</label>
          <input id="agent-subject" className="field" value={editedSubject} onChange={(e) => setEditedSubject(e.target.value)} disabled={decide.isPending} />
          <label className="field-label agent-gap" htmlFor="agent-body">Body</label>
          <textarea id="agent-body" className="field agent-body" value={editedBody} onChange={(e) => setEditedBody(e.target.value)} disabled={decide.isPending} />
          <div className="agent-approval-actions">
            <button className="button" onClick={() => decide.mutate(true)} disabled={decide.isPending || !editedBody.trim() || !editedSubject.trim()}>
              {decide.isPending ? <Loader2 size={15} className="spin" /> : <CheckCircle2 size={15} />} Approve &amp; send
            </button>
            <button className="button button-quiet" onClick={() => decide.mutate(false)} disabled={decide.isPending}>
              <XCircle size={15} /> Reject
            </button>
          </div>
        </section>
      )}

      {run?.status === "completed" && (
        <div className="alert alert-success agent-outcome">
          <CheckCircle2 size={15} /> Approved and sent to {finalEmail?.recipient_email}. Demo mode: delivery was simulated and nothing left this machine. The lead is marked <strong>sent</strong> below.
        </div>
      )}
      {run?.status === "cancelled" && (
        <div className="alert alert-info agent-outcome">You rejected the draft. Nothing was sent, and the lead is marked rejected.</div>
      )}

      {/* Lead history */}
      <section className="panel agent-leads">
        <div className="panel-heading">
          <div>
            <h2 className="section-title">Outreach history</h2>
            <p className="section-caption">Every lead the agent created, with where the contact came from</p>
          </div>
          <span className="status-pill status-neutral">{leads.length} leads</span>
        </div>
        {leadsQuery.isLoading ? (
          <div className="panel-pad"><div className="skeleton" style={{ height: 80 }} /></div>
        ) : leads.length === 0 ? (
          <div className="empty-state">
            <div>
              <div className="empty-icon"><Mail size={20} /></div>
              <p className="empty-title">No outreach yet</p>
              <p className="empty-copy">Run the agent above. Each draft you review is saved here with its status.</p>
            </div>
          </div>
        ) : (
          <div className="table-wrap agent-table">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Opportunity</th>
                  <th>Contact</th>
                  <th>Source</th>
                  <th>Subject</th>
                  <th>Status</th>
                  <th style={{ textAlign: "right" }}>Credits</th>
                </tr>
              </thead>
              <tbody>
                {leads.map((lead) => {
                  const s = LEAD_STATUS[lead.status] ?? { label: lead.status, cls: "status-neutral" };
                  return (
                    <tr key={lead.id}>
                      <td>
                        <div className="agent-cell-main">{lead.role ?? "—"}</div>
                        <div className="agent-cell-sub">
                          {lead.company ?? ""}
                          {lead.opportunity_url && (
                            <a href={lead.opportunity_url} target="_blank" rel="noreferrer" className="text-link"> <ArrowUpRight size={11} /></a>
                          )}
                        </div>
                      </td>
                      <td>
                        <div className="agent-cell-main">{lead.contact_name ?? "Hiring team"}</div>
                        <div className="agent-cell-sub">{lead.contact_email ?? "—"}</div>
                      </td>
                      <td><SourceTag source={lead.contact_source} /></td>
                      <td className="agent-cell-subject">{lead.email_subject ?? "—"}</td>
                      <td><span className={`status-pill ${s.cls}`} title={lead.error_message ?? undefined}>{s.label}</span></td>
                      <td style={{ textAlign: "right" }}>{lead.credit_cost.toFixed(2)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
