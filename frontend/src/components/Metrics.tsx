import type { PolicyId, Summary } from "../api";
import { fmt, int, pct } from "../format";
import { Delta } from "./bits";

interface Item {
  key: string;
  label: string;
  unit: string;
  value: (s: Summary) => number;
  show: (v: number) => string;
  digits: number;
  scale?: number;
  suffix?: string;
  note: (s: Summary) => string;
}

const ITEMS: Item[] = [
  {
    key: "avg_wait_slots", label: "Average wait", unit: "slots per request", digits: 2,
    value: (s) => s.overall.avg_wait_slots, show: (v) => fmt(v, 2),
    note: (s) => `about ${fmt(s.overall.avg_wait_minutes, 0)} minutes, unserved drivers included`,
  },
  {
    key: "completion_rate", label: "Fully served", unit: "of requests", digits: 1, scale: 100, suffix: " pp",
    value: (s) => s.overall.completion_rate, show: (v) => pct(v),
    note: (s) => `${int(s.overall.unserved)} never reached a charger`,
  },
  {
    key: "energy_kwh", label: "Energy delivered", unit: "kWh over 60 days", digits: 0,
    value: (s) => s.overall.energy_kwh, show: (v) => int(v),
    note: (s) => `${int(s.overall.requests)} requests in total`,
  },
  {
    key: "idle_slots", label: "Idle slots", unit: "bay slots held after a full charge", digits: 0,
    value: (s) => s.overall.idle_slots, show: (v) => int(v),
    note: (s) => `${int(s.overall.holds)} visits chose to hold`,
  },
];

export function Metrics({ p0, p1, policy, compare }: { p0: Summary; p1: Summary; policy: PolicyId; compare: boolean }) {
  const main = policy === "P0" ? p0 : p1;
  return (
    <dl className="grid grid-cols-2 border-y border-stone lg:grid-cols-4">
      {ITEMS.map((it, i) => (
        <div key={it.key}
          className={`px-1 py-5 sm:px-5 ${i > 0 ? "lg:border-l" : ""} ${i % 2 === 1 ? "border-l" : ""} ${i > 1 ? "border-t lg:border-t-0" : ""} border-stone`}>
          <dt className="text-sm font-semibold text-ink">{it.label}</dt>
          {compare ? (
            <dd className="mt-1">
              <div className="num flex items-baseline gap-3">
                <span className="font-display text-[2rem] leading-none text-p0">{it.show(it.value(p0))}</span>
                <span className="font-display text-[2rem] leading-none text-p1">{it.show(it.value(p1))}</span>
              </div>
              <div className="mt-2 text-sm text-slate">
                P0 then P1, change <Delta value={it.value(p1) - it.value(p0)} metric={it.key} digits={it.digits}
                  scale={it.scale} suffix={it.suffix} />
              </div>
            </dd>
          ) : (
            <dd className="mt-1">
              <span className="num font-display text-[2.6rem] leading-none">{it.show(it.value(main))}</span>
              <span className="ml-2 text-sm text-slate">{it.unit}</span>
              <div className="mt-2 text-sm text-slate">{it.note(main)}</div>
            </dd>
          )}
        </div>
      ))}
    </dl>
  );
}
