"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  ArrowRight,
  Bot,
  CheckCircle2,
  CircleDot,
  Clock,
  Loader2,
  Mail,
  MessageSquare,
  Sparkles,
  Target,
  User,
  XCircle,
  Zap,
} from "lucide-react";
import clsx from "clsx";
import api from "@/lib/api";

// ---------- Types ----------

type RunStatus =
  | "pending"
  | "planning"
  | "executing"
  | "awaiting_approval"
  | "completed"
  | "failed"
  | "cancelled";

type StepStatus = "pending" | "running" | "ok" | "failed" | "skipped";

interface AgentStepResult {
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
  result: AgentStepResult | null;
}

interface ApprovalRequest {
  run_id: string;
  step_index: number;
  kind: string;
  recipient_email: string;
  recipient_name?: string | null;
  subject: string;
  body: string;
}

interface AgentRun {
  id: string;
  user_id: string;
  goal: {
    prompt: string;
    max_steps: number;
    credit_budget: number;
    dry_run: boolean;
  };
  status: RunStatus;
  plan: AgentStep[];
  current_step: number;
  credits_used: number;
  error?: string | null;
  created_at: string;
  updated_at: string;
  pending_approval: ApprovalRequest | null;
}

interface OutreachLead {
  id: string;
  contact_name?: string | null;
  contact_title?: string | null;
  contact_email?: string | null;
  contact_linkedin?: string | null;
  status: string;
  email_subject?: string | null;
  email_draft?: string | null;
  credit_cost: number;
  created_at?: string | null;
  sent_at?: string | null;
}

// ---------- Helpers ----------

const TOOL_LABELS: Record<string, string> = {
  db_search_opportunities: "Search saved opportunities",
  crustdata_person_search: "Find contacts",
  crustdata_person_enrich: "Enrich contact",
  draft_email: "Draft email",
  save_lead: "Save lead",
  request_approval: "Request approval",
  send_email: "Send email",
};

const TOOL_ICONS: Record<string, typeof Bot> = {
  db_search_opportunities: Target,
  crustdata_person_search: User,
  crustdata_person_enrich: Sparkles,
  draft_email: MessageSquare,
  save_lead: CheckCircle2,
  request_approval: Clock,
  send_email: Mail,
};

const STATUS_STYLES: Record<string, { label: string; className: string }> = {
  pending: { label: "Pending", className: "status-neutral" },
  planning: { label: "Planning", className: "status-blue" },
  executing: { label: "Executing", className: "status-blue" },
  awaiting_approval: { label: "Awaiting approval", className: "status-warning" },
  completed: { label: "Completed", className: "status-success" },
  failed: { label: "Failed", className: "status-danger" },
  cancelled: { label: "Cancelled", className: "status-neutral" },
  pending_approval: { label: "Pending approval", className: "status-warning" },
  approved: { label: "Approved", className: "status-blue" },
  sent: { label: "Sent", className: "status-success" },
  skipped: { label: "Skipped", className: "status-neutral" },
};

function stepStatusIcon(status: StepStatus) {
  switch (status) {
    case "ok":
      return { Icon: CheckCircle2, className: "text-emerald-500" };
    case "failed":
      return { Icon: XCircle, className: "text-red-500" };
    case "skipped":
      return { Icon: CircleDot, className: "text-slate-400" };
    case "running":
      return { Icon: Loader2, className: "text-blue-500 animate-spin" };
    default:
      return { Icon: CircleDot, className: "text-slate-300" };
  }
}

function extractError(err: unknown, fallback: string): string {
  const e = err as { response?: { data?: { detail?: unknown } } };
  const detail = e?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (err instanceof Error) return err.message;
  return fallback;
}

function summarizeStepResult(result: AgentStepResult | null): string | null {
  if (!result) return null;
  if (!result.ok) return result.error ?? "Failed";
  if (Array.isArray(result.data)) return `${result.data.length} result(s)`;
  if (result.data && typeof result.data === "object") {
    const obj = result.data as Record<string, unknown>;
    if (typeof obj.lead_id === "string") return `lead ${obj.lead_id.slice(0, 8)}…`;
    if (typeof obj.subject === "string") return obj.subject;
  }
  return null;
}

// ---------- Page ----------

