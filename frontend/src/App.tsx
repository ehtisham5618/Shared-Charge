import { useCallback, useEffect, useState } from "react";
import {
  api, runId, type Comparison, type Demand, type EvoPoint, type GameTheory, type Meta, type PolicyId,
  type RunData, type StatRow, type Visit,
} from "./api";
import { DEMAND_LABEL, POLICY_LABEL, fmt } from "./format";
import { ErrorNote, Section, Skeleton } from "./components/bits";
import { Overview, type RunRow } from "./components/Overview";
import { SitePlan, SitePlanLegend } from "./components/SitePlan";
import { PolicyPairs, SeedStats } from "./components/PolicyComparison";
import { ControlResult, DriverTypes, Strategies } from "./components/Drivers";
import { Evolution } from "./components/Evolution";
import { Games } from "./components/Games";
import { VisitTable } from "./components/Visits";
import { Downloads, MiniCase, Provenance } from "./components/Provenance";
import { Sidebar, TABS, type Tab } from "./components/Sidebar";

type View = PolicyId | "compare";

interface Selected {
  p0: RunData;
  p1: RunData;
  v0: Visit[];
  v1: Visit[];
  comparison: Comparison;
}

const tabFromHash = (): Tab => {
  const h = window.location.hash.replace("#", "") as Tab;
  return TABS.some((t) => t.id === h) ? h : "overview";
};

function Wordmark() {
  return (
    <span className="flex items-center gap-2.5">
      <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true">
        <rect width="32" height="32" rx="7" fill="#1D232D" />
        <rect x="0.75" y="0.75" width="30.5" height="30.5" rx="6.5" fill="none" stroke="#2FBFAE" strokeOpacity="0.55" strokeWidth="1.5" />
        <path d="M9 7v18M23 7v18" stroke="#2FBFAE" strokeWidth="2.2" strokeLinecap="round" />
        <path d="M17.5 9l-5 8h4l-2 7 5-8h-4z" fill="#E8B04A" />
      </svg>
      <span className="font-display text-[1.55rem] font-semibold leading-none">Shared Charge</span>
    </span>
  );
}

