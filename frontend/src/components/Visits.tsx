import { useMemo, useState } from "react";
import type { Visit } from "../api";
import { ACTION_LABEL, STRATEGY_LABEL, clock, fmt } from "../format";

const PAGE = 20;

export function VisitTable({ visits, runId, day }: { visits: Visit[]; runId: string; day: number }) {
  const [scope, setScope] = useState<"day" | "all">("day");
  const [type, setType] = useState("all");
  const [strategy, setStrategy] = useState("all");
  const [outcome, setOutcome] = useState("all");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);

  const rows = useMemo(() => {
    const q = query.trim().toUpperCase();
    return visits.filter((v) =>
      (scope === "all" || v.day === day) &&
      (type === "all" || v.driver_type === type) &&
      (strategy === "all" || v.strategy === strategy) &&
      (outcome === "all" || v.action === outcome) &&
      (!q || v.driver_id.includes(q)));
  }, [visits, scope, day, type, strategy, outcome, query]);

  const pages = Math.max(1, Math.ceil(rows.length / PAGE));
  const p = Math.min(page, pages - 1);
  const shown = rows.slice(p * PAGE, p * PAGE + PAGE);
  const reset = <T,>(fn: (v: T) => void) => (v: T) => { fn(v); setPage(0); };

  const select = (label: string, value: string, set: (v: string) => void, opts: [string, string][]) => (
    <label className="flex flex-col text-sm">
      <span className="text-slate">{label}</span>
      <select value={value} onChange={(e) => reset(set)(e.target.value)}
        className="mt-1 rounded-[4px] border border-stone bg-paper px-2 py-1.5">
        {opts.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
    </label>
  );

  return (
    <div>
      <div className="flex flex-wrap items-end gap-4">
        <div className="flex flex-col text-sm">
          <span className="text-slate">Show</span>
          <div className="seg mt-1" role="group" aria-label="Visit scope">
            <button aria-pressed={scope === "day"} onClick={() => reset(setScope)("day")}>Day {day}</button>
            <button aria-pressed={scope === "all"} onClick={() => reset(setScope)("all")}>All 60 days</button>
          </div>
        </div>
        {select("Driver type", type, setType, [["all", "All types"], ["urgent", "Urgent"], ["flexible", "Flexible"]])}
        {select("Driver rule", strategy, setStrategy, [["all", "All rules"], ...Object.entries(STRATEGY_LABEL)])}
        {select("Outcome", outcome, setOutcome, [["all", "All outcomes"], ...Object.entries(ACTION_LABEL)])}
        <label className="flex flex-col text-sm">
          <span className="text-slate">Driver ID</span>
          <input value={query} onChange={(e) => reset(setQuery)(e.target.value)} placeholder="D017"
            className="mt-1 w-28 rounded-[4px] border border-stone bg-paper px-2 py-1.5" />
        </label>
        <span className="num ml-auto text-sm text-slate" aria-live="polite">{rows.length} visits</span>
      </div>

      <div className="mt-4 overflow-x-auto">
        {rows.length === 0 ? (
          <p className="panel p-6 text-center text-slate">
            No visits match these filters. Clear a filter or switch to all 60 days.
          </p>
        ) : (
          <table className="data-table num">
            <caption className="sr-only">Visit-level results for {runId}</caption>
            <thead>
              <tr>
                <th>Day</th><th>Driver</th><th>Type</th><th>Rule</th><th>Bay</th>
                <th className="r">Arrive</th><th className="r">Start</th><th className="r">Full</th><th className="r">Release</th><th className="r">Leave</th>
                <th className="r">kWh</th><th className="r">Wait</th><th>Outcome</th><th className="r">Idle</th>
                <th className="r">Penalty</th><th className="r">Gross</th><th className="r">Net</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((v) => (
                <tr key={v.request_id}>
                  <td>{v.day}</td>
                  <td className="font-semibold">{v.driver_id}</td>
                  <td className="capitalize">{v.driver_type}</td>
                  <td>{STRATEGY_LABEL[v.strategy]}</td>
                  <td>{v.charger_id ?? "—"}</td>
                  <td className="r">{clock(v.arrival)}</td>
                  <td className="r">{clock(v.start)}</td>
                  <td className="r">{clock(v.finish)}</td>
                  <td className="r">{clock(v.release)}</td>
                  <td className="r">{clock(v.departure)}</td>
                  <td className="r">{fmt(v.delivered_kwh, 0)}/{fmt(v.requested_kwh, 0)}</td>
                  <td className="r">{v.waiting_slots}</td>
                  <td className={v.action === "unserved" || v.action === "departed_incomplete" ? "text-loss" : ""}>{ACTION_LABEL[v.action]}</td>
                  <td className="r">{v.idle_slots}</td>
                  <td className="r">{fmt(v.penalty, 0)}</td>
                  <td className="r">{fmt(v.gross_utility, 0)}</td>
                  <td className="r font-semibold">{fmt(v.net_utility, 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {rows.length > PAGE && (
        <nav className="mt-3 flex items-center justify-end gap-2 text-sm" aria-label="Table pages">
          <button className="btn-quiet" disabled={p === 0} onClick={() => setPage(p - 1)}>Previous</button>
          <span className="num text-slate">Page {p + 1} of {pages}</span>
          <button className="btn-quiet" disabled={p >= pages - 1} onClick={() => setPage(p + 1)}>Next</button>
        </nav>
      )}
      <p className="mt-3 text-sm text-slate">Times are boundaries from 08:00 in 30-minute slots. A dash marks a missing value (saved as NA): service never started or never finished.</p>
    </div>
  );
}
