import type { ReactNode } from "react";
import { LOWER_IS_BETTER, signed } from "../format";

function judge(metric: string, v: number, digits: number) {
  const flat = Math.abs(v) < 0.5 * 10 ** -digits;
  const lower = Object.entries(LOWER_IS_BETTER).some(([k, low]) => low && metric.endsWith(k));
  return flat ? null : lower ? v < 0 : v > 0;
}

/** A P1-minus-P0 change, coloured by whether it is better for drivers. */
export function Delta({ value, metric, digits = 2, suffix = "", scale = 1, chip = false }: {
  value: number; metric: string; digits?: number; suffix?: string; scale?: number; chip?: boolean;
}) {
  const v = value * scale;
  const good = judge(metric, v, digits);
  const word = good == null ? "no change" : good ? "better" : "worse";
  if (chip) {
    const cls = good == null ? "chip-flat" : good ? "chip-good" : "chip-bad";
    return <span className={`chip num ${cls}`} title={`P1 minus P0: ${word}`}>{signed(v, digits, suffix)}</span>;
  }
  const color = good == null ? "text-slate" : good ? "text-pine-deep" : "text-loss";
  return <span className={`num font-semibold ${color}`} title={`P1 minus P0: ${word}`}>{signed(v, digits, suffix)}</span>;
}

export function Section({ title, hint, children, aside }: {
  title: string; hint?: ReactNode; children: ReactNode; aside?: ReactNode;
}) {
  return (
    <section className="py-6">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="section-title">{title}</h2>
          {hint && <p className="mt-1 text-sm text-slate">{hint}</p>}
        </div>
        {aside}
      </div>
      {children}
    </section>
  );
}

export function Skeleton({ h = 120 }: { h?: number }) {
  return <div className="animate-pulse rounded-md bg-paper" style={{ height: h }} aria-hidden="true" />;
}

export function ErrorNote({ error, retry }: { error: string; retry?: () => void }) {
  return (
    <div role="alert" className="panel p-4 text-sm">
      <p className="font-semibold text-loss">Results could not be loaded.</p>
      <p className="mt-1 text-slate">{error}</p>
      <p className="mt-1 text-slate">
        Start the API with <code>python -m shared_charge serve</code> after running <code>python -m shared_charge all</code>.
      </p>
      {retry && <button className="btn-quiet mt-3" onClick={retry}>Try again</button>}
    </div>
  );
}
