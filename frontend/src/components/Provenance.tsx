import type { Meta, MiniCaseDriver, Settings } from "../api";
import { downloadUrl } from "../api";
import { DEMAND_LABEL } from "../format";

export function Downloads({ runIds }: { runIds: string[] }) {
  const files: [string, string][] = [];
  for (const id of runIds) {
    files.push([`runs/${id}/visits.csv`, `Visits, ${id} (CSV)`]);
    files.push([`runs/${id}/summary.json`, `Summary, ${id} (JSON)`]);
    files.push([`runs/${id}/settings.json`, `Settings, ${id} (JSON)`]);
  }
  files.push(["summary_runs.csv", "All 40 run summaries (CSV)"]);
  files.push(["comparison_stats.csv", "P1 vs P0 across seeds (CSV)"]);
  files.push(["comparison_by_seed.csv", "P1 vs P0 per seed (CSV)"]);
  files.push(["control_stats.csv", "Fixed-Hold control (CSV)"]);
  files.push(["evolutionary.csv", "Evolutionary trajectories (CSV)"]);
  files.push(["game_theory.json", "Game-theory calculations (JSON)"]);
  return (
    <ul className="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2 lg:grid-cols-3">
      {files.map(([path, label]) => (
        <li key={path}>
          <a href={downloadUrl(path)} download className="text-pine-deep underline decoration-stone underline-offset-4 hover:decoration-pine">
            {label}
          </a>
        </li>
      ))}
    </ul>
  );
}

export function Provenance({ settings }: { settings: Settings[] }) {
  const s = settings[0];
  return (
    <div className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
      <div className="panel p-5">
        <h3 className="font-display text-xl font-semibold">Settings used</h3>
        <dl className="num mt-3 grid grid-cols-[auto_1fr] gap-x-6 gap-y-1.5 text-sm">
          <dt className="text-slate">Runs shown</dt><dd>{settings.map((x) => x.run_id).join(", ")}</dd>
          <dt className="text-slate">Demand</dt><dd>{DEMAND_LABEL[s.demand]}, {s.requests} requests</dd>
          <dt className="text-slate">Policies</dt><dd>{settings.map((x) => `${x.policy_id} ${x.policy_name}, fee ${x.fee_per_idle_slot}`).join("; ")}</dd>
          <dt className="text-slate">Seed</dt><dd>{s.seed} (generator seed {s.generator_seed}, urgent prior {s.urgent_prior})</dd>
          <dt className="text-slate">Duration</dt><dd>{s.days} simulated days, boundaries 0 to {s.day_end_boundary}, {s.slot_minutes}-minute slots</dd>
          <dt className="text-slate">Site</dt><dd>{s.chargers} chargers at {s.charger_power_kw} kW, {s.kwh_per_slot} kWh per full slot</dd>
          <dt className="text-slate">Utility</dt><dd>{s.utility}</dd>
          <dt className="text-slate">Input folder</dt><dd><code>{s.input_dir}</code></dd>
        </dl>
        <h4 className="mt-4 text-sm font-semibold">Event order at each boundary</h4>
        <ol className="mt-1 list-decimal pl-5 text-sm text-slate">
          {s.event_order.map((e) => <li key={e}>{e}</li>)}
        </ol>
      </div>
      <div className="panel p-5">
        <h3 className="font-display text-xl font-semibold">Input files (SHA-256)</h3>
        <table className="data-table mt-2">
          <tbody>
            {Object.entries(s.input_files).map(([f, h]) => (
              <tr key={f}><td>{f}</td><td className="num text-slate" title={h}><code>{h.slice(0, 16)}…</code></td></tr>
            ))}
          </tbody>
        </table>
        <p className="mt-3 text-sm text-slate">
          Both policies read the same files for a seed, so requests, driver types and starting rules are matched.
        </p>
      </div>
    </div>
  );
}

export function MiniCase({ mini }: { mini: Meta["mini_case"] }) {
  const cases: [string, string][] = [["all_release", "Everyone releases"], ["A_holds_one_slot", "A holds one slot"]];
  return (
    <div className="grid gap-5 lg:grid-cols-2">
      {cases.map(([key, title]) => {
        const c = mini.cases[key];
        const sim = c.simulated;
        return (
          <article key={key} className="panel p-5">
            <header className="flex items-baseline justify-between">
              <h3 className="font-display text-xl font-semibold">{title}</h3>
              <span className={`text-sm font-semibold ${c.match ? "text-pine-deep" : "text-loss"}`}>
                {c.match ? "Matches expected JSON" : "Does not match"}
              </span>
            </header>
            <table className="data-table num mt-2">
              <thead><tr><th>Driver</th><th className="r">Start</th><th className="r">Full</th><th className="r">Release</th><th className="r">Wait</th><th className="r">Utility</th></tr></thead>
              <tbody>
                {["A", "B", "C"].map((d) => {
                  const r = sim[d] as MiniCaseDriver;
                  return (
                    <tr key={d}><td>{d}</td><td className="r">{r.start}</td><td className="r">{r.finish}</td><td className="r">{r.release}</td><td className="r">{r.wait_slots}</td><td className="r">{r.utility}</td></tr>
                  );
                })}
              </tbody>
            </table>
            <p className="num mt-2 text-sm text-slate">
              Total wait {String(sim.total_wait_slots)} slots, energy {String(sim.delivered_kwh)} kWh, utility {String(sim.total_utility)}.
            </p>
          </article>
        );
      })}
    </div>
  );
}
