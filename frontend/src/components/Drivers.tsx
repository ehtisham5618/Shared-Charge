import type { Comparison, DriverType, Group, StatRow, Strategy, Summary } from "../api";
import { STRATEGY_LABEL, fmt, int, pct, signed } from "../format";
import { Delta } from "./bits";

const ROWS: { key: keyof Group; label: string; show: (v: number) => string; digits: number; scale?: number; suffix?: string }[] = [
  { key: "avg_wait_slots", label: "Average wait (slots)", show: (v) => fmt(v, 2), digits: 2 },
  { key: "completion_rate", label: "Fully served", show: (v) => pct(v), digits: 1, scale: 100, suffix: " pp" },
  { key: "energy_kwh", label: "Energy delivered (kWh)", show: (v) => int(v), digits: 0 },
  { key: "idle_slots", label: "Idle slots", show: (v) => int(v), digits: 0 },
  { key: "mean_gross_utility", label: "Utility before penalty, per visit", show: (v) => fmt(v, 2), digits: 2 },
  { key: "mean_net_utility", label: "Utility after penalty, per visit", show: (v) => fmt(v, 2), digits: 2 },
];

const TYPE_TEXT: Record<DriverType, { title: string; weights: string }> = {
  urgent: { title: "Urgent drivers", weights: "v = 3 per kWh, w = 3 per waiting slot, h = 1 per idle slot" },
  flexible: { title: "Flexible drivers", weights: "v = 2 per kWh, w = 1 per waiting slot, h = 2 per idle slot" },
};

function RangeBar({ s }: { s: StatRow }) {
  // A small range strip on a symmetric scale around zero.
  const lim = Math.max(1.6, Math.abs(s.diff_min), Math.abs(s.diff_max));
  const pos = (v: number) => `${50 + (v / lim) * 50}%`;
  return (
    <div className="relative h-5 w-full" aria-hidden="true">
      <div className="absolute top-1/2 h-px w-full bg-stone" />
      <div className="absolute top-0 h-full w-px bg-faint" style={{ left: "50%" }} />
      <div className="absolute top-1/2 h-[3px] -translate-y-1/2 rounded bg-slate"
        style={{ left: pos(Math.min(s.diff_min, s.diff_max)), width: `calc(${pos(s.diff_max)} - ${pos(s.diff_min)})` }} />
      <div className="absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-ink" style={{ left: pos(s.diff_mean) }} />
    </div>
  );
}

export function DriverTypes({ p0, p1, comparison }: { p0: Summary; p1: Summary; comparison: Comparison }) {
  const stat = (t: DriverType) => comparison.stats.find((r) => r.metric === `${t}_mean_net_utility`)!;
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {(["urgent", "flexible"] as DriverType[]).map((t) => {
        const a = p0.by_type[t];
        const b = p1.by_type[t];
        const s = stat(t);
        return (
          <article key={t} className="panel p-5">
            <header className="flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="font-display text-2xl font-semibold">{TYPE_TEXT[t].title}</h3>
              <span className="num text-sm text-slate">{int(a.requests)} visits</span>
            </header>
            <p className="text-sm text-slate">{TYPE_TEXT[t].weights}</p>
            <table className="data-table num mt-4">
              <thead>
                <tr><th>This seed</th><th className="r text-p0">P0</th><th className="r text-p1">P1</th><th className="r">Change</th></tr>
              </thead>
              <tbody>
                {ROWS.map((r) => (
                  <tr key={r.key}>
                    <td>{r.label}</td>
                    <td className="r">{r.show(a[r.key])}</td>
                    <td className="r">{r.show(b[r.key])}</td>
                    <td className="r"><Delta value={b[r.key] - a[r.key]} metric={r.key} digits={r.digits} scale={r.scale} suffix={r.suffix} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-stone pt-4 text-sm">
              <span className="text-slate">Net utility change over 5 seeds</span>
              <span className="flex items-center gap-2">
                <Delta chip value={s.diff_mean} metric="mean_net_utility" />
                <span className="num text-faint">{signed(s.diff_min)} to {signed(s.diff_max)}</span>
              </span>
            </div>
            <div className="mt-2"><RangeBar s={s} /></div>
          </article>
        );
      })}
    </div>
  );
}

const STRATS: Strategy[] = ["release", "hold", "reciprocal", "fee_aware"];
const STRAT_RULE: Record<Strategy, string> = {
  release: "Always releases",
  hold: "Holds the largest legal amount, up to 2 slots",
  reciprocal: "Holds 1 slot if its last visit went badly",
  fee_aware: "Holds only while h − F is positive",
};

export function Strategies({ p0, p1 }: { p0: Summary; p1: Summary }) {
  return (
    <div className="overflow-x-auto">
      <table className="data-table num">
        <thead>
          <tr>
            <th>Driver rule</th>
            <th>What it does after a full charge</th>
            <th className="r">Idle slots P0</th>
            <th className="r">Idle slots P1</th>
            <th className="r">Net utility P0</th>
            <th className="r">Net utility P1</th>
            <th className="r">Change</th>
          </tr>
        </thead>
        <tbody>
          {STRATS.map((s) => (
            <tr key={s}>
              <td className="font-semibold">{STRATEGY_LABEL[s]}</td>
              <td className="text-slate">{STRAT_RULE[s]}</td>
              <td className="r">{int(p0.by_strategy[s].idle_slots)}</td>
              <td className="r">{int(p1.by_strategy[s].idle_slots)}</td>
              <td className="r">{fmt(p0.by_strategy[s].mean_net_utility, 2)}</td>
              <td className="r">{fmt(p1.by_strategy[s].mean_net_utility, 2)}</td>
              <td className="r"><Delta value={p1.by_strategy[s].mean_net_utility - p0.by_strategy[s].mean_net_utility} metric="mean_net_utility" /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ControlResult({ stats }: { stats: StatRow[] }) {
  const g = (m: string) => stats.find((r) => r.metric === m)!;
  const wait = g("avg_wait_slots");
  const idle = g("idle_slots");
  const net = g("mean_net_utility");
  const pen = g("total_penalty");
  return (
    <aside className="panel p-5">
      <h3 className="section-title">Control: every driver on fixed Hold</h3>
      <p className="mt-1 text-sm text-slate">Medium demand, 10 extra runs. Hold ignores the fee, so only the penalty changes.</p>
      <dl className="num mt-4 grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4">
        <div><dt className="text-sm text-slate">Waiting change</dt><dd className="font-display text-2xl">{signed(wait.diff_mean)}</dd></div>
        <div><dt className="text-sm text-slate">Idle slot change</dt><dd className="font-display text-2xl">{signed(idle.diff_mean, 0)}</dd></div>
        <div><dt className="text-sm text-slate">Penalty paid per run</dt><dd className="font-display text-2xl">{int(pen.P1_mean)}</dd></div>
        <div><dt className="text-sm text-slate">Net utility per visit</dt><dd className="font-display text-2xl text-loss">{signed(net.diff_mean)}</dd></div>
      </dl>

    </aside>
  );
}
