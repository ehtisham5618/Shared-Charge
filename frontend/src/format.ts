export const SLOT_MIN = 30;

const nf = (d: number) => new Intl.NumberFormat("en-GB", { minimumFractionDigits: d, maximumFractionDigits: d });

export const fmt = (v: number | null | undefined, digits = 2) => (v == null ? "—" : nf(digits).format(v));
export const pct = (v: number | null | undefined, digits = 1) => (v == null ? "—" : `${nf(digits).format(v * 100)}%`);
export const int = (v: number | null | undefined) => (v == null ? "—" : nf(0).format(v));

export const signed = (v: number, digits = 2, suffix = "") => {
  const s = nf(digits).format(Math.abs(v));
  if (Math.abs(v) < 0.5 * 10 ** -digits) return `0${suffix}`;
  return `${v > 0 ? "+" : "−"}${s}${suffix}`;
};

/** Boundary index 0..16 to clock time, 08:00..16:00 */
export const clock = (b: number | null) => {
  if (b == null) return "—";
  const mins = 8 * 60 + b * SLOT_MIN;
  return `${String(Math.floor(mins / 60)).padStart(2, "0")}:${String(mins % 60).padStart(2, "0")}`;
};

export const DEMAND_LABEL = { low: "Low", medium: "Medium", high: "High" } as const;
export const POLICY_LABEL = { P0: "No fee", P1: "Fee of 2 per idle slot" } as const;
export const STRATEGY_LABEL = { release: "Release", hold: "Hold", reciprocal: "Reciprocal", fee_aware: "Fee aware" } as const;
export const ACTION_LABEL: Record<string, string> = {
  release: "Released",
  hold_1: "Held 1 slot",
  hold_2: "Held 2 slots",
  forced_release: "Finished at departure",
  departed_incomplete: "Left before full",
  unserved: "Never served",
};

/** For each metric: is a lower value better? Used to colour changes honestly. */
export const LOWER_IS_BETTER: Record<string, boolean> = {
  avg_wait_slots: true,
  idle_slots: true,
  unserved: true,
  total_penalty: true,
};