export default function App() {
  const [tab, setTab] = useState<Tab>(tabFromHash);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [evo, setEvo] = useState<EvoPoint[] | null>(null);
  const [gt, setGt] = useState<GameTheory | null>(null);
  const [control, setControl] = useState<StatRow[] | null>(null);
  const [runs, setRuns] = useState<RunRow[]>([]);
  const [comparisons, setComparisons] = useState<Partial<Record<Demand, Comparison>>>({});
  const [bootError, setBootError] = useState<string | null>(null);

  const [demand, setDemand] = useState<Demand>("medium");
  const [view, setView] = useState<View>("compare");
  const [seed, setSeed] = useState(0);
  const [day, setDay] = useState(1);

  const [sel, setSel] = useState<Selected | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [toast, setToast] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    const onHash = () => setTab(tabFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  const openTab = (t: Tab) => {
    window.history.replaceState(null, "", `#${t}`);
    setTab(t);
    window.scrollTo({ top: 0 });
  };

  const boot = useCallback(() => {
    setBootError(null);
    Promise.all([
      api.meta(), api.evolutionary(), api.gameTheory(), api.control(),
      fetch("/api/summary-runs").then((r) => r.json() as Promise<RunRow[]>),
      api.comparison("low"), api.comparison("medium"), api.comparison("high"),
    ])
      .then(([m, e, g, c, r, lo, me, hi]) => {
        setMeta(m); setEvo(e); setGt(g); setControl(c.stats); setRuns(r);
        setComparisons({ low: lo, medium: me, high: hi });
      })
      .catch((e: Error) => setBootError(e.message));
  }, []);
  useEffect(boot, [boot]);

  const load = useCallback(() => {
    let live = true;
    setLoading(true);
    setError(null);
    const a = runId(demand, "P0", seed);
    const b = runId(demand, "P1", seed);
    Promise.all([api.run(a), api.run(b), api.visits(a), api.visits(b), api.comparison(demand)])
      .then(([p0, p1, v0, v1, comparison]) => { if (live) setSel({ p0, p1, v0, v1, comparison }); })
      .catch((e: Error) => { if (live) setError(e.message); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [demand, seed]);
  useEffect(load, [load]);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 6000);
    return () => clearTimeout(t);
  }, [toast]);

  const compare = view === "compare";
  const policy: PolicyId = view === "P1" ? "P1" : "P0";
  const shownIds = compare ? [runId(demand, "P0", seed), runId(demand, "P1", seed)] : [runId(demand, policy, seed)];

  const runAgain = async () => {
    setRunning(true);
    setToast(null);
    try {
      const results = await Promise.all(shownIds.map((id) => api.rerun(id)));
      const ok = results.every((r) => r.identical_to_saved);
      const ms = results.reduce((s, r) => s + r.elapsed_ms, 0);
      setToast({
        ok,
        text: ok
          ? `${results.length * 60} simulated days in ${fmt(ms, 0)} ms. Identical to the saved results.`
          : "The new run differs from the saved files. Run python -m shared_charge all.",
      });
      load();
    } catch (e) {
      setToast({ ok: false, text: `The experiment could not run: ${(e as Error).message}` });
    } finally {
      setRunning(false);
    }
  };

  if (bootError) {
    return <main className="mx-auto max-w-3xl p-8"><Wordmark /><div className="mt-8"><ErrorNote error={bootError} retry={boot} /></div></main>;
  }

  const showControls = tab !== "theory";
  const busy = loading ? "opacity-50 transition-opacity" : "transition-opacity";

  return (
    <div className="min-h-screen">
      <Sidebar tab={tab} onSelect={openTab}
        status={meta ? { ok: meta.mini_case.all_match, text: `${meta.manifest.main_runs + meta.manifest.control_runs} runs verified` } : undefined} />

      <header className="z-30 border-b border-stone bg-mineral/95 backdrop-blur md:sticky md:top-0 md:pl-[92px]">
        <form className="mx-auto flex max-w-[1240px] flex-wrap items-center gap-x-5 gap-y-3 px-4 py-3 sm:px-6"
          onSubmit={(e) => { e.preventDefault(); runAgain(); }} aria-label="Experiment settings">
          <span className="mr-2"><Wordmark /></span>
          {showControls && (
            <>
              <div className="seg" role="group" aria-label="Demand">
                {(["low", "medium", "high"] as Demand[]).map((d) => (
                  <button type="button" key={d} aria-pressed={demand === d} onClick={() => setDemand(d)}>{DEMAND_LABEL[d]}</button>
                ))}
              </div>
              <div className="seg" role="group" aria-label="Policy">
                <button type="button" aria-pressed={compare} onClick={() => setView("compare")}>P0 vs P1</button>
                <button type="button" aria-pressed={view === "P0"} onClick={() => setView("P0")}>P0 only</button>
                <button type="button" aria-pressed={view === "P1"} onClick={() => setView("P1")}>P1 only</button>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate">Seed</span>
                <div className="seg" role="group" aria-label="Seed">
                  {(meta?.seeds ?? [0, 1, 2, 3, 4]).map((s) => (
                    <button type="button" key={s} aria-pressed={seed === s} onClick={() => setSeed(s)} className="num">{s}</button>
                  ))}
                </div>
              </div>
              <button type="submit" className="btn-primary sm:ml-auto" disabled={running || loading}>
                {running ? "Running…" : "Run experiment"}
              </button>
            </>
          )}
        </form>
      </header>

      {toast && (
        <div role="status" className="panel fixed right-4 bottom-24 z-50 max-w-sm md:bottom-4 p-4 text-sm shadow-[0_16px_40px_-12px_rgba(0,0,0,.8)]">
          <p className={`font-semibold ${toast.ok ? "text-pine-deep" : "text-loss"}`}>{toast.ok ? "Experiment reproduced" : "Run problem"}</p>
          <p className="mt-1 text-slate">{toast.text}</p>
        </div>
      )}

      <div className="md:pl-[92px]">
      <main className="mx-auto max-w-[1240px] px-4 pt-8 pb-28 sm:px-6 md:pb-16" key={tab}>
        {error && <div className="mb-6"><ErrorNote error={error} retry={load} /></div>}

        {tab === "overview" && (
          !sel ? <Skeleton h={480} /> : (
            <div className={busy} aria-busy={loading}>
              <Overview p0={sel.p0.summary} p1={sel.p1.summary} view={view} runs={runs} comparisons={comparisons} demand={demand} />
            </div>
          )
        )}

        {tab === "site" && (
          <div className="view-in">
            <Section title={`Day ${day} at the site`} hint="Each bar is one real visit from the saved run. Hover a bar for details."
              aside={
                <div className="flex items-center gap-2">
                  <button className="btn-quiet" onClick={() => setDay(Math.max(1, day - 1))} disabled={day <= 1} aria-label="Previous day">‹</button>
                  <input type="range" min={1} max={meta?.site.days ?? 60} value={day} onChange={(e) => setDay(Number(e.target.value))}
                    className="w-40 accent-[#2FBFAE] sm:w-64" aria-label="Simulated day" />
                  <button className="btn-quiet" onClick={() => setDay(Math.min(60, day + 1))} disabled={day >= 60} aria-label="Next day">›</button>
                </div>
              }>
              {!sel ? <Skeleton h={380} /> : (
                <div className={`space-y-4 ${busy}`} aria-busy={loading}>
                  <SitePlanLegend />
                  {(compare || policy === "P0") && <div className="panel p-4 sm:p-5"><SitePlan visits={sel.v0} day={day} policy="P0" label={POLICY_LABEL.P0} /></div>}
                  {(compare || policy === "P1") && <div className="panel p-4 sm:p-5"><SitePlan visits={sel.v1} day={day} policy="P1" label={POLICY_LABEL.P1} /></div>}
                </div>
              )}
            </Section>
          </div>
        )}

        {tab === "drivers" && (
          !sel ? <Skeleton h={480} /> : (
            <div className={`view-in ${busy}`} aria-busy={loading}>
              <Section title="Who gains and who pays" hint={`${DEMAND_LABEL[demand]} demand, seed ${seed}`}>
                <DriverTypes p0={sel.p0.summary} p1={sel.p1.summary} comparison={sel.comparison} />
              </Section>
              <Section title="By driver rule" hint="Only Fee aware drivers change behaviour. Hold drivers keep holding and pay.">
                <div className="panel p-2 sm:p-4"><Strategies p0={sel.p0.summary} p1={sel.p1.summary} /></div>
              </Section>
              {control && <div className="py-6"><ControlResult stats={control} /></div>}
              <Section title="All measures" hint={`Seed ${seed} and all five seeds`}>
                <div className="space-y-6">
                  <PolicyPairs p0={sel.p0.summary} p1={sel.p1.summary} />
                  <div className="panel p-2 sm:p-4"><SeedStats comparison={sel.comparison} seed={seed} /></div>
                </div>
              </Section>
            </div>
          )
        )}

        {tab === "theory" && (
          <div className="view-in">
            <Section title="If drivers copy what works" hint="Evolutionary C/H model, 30 updates from x = 0.5">
              {evo ? <Evolution points={evo} /> : <Skeleton h={340} />}
            </Section>
            <Section title="The game behind the queue" hint="Teaching payoffs, not the simulator's energy formula">
              {gt ? <Games gt={gt} /> : <Skeleton h={260} />}
            </Section>
          </div>
        )}

        {tab === "data" && (
          !sel || !meta ? <Skeleton h={480} /> : (
            <div className="view-in">
              <Section title="Every visit" hint={compare ? `${sel.p1.run_id}. Choose “P0 only” for the baseline.` : (view === "P0" ? sel.p0.run_id : sel.p1.run_id)}>
                <VisitTable key={`${demand}-${seed}-${view}`} visits={view === "P0" ? sel.v0 : sel.v1}
                  runId={view === "P0" ? sel.p0.run_id : sel.p1.run_id} day={day} />
              </Section>
              <Section title="Downloads"><div className="panel p-5"><Downloads runIds={shownIds} /></div></Section>
              <Section title="Mini case check" hint="One charger, three drivers, P0, against mini_case_expected.json"><MiniCase mini={meta.mini_case} /></Section>
              <Section title="Settings and inputs">
                <Provenance settings={compare ? [sel.p0.settings, sel.p1.settings] : [policy === "P0" ? sel.p0.settings : sel.p1.settings]} />
              </Section>
            </div>
          )
        )}
      </main>

      <footer className="border-t border-stone">
        <p className="mx-auto max-w-[1240px] px-4 py-5 pb-28 text-sm text-faint sm:px-6 md:pb-5">
          Synthetic teaching data. Utility values are points, not prices.
        </p>
      </footer>
      </div>
    </div>
  );
}
