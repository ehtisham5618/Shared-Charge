import { useMemo, useState } from "react";
import { CircleCheck, Clock3, SquareParking, Zap } from "lucide-react";
import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Comparison, Demand, PolicyId, Summary } from "../api";
import { DEMAND_LABEL, fmt, int, pct, signed } from "../format";
import { Delta } from "./bits";

/** Evenly spaced axis ticks with a clean step (1, 2, 2.5 or 5 times a power of ten). */
const axisTicks = (max: number, isShare: boolean) => {
  if (isShare) return [0, 0.25, 0.5, 0.75, 1];
  const raw = (max * 1.1) / 5;
  const p = 10 ** Math.floor(Math.log10(raw));
  const step = ([1, 2, 2.5, 5, 10].find((m) => m * p >= raw) ?? 10) * p;
  const top = Math.ceil((max * 1.1) / step) * step;
  return Array.from({ length: Math.round(top / step) + 1 }, (_, i) => +(i * step).toFixed(6));
};

export interface RunRow {
  run_id: string; seed: number; demand: Demand; policy: PolicyId; control_all_hold: boolean;
  [metric: string]: number | string | boolean;
}

const KPIS = [
  { key: "avg_wait_slots", icon: Clock3, label: "Average wait", unit: "slots", get: (s: Summary) => s.overall.avg_wait_slots, show: (v: number) => fmt(v, 2), digits: 2, scale: 1, suffix: "" },
  { key: "completion_rate", icon: CircleCheck, label: "Fully served", unit: "", get: (s: Summary) => s.overall.completion_rate, show: (v: number) => pct(v), digits: 1, scale: 100, suffix: " pp" },
  { key: "energy_kwh", icon: Zap, label: "Energy delivered", unit: "kWh", get: (s: Summary) => s.overall.energy_kwh, show: (v: number) => int(v), digits: 0, scale: 1, suffix: "" },
  { key: "idle_slots", icon: SquareParking, label: "Idle bay slots", unit: "", get: (s: Summary) => s.overall.idle_slots, show: (v: number) => int(v), digits: 0, scale: 1, suffix: "" },
];

const CHART_METRICS = [
  { key: "avg_wait_slots", label: "Waiting", unit: "slots per request", show: (v: number) => fmt(v, 2) },
  { key: "completion_rate", label: "Fully served", unit: "% of requests", show: (v: number) => pct(v) },
  { key: "idle_slots", label: "Idle slots", unit: "per 60-day run", show: (v: number) => int(v) },
  { key: "mean_net_utility", label: "Net utility", unit: "points per visit", show: (v: number) => fmt(v, 2) },
];