export default function AgentPage() {
  const queryClient = useQueryClient();
  const [prompt, setPrompt] = useState(
    "Find 1 ML internship from my saved opportunities and draft a personalized outreach email to a hiring contact."
  );
  const [currentRun, setCurrentRun] = useState<AgentRun | null>(null);
  const [editedSubject, setEditedSubject] = useState("");
  const [editedBody, setEditedBody] = useState("");
  const [runError, setRunError] = useState<string | null>(null);

  const leadsQuery = useQuery({
    queryKey: ["agent-leads"],
    queryFn: async () => (await api.get<OutreachLead[]>("/agent/leads")).data,
  });

  const startRunMutation = useMutation({
    mutationFn: async () => {
      setRunError(null);
      const res = await api.post<AgentRun>("/agent/run", {
        prompt,
        max_steps: 8,
        credit_budget: 20.0,
        dry_run: true,
      });
      return res.data;
    },
    onSuccess: (run) => {
      setCurrentRun(run);
      if (run.pending_approval) {
        setEditedSubject(run.pending_approval.subject);
        setEditedBody(run.pending_approval.body);
      }
      queryClient.invalidateQueries({ queryKey: ["agent-leads"] });
    },
    onError: (err) => setRunError(extractError(err, "Run failed")),
  });

  const approveMutation = useMutation({
    mutationFn: async ({ approved }: { approved: boolean }) => {
      if (!currentRun) throw new Error("No active run");
      const res = await api.post<AgentRun>(
        `/agent/run/${currentRun.id}/approve`,
        {
          approved,
          edited_subject: approved ? editedSubject : null,
          edited_body: approved ? editedBody : null,
        }
      );
      return res.data;
    },
    onSuccess: (run) => {
      setCurrentRun(run);
      queryClient.invalidateQueries({ queryKey: ["agent-leads"] });
    },
    onError: (err) => setRunError(extractError(err, "Approval failed")),
  });

  const isRunning = startRunMutation.isPending || approveMutation.isPending;
  const leads = leadsQuery.data ?? [];
  const traceStatus = currentRun ? STATUS_STYLES[currentRun.status] : null;

  return (
    <div className="space-y-6 text-slate-900 dark:text-slate-100">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Bot size={22} />
          Career Outreach Agent
        </h1>
        <p className="text-slate-600 dark:text-slate-400 mt-1">
          Give the agent a goal. It plans, finds contacts, drafts emails, and
          pauses for your approval before sending anything.
        </p>
      </div>

      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-6 space-y-4">
        <label className="text-sm font-medium block">Your goal</label>
        <textarea
          className="w-full min-h-[100px] px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          disabled={isRunning}
          placeholder="Describe what you want the agent to do..."
        />
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="text-xs text-slate-600 dark:text-slate-400">
            Dry-run mode (no real emails) &bull; Budget 20 credits &bull; Max 8 steps
          </div>
          <button
            onClick={() => startRunMutation.mutate()}
            disabled={isRunning || !prompt.trim()}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 dark:bg-slate-100 dark:hover:bg-slate-200 dark:text-slate-900 text-white text-sm font-medium disabled:opacity-50 transition"
          >
            {startRunMutation.isPending ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Running agent&hellip;
              </>
            ) : (
              <>
                <Bot size={16} />
                Run agent
              </>
            )}
          </button>
        </div>
        {runError && (
          <div className="text-sm text-red-600 dark:text-red-400 rounded-lg border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/40 px-3 py-2">
            {runError}
          </div>
        )}
      </div>

      {currentRun && (
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-6 space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <h2 className="font-semibold flex items-center gap-2">
              <Activity size={18} />
              Agent trace
            </h2>
            <div className="flex items-center gap-3 text-sm">
              {traceStatus && (
                <span
                  className={clsx(
                    "px-2 py-0.5 rounded-full text-xs font-medium",
                    traceStatus.className
                  )}
                >
                  {traceStatus.label}
                </span>
              )}
              <span className="text-slate-600 dark:text-slate-400 flex items-center gap-1">
                <Zap size={14} />
                {currentRun.credits_used.toFixed(2)} credits
              </span>
            </div>
          </div>

          <ol className="space-y-2">
            {currentRun.plan.map((step) => {
              const { Icon, className } = stepStatusIcon(step.status);
              const ToolIcon = TOOL_ICONS[step.call.tool] ?? ArrowRight;
              const summary = summarizeStepResult(step.result);
              return (
                <li
                  key={step.index}
                  className="flex items-start gap-3 p-3 rounded-lg border border-slate-100 dark:border-slate-800"
                >
                  <Icon size={18} className={clsx("mt-0.5 shrink-0", className)} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 text-sm font-medium text-slate-900 dark:text-slate-100">
                      <ToolIcon size={14} className="text-slate-400" />
                      {TOOL_LABELS[step.call.tool] ?? step.call.tool}
                    </div>
                    {summary && (
                      <div
                        className={clsx(
                          "text-xs mt-1 truncate",
                          step.result && !step.result.ok
                            ? "text-red-500"
                            : "text-slate-600 dark:text-slate-400"
                        )}
                      >
                        {summary}
                      </div>
                    )}
                    {step.result?.duration_ms != null && (
                      <div className="text-xs text-slate-400 mt-1">
                        {step.result.duration_ms}ms
                      </div>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>

          {currentRun.error && (
            <div className="text-sm text-red-600 dark:text-red-400">
              {currentRun.error}
            </div>
          )}
        </div>
      )}

      {currentRun?.pending_approval && (
        <div className="rounded-xl border-2 border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-950/20 p-6 space-y-4">
          <div className="flex items-center gap-2">
            <Clock size={18} className="text-amber-600 dark:text-amber-400" />
            <h2 className="font-semibold">Approval required</h2>
          </div>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            The agent has drafted an email. Review it below, edit if needed, then
            approve to send. Nothing is sent until you click Approve.
          </p>

          <div className="grid gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600 dark:text-slate-400 block">
                To
              </label>
              <div className="text-sm mt-0.5 text-slate-900 dark:text-slate-100"
                {currentRun.pending_approval.recipient_name ?? "Contact"}{" "}
                &lt;{currentRun.pending_approval.recipient_email}&gt;
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 dark:text-slate-400 block">
                Subject
              </label>
              <input
                type="text"
                className="w-full mt-1 px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm"
                value={editedSubject}
                onChange={(e) => setEditedSubject(e.target.value)}
                disabled={approveMutation.isPending}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 dark:text-slate-400 block">
                Body
              </label>
              <textarea
                className="w-full mt-1 min-h-[200px] px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm font-mono"
                value={editedBody}
                onChange={(e) => setEditedBody(e.target.value)}
                disabled={approveMutation.isPending}
              />
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={() => approveMutation.mutate({ approved: true })}
              disabled={approveMutation.isPending}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium disabled:opacity-50 transition"
            >
              {approveMutation.isPending ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Sending&hellip;
                </>
              ) : (
                <>
                  <CheckCircle2 size={16} />
                  Approve &amp; send
                </>
              )}
            </button>
            <button
              onClick={() => approveMutation.mutate({ approved: false })}
              disabled={approveMutation.isPending}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 text-sm font-medium disabled:opacity-50 transition"
            >
              <XCircle size={16} />
              Reject
            </button>
          </div>
        </div>
      )}

      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-6">
        <h2 className="font-semibold mb-4 flex items-center gap-2">
          <Mail size={18} />
          Outreach leads ({leads.length})
        </h2>
        {leadsQuery.isLoading ? (
          <div className="text-sm text-slate-600 dark:text-slate-400">Loading&hellip;</div>
        ) : leads.length === 0 ? (
          <div className="text-sm text-slate-600 dark:text-slate-400">
            No leads yet. Run the agent above.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b border-slate-200 dark:border-slate-700">
                  <th className="py-2 font-medium text-slate-700 dark:text-slate-300">Contact</th>
                  <th className="py-2 font-medium text-slate-700 dark:text-slate-300">Email</th>
                  <th className="py-2 font-medium text-slate-700 dark:text-slate-300">Subject</th>
                  <th className="py-2 font-medium text-slate-700 dark:text-slate-300">Status</th>
                  <th className="py-2 font-medium text-right">Credits</th>
                </tr>
              </thead>
              <tbody>
                {leads.map((lead) => {
                  const s = STATUS_STYLES[lead.status];
                  return (
                    <tr
                      key={lead.id}
                      className="border-b border-slate-100 dark:border-slate-800"
                    >
                      <td className="py-2">
                        <div className="font-medium">
                          {lead.contact_name ?? "\u2014"}
                        </div>
                        <div className="text-xs text-slate-600 dark:text-slate-400">
                          {lead.contact_title ?? ""}
                        </div>
                      </td>
                      <td className="py-2 text-xs">
                        {lead.contact_email ?? "\u2014"}
                      </td>
                      <td className="py-2 text-xs max-w-[240px] truncate">
                        {lead.email_subject ?? "\u2014"}
                      </td>
                      <td className="py-2">
                        <span
                          className={clsx(
                            "px-2 py-0.5 rounded-full text-xs",
                            s?.className ?? "status-neutral"
                          )}
                        >
                          {s?.label ?? lead.status}
                        </span>
                      </td>
                      <td className="py-2 text-right text-xs">
                        {lead.credit_cost.toFixed(2)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

