import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Comparison, Summary } from "../api";
import { LOWER_IS_BETTER, fmt, int, pct, signed } from "../format";
import { Delta } from "./bits";

const P0 = "#58A0D8";
const P1 = "#C48A22";

interface M {
  key: string;
  label: string;
  unit: string;
  get: (s: Summary) => number;
  show: (v: number) => string;
  digits: number;
  scale?: number;
  suffix?: string;
}

export const COMPARE_METRICS: M[] = [
  { key: "avg_wait_slots", label: "Average wait", unit: "slots", get: (s) => s.overall.avg_wait_slots, show: (v) => fmt(v, 2), digits: 2 },
  { key: "completion_rate", label: "Fully served", unit: "% of requests", get: (s) => s.overall.completion_rate, show: (v) => pct(v), digits: 1, scale: 100, suffix: " pp" },
  { key: "energy_kwh", label: "Energy delivered", unit: "kWh", get: (s) => s.overall.energy_kwh, show: (v) => int(v), digits: 0 },
  { key: "idle_slots", label: "Idle slots", unit: "slots", get: (s) => s.overall.idle_slots, show: (v) => int(v), digits: 0 },
  { key: "mean_gross_utility", label: "Utility before penalty", unit: "points per request", get: (s) => s.overall.mean_gross_utility, show: (v) => fmt(v, 2), digits: 2 },
  { key: "mean_net_utility", label: "Utility after penalty", unit: "points per request", get: (s) => s.overall.mean_net_utility, show: (v) => fmt(v, 2), digits: 2 },
];

function Pair({ m, p0, p1 }: { m: M; p0: Summary; p1: Summary }) {
  const data = [
    { name: "P0", value: m.get(p0) },
    { name: "P1", value: m.get(p1) },
  ];
  return (
    <figure className="panel p-4">
      <figcaption className="flex items-baseline justify-between gap-2">
        <span className="font-semibold">{m.label}</span>
        <Delta value={m.get(p1) - m.get(p0)} metric={m.key} digits={m.digits} scale={m.scale} suffix={m.suffix} />
      </figcaption>
      <p className="text-xs text-slate">{m.unit}</p>
      <div className="mt-2 h-[92px]" role="img" aria-label={`${m.label}: P0 ${m.show(data[0].value)}, P1 ${m.show(data[1].value)}`}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 0, right: 64, bottom: 0, left: 0 }} barCategoryGap={8}>
            <XAxis type="number" hide domain={[0, "dataMax"]} />
            <YAxis type="category" dataKey="name" width={28} tickLine={false} axisLine={false}
              tick={{ fill: "#9AA5B4", fontSize: 13 }} />
            <Tooltip cursor={{ fill: "rgba(255,255,255,0.04)" }} formatter={(v: number) => [m.show(v), m.label]}
              contentStyle={{ background: "#171C24", borderRadius: 6, borderColor: "#2A3240", color: "#E6EAF0", fontSize: 13 }} labelStyle={{ color: "#9AA5B4" }} />
            <Bar dataKey="value" radius={[0, 4, 4, 0]} isAnimationActive={false}>
              {data.map((d) => <Cell key={d.name} fill={d.name === "P0" ? P0 : P1} />)}
              <LabelList dataKey="value" position="right" formatter={(v: number) => m.show(v)}
                style={{ fill: "#E6EAF0", fontSize: 13, fontVariantNumeric: "tabular-nums" }} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}

export function PolicyPairs({ p0, p1 }: { p0: Summary; p1: Summary }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {COMPARE_METRICS.map((m) => <Pair key={m.key} m={m} p0={p0} p1={p1} />)}
    </div>
  );
}

export function SeedStats({ comparison, seed }: { comparison: Comparison; seed: number }) {
  const rows = COMPARE_METRICS.map((m) => {
    const s = comparison.stats.find((r) => r.metric === m.key)!;
    const thisSeed = comparison.by_seed.find((r) => r.metric === m.key && r.seed === seed)!;
    const better = LOWER_IS_BETTER[m.key] ? s.seeds_P1_lower : s.seeds_P1_higher;
    return { m, s, thisSeed, better };
  });
  const scaled = (m: M, v: number) => v * (m.scale ?? 1);
  return (
    <div className="overflow-x-auto">
      <table className="data-table num">
        <caption className="sr-only">P1 minus P0 on matching seeds</caption>
        <thead>
          <tr>
            <th>Measure</th>
            <th className="r">P0 mean</th>
            <th className="r">P1 mean</th>
            <th className="r">Change, seed {seed}</th>
            <th className="r">Mean change</th>
            <th className="r">Range over 5 seeds</th>
            <th className="r">Seeds where P1 is better</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ m, s, thisSeed, better }) => (
            <tr key={m.key}>
              <td>{m.label}</td>
              <td className="r">{m.show(s.P0_mean)}</td>
              <td className="r">{m.show(s.P1_mean)}</td>
              <td className="r"><Delta value={thisSeed.diff_P1_minus_P0} metric={m.key} digits={m.digits} scale={m.scale} suffix={m.suffix} /></td>
              <td className="r"><Delta value={s.diff_mean} metric={m.key} digits={m.digits} scale={m.scale} suffix={m.suffix} /></td>
              <td className="r text-slate">
                {signed(scaled(m, s.diff_min), m.digits)} to {signed(scaled(m, s.diff_max), m.digits)}
              </td>
              <td className="r">{better} of 5</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