export function Overview({ p0, p1, view, runs, comparisons, demand }: {
  p0: Summary; p1: Summary; view: PolicyId | "compare"; runs: RunRow[];
  comparisons: Partial<Record<Demand, Comparison>>; demand: Demand;
}) {
  const [metric, setMetric] = useState(CHART_METRICS[0]);
  const compare = view === "compare";
  const main = view === "P0" ? p0 : p1;

  const chartData = useMemo(() => (["low", "medium", "high"] as Demand[]).map((d) => {
    const mean = (pol: PolicyId) => {
      const xs = runs.filter((r) => r.demand === d && r.policy === pol && !r.control_all_hold).map((r) => Number(r[metric.key]));
      return xs.reduce((a, b) => a + b, 0) / xs.length;
    };
    return { demand: DEMAND_LABEL[d], P0: mean("P0"), P1: mean("P1") };
  }), [runs, metric]);
  const ticks = useMemo(() => axisTicks(Math.max(...chartData.flatMap((r) => [r.P0, r.P1])), metric.key === "completion_rate"),
    [chartData, metric]);

  const findings = useMemo(() => {
    const all = (["low", "medium", "high"] as Demand[]).map((d) => comparisons[d]).filter(Boolean) as Comparison[];
    if (all.length < 3) return null;
    const st = (d: Demand, m: string) => comparisons[d]!.stats.find((r) => r.metric === m)!;
    const waitBetter = all.reduce((s, c) => s + c.stats.find((r) => r.metric === "avg_wait_slots")!.seeds_P1_lower, 0);
    const servedBetter = all.reduce((s, c) => s + c.stats.find((r) => r.metric === "completion_rate")!.seeds_P1_higher, 0);
    return {
      waitBetter, servedBetter,
      urgentMed: st("medium", "urgent_mean_net_utility").diff_mean,
      flexMed: st("medium", "flexible_mean_net_utility").diff_mean,
      lowNet: st("low", "mean_net_utility").diff_mean,
      lowSeeds: st("low", "mean_net_utility").seeds_P1_lower,
    };
  }, [comparisons]);

  const waitStat = comparisons[demand]?.stats.find((r) => r.metric === "avg_wait_slots");
  const waitPct = waitStat ? (waitStat.diff_mean / waitStat.P0_mean) * 100 : null;

  return (
    <div className="view-in space-y-8">
      <div className="grid gap-6 lg:grid-cols-[1fr_auto] lg:items-end">
        <div>
          <h1 className="text-[2.4rem] font-semibold sm:text-[3.2rem]">Does an idle fee shorten the queue?</h1>
          <p className="mt-2 text-lg text-slate">
            Six shared chargers, 40 drivers, 60 days. P0 has no fee; P1 charges 2 points for each slot a full car keeps the bay.
          </p>
        </div>
        {waitPct != null && (
          <div className="lg:text-right" aria-label="Headline result">
            <div className="num font-display text-[4.2rem] font-semibold leading-none text-pine-deep">
              {waitPct < 0 ? "−" : "+"}{fmt(Math.abs(waitPct), 0)}%
            </div>
            <div className="text-sm text-slate">waiting with the fee, {DEMAND_LABEL[demand].toLowerCase()} demand, 5 seeds</div>
          </div>
        )}
      </div>

      <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {KPIS.map((k) => (
          <div key={k.key} className="panel p-4 sm:p-5">
            <dt className="flex items-center gap-2.5 text-sm text-slate">
              <span className="grid size-8 place-items-center rounded-lg bg-pine/12 text-pine" aria-hidden="true">
                <k.icon className="size-[18px]" strokeWidth={2} />
              </span>
              {k.label}
            </dt>
            <dd className="mt-2">
              <div className="flex flex-wrap items-baseline gap-x-2">
                <span className={`num font-display text-[2.4rem] leading-none ${compare ? "text-p1" : ""}`}>{k.show(k.get(main))}</span>
                {k.unit && <span className="text-sm text-slate">{k.unit}</span>}
              </div>
              {compare && (
                <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-slate">
                  <span className="num">P0 <span className="text-p0">{k.show(k.get(p0))}</span></span>
                  <Delta chip value={k.get(p1) - k.get(p0)} metric={k.key} digits={k.digits} scale={k.scale} suffix={k.suffix} />
                </div>
              )}
            </dd>
          </div>
        ))}
      </dl>

      <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
        <figure className="panel min-w-0 p-5">
          <figcaption className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="font-semibold">{metric.label} by demand</div>
              <div className="text-sm text-slate">{metric.unit}, mean of 5 seeds</div>
            </div>
            <div className="seg max-w-full overflow-x-auto" role="group" aria-label="Chart measure">
              {CHART_METRICS.map((m) => (
                <button key={m.key} aria-pressed={metric.key === m.key} onClick={() => setMetric(m)}>{m.label}</button>
              ))}
            </div>
          </figcaption>
          <div className="mb-1 flex gap-4 text-sm text-slate">
            <span><span className="swatch bg-p0" /> P0 no fee</span>
            <span><span className="swatch bg-p1" /> P1 fee 2</span>
          </div>
          <div className="h-[260px]" role="img" aria-label={`${metric.label} by demand level for P0 and P1`}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 22, right: 8, bottom: 0, left: -8 }} barGap={4} barCategoryGap="28%">
                <CartesianGrid stroke="#2A3240" vertical={false} />
                <XAxis dataKey="demand" tick={{ fill: "#9AA5B4", fontSize: 13 }} tickLine={false} axisLine={{ stroke: "#2A3240" }} />
                <YAxis domain={[0, ticks[ticks.length - 1]]} ticks={ticks} tick={{ fill: "#6B7585", fontSize: 12 }} tickLine={false} axisLine={false}
                  tickFormatter={(v: number) => (metric.key === "completion_rate" ? `${Math.round(v * 100)}%` : String(v))} />
                <Tooltip cursor={{ fill: "rgba(255,255,255,0.04)" }} formatter={(v: number, n: string) => [metric.show(v), n]}
                  contentStyle={{ background: "#171C24", border: "1px solid #2A3240", borderRadius: 6, color: "#E6EAF0", fontSize: 13 }}
                  labelStyle={{ color: "#9AA5B4" }} />
                {(["P0", "P1"] as const).map((p) => (
                  <Bar key={p} dataKey={p} fill={p === "P0" ? "#58A0D8" : "#C48A22"} radius={[4, 4, 0, 0]} isAnimationActive={false}>
                    <LabelList dataKey={p} position="top" formatter={(v: number) => metric.show(v)} style={{ fill: "#CDD3DC", fontSize: 12 }} />
                  </Bar>
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </figure>

        <div className="panel min-w-0 p-5">
          <h2 className="font-display text-2xl font-semibold">What we found</h2>
          {findings ? (
            <ul className="mt-4 space-y-4">
              <li className="flex gap-3">
                <span className="mt-1 size-2.5 shrink-0 rounded-full bg-pine-deep" aria-hidden="true" />
                <span>Waiting fell in <strong className="num">{findings.waitBetter} of 15</strong> matched runs, and more drivers were fully served in <strong className="num">{findings.servedBetter} of 15</strong>.</span>
              </li>
              <li className="flex gap-3">
                <span className="mt-1 size-2.5 shrink-0 rounded-full bg-pine-deep" aria-hidden="true" />
                <span>When bays are scarce, Urgent drivers gain most: <strong className="num">{signed(findings.urgentMed)}</strong> points per visit at medium demand, against <strong className="num">{signed(findings.flexMed)}</strong> for Flexible drivers.</span>
              </li>
              <li className="flex gap-3">
                <span className="mt-1 size-2.5 shrink-0 rounded-full bg-loss" aria-hidden="true" />
                <span>At low demand the fee costs more than it saves: net utility <strong className="num">{signed(findings.lowNet)}</strong> per visit, lower in {findings.lowSeeds} of 5 seeds.</span>
              </li>
            </ul>
          ) : <p className="mt-4 text-slate">Loading findings.</p>}
        </div>
      </div>
    </div>
  );
}
