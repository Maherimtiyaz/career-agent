"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowDownToLine, ArrowRight, Check, Database, RefreshCw, Sheet } from "lucide-react";
import api from "@/lib/api";

interface ScrapeResult {
  source: string;
  inserted: number;
  error?: string;
}

interface SheetImportResult {
  inserted: number;
  skipped: number;
}

export default function ImportPage() {
  const qc = useQueryClient();
  const [url, setUrl] = useState("");
  const [sheetResult, setSheetResult] = useState<SheetImportResult | null>(null);
  const [sheetError, setSheetError] = useState("");

  const scrapeMutation = useMutation({
    mutationFn: () => api.post("/ingestion/run?source=all"),
    onSuccess: response => {
      qc.invalidateQueries({ queryKey: ["opportunities"] });
      qc.invalidateQueries({ queryKey: ["analytics"] });
      qc.invalidateQueries({ queryKey: ["ai-recommendations"] });
      return response;
    },
  });

  const sheetMutation = useMutation({
    mutationFn: (sheetUrl: string) => api.post<SheetImportResult>("/sheet/import", { sheet_url: sheetUrl }),
    onSuccess: response => {
      setSheetResult(response.data);
      setSheetError("");
      qc.invalidateQueries({ queryKey: ["applications"] });
      qc.invalidateQueries({ queryKey: ["analytics"] });
    },
    onError: (requestError: unknown) => {
      const detail = (requestError as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
      setSheetError(typeof detail === "string" ? detail : "The sheet couldn’t be imported. Check the link and try again.");
      setSheetResult(null);
    },
  });

  const scrapeResults = scrapeMutation.data?.data?.results as ScrapeResult[] | undefined;
  const totalInserted = scrapeResults?.reduce((total, result) => total + (result.inserted ?? 0), 0) ?? 0;
  const sourceNames = ["GSoC", "YC Jobs", "MLH Fellowship", "Devfolio"];

  return (
    <div className="page-wrap">
      <header className="page-head">
        <div><div className="eyebrow">Keep your data connected</div><h1 className="page-title">Data sources</h1><p className="page-description">Bring fresh opportunities and your existing tracker into Career Agent.</p></div>
        <span className="page-context"><Database size={14} aria-hidden="true" /> Connected to your workspace</span>
      </header>

      <div className="source-grid">
        <section className="panel source-card">
          <div className="source-card-top">
            <span className="source-icon"><RefreshCw size={17} aria-hidden="true" /></span>
            <span className="source-status"><span className="source-status-dot" /> Scheduled daily</span>
          </div>
          <div className="source-section-label">Opportunity discovery</div>
          <h2 className="source-title">Live platform sources</h2>
          <p className="source-description">Refresh opportunities from student programs, startup listings, and hackathon platforms. Scheduled refreshes run every 24 hours.</p>
          <div className="source-tags">{sourceNames.map(name => <span className="tag" key={name}>{name}</span>)}</div>
          <button className="button source-action" disabled={scrapeMutation.isPending} onClick={() => scrapeMutation.mutate()} type="button">
            <RefreshCw size={14} aria-hidden="true" /> {scrapeMutation.isPending ? "Refreshing sources…" : "Refresh sources"}
          </button>
          {scrapeMutation.isError && <div className="alert alert-error source-feedback" role="alert">We couldn’t refresh the sources. Check your connection and try again.</div>}
          {scrapeResults && (
            <div className={`source-results${scrapeResults.some(result => result.error) ? " source-results-warning" : ""}`} role="status">
              <div className="source-results-summary">
                <span className="source-results-icon">{scrapeResults.some(result => result.error) ? <Database size={15} /> : <Check size={15} />}</span>
                <span>{totalInserted ? `${totalInserted} new ${totalInserted === 1 ? "opportunity" : "opportunities"} added` : "Sources are up to date"}</span>
              </div>
              <div className="source-result-list">
                {scrapeResults.map(result => <div className="source-result-row" key={result.source}><span>{result.source}</span><span className={result.error ? "result-error" : "result-count"}>{result.error ? "Unavailable" : `+${result.inserted}`}</span></div>)}
              </div>
            </div>
          )}
        </section>

        <section className="panel source-card">
          <div className="source-card-top">
            <span className="source-icon source-icon-blue"><Sheet size={17} aria-hidden="true" /></span>
            <span className="source-status source-status-neutral">Personal tracker</span>
          </div>
          <div className="source-section-label">Bring your own data</div>
          <h2 className="source-title">Import a Google Sheet</h2>
          <p className="source-description">Move an existing application tracker into your workspace. Your sheet needs to be shared as “Anyone with the link can view.”</p>
          <div className="sheet-requirements"><span>Required columns</span><code>company</code><code>role</code></div>
          <form className="sheet-import-form" onSubmit={event => { event.preventDefault(); sheetMutation.mutate(url.trim()); }}>
            <label className="field-wrap" htmlFor="sheet-url">
              <span className="field-label">Google Sheets link</span>
              <input autoComplete="url" className="field" id="sheet-url" onChange={event => { setUrl(event.target.value); setSheetError(""); }} placeholder="https://docs.google.com/spreadsheets/…" required type="url" value={url} />
            </label>
            <button className="button" disabled={sheetMutation.isPending || !url.trim()} type="submit">
              {sheetMutation.isPending ? "Importing…" : <><ArrowDownToLine size={14} aria-hidden="true" /> Import tracker</>}
            </button>
          </form>
          {sheetError && <div className="alert alert-error source-feedback" role="alert">{sheetError}</div>}
          {sheetResult && <div className="alert alert-success source-feedback" role="status"><Check size={14} aria-hidden="true" /> {sheetResult.inserted} {sheetResult.inserted === 1 ? "row" : "rows"} added, {sheetResult.skipped} skipped.</div>}
        </section>
      </div>

      <div className="source-note"><ArrowRight size={14} aria-hidden="true" /><span>Newly imported applications are added to your tracker and reflected in Analytics.</span></div>
    </div>
  );
}
