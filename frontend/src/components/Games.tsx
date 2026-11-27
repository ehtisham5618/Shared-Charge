import type { GameTheory } from "../api";
import { fmt } from "../format";

/** Compact read-out of results/game_theory.json. Full working is in the report appendix. */
export function Games({ gt }: { gt: GameTheory }) {
  const pay = gt.normal_form.payoffs as Record<string, [number, number]>;
  const br1 = gt.normal_form.best_responses.P1_vs_P2 as Record<string, string[]>;
  const br2 = gt.normal_form.best_responses.P2_vs_P1 as Record<string, string[]>;
  const inf = gt.infinite_repeated;
  const bay = gt.bayesian;
  const mb = gt.mixed_vs_behavioral;
  const row = (d: number) => inf.table.find((r: { delta: number }) => r.delta === d);

  return (
    <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
      <article className="panel p-5">
        <h3 className="font-display text-xl font-semibold">Normal form</h3>
        <p className="text-sm text-slate">C releases, H holds one slot. Best responses are underlined.</p>
        <table className="num mt-3 w-full text-center text-sm">
          <thead><tr><th></th><th className="pb-1 font-semibold">P2 C</th><th className="pb-1 font-semibold">P2 H</th></tr></thead>
          <tbody>
            {["C", "H"].map((a1) => (
              <tr key={a1}>
                <th className="pr-2 text-left font-semibold">P1 {a1}</th>
                {["C", "H"].map((a2) => {
                  const [u1, u2] = pay[a1 + a2];
                  const ne = a1 === "H" && a2 === "H";
                  return (
                    <td key={a2} className={`border border-stone px-2 py-2 ${ne ? "bg-ochre/25 font-semibold" : ""}`}>
                      (<span className={br1[a2].includes(a1) ? "underline decoration-2 underline-offset-2" : ""}>{u1}</span>,{" "}
                      <span className={br2[a1].includes(a2) ? "underline decoration-2 underline-offset-2" : ""}>{u2}</span>)
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-3 text-sm">
          H is strictly dominant for both, so the only pure Nash equilibrium is (H, H) with (1, 1). The best joint outcome is (C, C) with (4, 4).
        </p>
      </article>

      <article className="panel p-5">
        <h3 className="font-display text-xl font-semibold">Infinite repetition</h3>
        <p className="text-sm text-slate">Grim trigger: start with C, switch to H forever after any H.</p>
        <p className="num mt-3 text-sm">
          4/(1 − δ) ≥ 6 + δ/(1 − δ)<br />4 ≥ 6 − 5δ, so δ ≥ <strong>{fmt(inf.threshold, 1)}</strong>
        </p>
        <table className="data-table num mt-3">
          <thead><tr><th>δ</th><th className="r">Cooperate</th><th className="r">Deviate</th></tr></thead>
          <tbody>
            {[0.2, 0.5].map((d) => (
              <tr key={d}>
                <td>{d}</td>
                <td className="r">{fmt(row(d).cooperate_forever, 2)}</td>
                <td className="r">{fmt(row(d).deviate_now, 2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-2 text-sm text-slate">Three known rounds: (H, H) in every round, 3 points each.</p>
      </article>

      <article className="panel p-5">
        <h3 className="font-display text-xl font-semibold">Bayesian check</h3>
        <p className="text-sm text-slate">P(Urgent) = 0.30, fee 1.5, Flexible +1 on H. Plan: Urgent C, Flexible H.</p>
        <table className="data-table num mt-3">
          <thead><tr><th>Type</th><th className="r">E[C]</th><th className="r">E[H]</th><th className="r">Plan</th></tr></thead>
          <tbody>
            {bay.checks.map((c: { type: string; EV_C: number; EV_H: number; planned: string; no_profitable_deviation: boolean }) => (
              <tr key={c.type}>
                <td className="capitalize">{c.type}</td>
                <td className="r">{fmt(c.EV_C, 2)}</td>
                <td className="r">{fmt(c.EV_H, 2)}</td>
                <td className="r font-semibold">{c.planned}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-3 text-sm">
          {bay.is_bayesian_nash_equilibrium
            ? "No type of either player gains by switching alone, so the plan is a Bayesian Nash equilibrium."
            : "Some type gains by switching, so the plan is not an equilibrium."}
        </p>
      </article>

      <article className="panel p-5">
        <h3 className="font-display text-xl font-semibold">Mixed vs behavioral</h3>
        <p className="text-sm text-slate">Forgotten stage, P2 fixed to L. P1 payoffs: LL 1, LR 8, RL 6, RR 2.</p>
        <dl className="num mt-3 space-y-2 text-sm">
          <div className="flex justify-between"><dt>50–50 lottery, always L or always R</dt><dd className="font-semibold">{fmt(mb.mixed_expected, 2)}</dd></div>
          <div className="flex justify-between"><dt>Fresh 50–50 draw at each visit</dt><dd className="font-semibold">{fmt(mb.behavioral_expected, 2)}</dd></div>
          <div className="flex justify-between"><dt>Perfect recall, repeat first draw</dt><dd className="font-semibold">{fmt(mb.recall_behavioral_expected, 2)}</dd></div>
        </dl>
        <p className="mt-3 text-sm text-slate">
          Fresh draws reach LR and RL with probability 0.25 each; the lottery never does. Without memory P1 cannot copy its first draw.
        </p>
      </article>
    </div>
  );
}
