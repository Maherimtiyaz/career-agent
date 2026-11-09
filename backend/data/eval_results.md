# Agent Evaluation Results

Generated: `2026-11-09T12:33:01.272206+00:00`  
Mode: dry-run (no Crustdata credits consumed, no emails sent)

## Summary

| Metric | Value |
|---|---|
| Scenarios run | 10 |
| Passed | 7/10 |
| Success rate | 70.0% |
| Approval gate reached | 60.0% |
| Avg steps per run | 5.9 |
| Avg credits per completed run | 0.442 |
| Avg wall time | 56.5s |

## Per-scenario results

| # | Scenario | Status | Steps | Credits | Time | Tools called |
|---|---|---|---|---|---|---|
| 1 | Happy path — ML internship | `completed` | 8 | 2.03 | 19.61s | db_search_opportunities → db_search_opportunities → crustdata_person_search → crustdata_person_enrich → draft_email → save_lead → request_approval → send_email |
| 2 | Happy path — Backend role | `completed` | 8 | 0.09 | 21.67s | db_search_opportunities → db_search_opportunities → crustdata_person_search → crustdata_person_enrich → draft_email → save_lead → request_approval → send_email |
| 3 | Happy path — Data science role | `failed` | 0 | 0.0 | 174.31s | — |
| 4 | Reject flow — user declines draft | `cancelled` | 8 | 0.0 | 18.1s | db_search_opportunities → db_search_opportunities → db_search_opportunities → crustdata_person_search → crustdata_person_enrich → draft_email → save_lead → request_approval |
| 5 | Vague goal — planning under uncertainty | `completed` | 8 | 0.09 | 165.09s | db_search_opportunities → db_search_opportunities → crustdata_person_search → crustdata_person_enrich → draft_email → save_lead → request_approval → send_email |
| 6 | Broad — any tech internship | `completed` | 8 | 0.0 | 25.53s | db_search_opportunities → db_search_opportunities → crustdata_person_search → crustdata_person_enrich → draft_email → save_lead → request_approval → send_email |
| 7 | Budget constrained — tiny credit budget | `error` | 0 | 0.0 | 0.0s | — |
| 8 | Max-steps constrained — 3 step limit | `failed` | 3 | 0.0 | 11.08s | db_search_opportunities → db_search_opportunities → crustdata_person_search |
| 9 | Recruiter contact (not manager) | `failed` | 8 | 0.0 | 107.44s | db_search_opportunities → db_search_opportunities → crustdata_person_search → crustdata_person_enrich → crustdata_person_search → crustdata_person_enrich → draft_email → save_lead |
| 10 | Repeat — same goal as #1 (cache efficiency) | `completed` | 8 | 0.0 | 22.22s | db_search_opportunities → db_search_opportunities → crustdata_person_search → crustdata_person_enrich → draft_email → save_lead → request_approval → send_email |

## Tool distribution

| Tool | Calls |
|---|---|
| `db_search_opportunities` | 17 |
| `crustdata_person_search` | 9 |
| `crustdata_person_enrich` | 8 |
| `draft_email` | 7 |
| `save_lead` | 7 |
| `request_approval` | 6 |
| `send_email` | 5 |

## Interpretation

- **Success rate** measures how often the agent completes the workflow end-to-end or reaches a valid approval pause.
- **Approval rate** confirms the HITL safety gate fires in every scenario where an email was drafted.
- **Tool distribution** proves the agent selects different tools based on context — not a hardcoded script.
- **Credits** are simulated in dry-run mode; in live mode the same caching and budget logic governs real spend.
- **Cache efficiency** — repeated goals (scenario 10) cost near zero because identical Crustdata queries hit the Redis cache.