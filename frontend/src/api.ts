// Typed access to the local results API. Every value shown on screen comes from here.

export type Demand = "low" | "medium" | "high";
export type PolicyId = "P0" | "P1";
export type DriverType = "urgent" | "flexible";
export type Strategy = "release" | "hold" | "reciprocal" | "fee_aware";

export interface Group {
  requests: number;
  avg_wait_slots: number;
  completion_rate: number;
  energy_kwh: number;
  idle_slots: number;
  unserved: number;
  incomplete: number;
  holds: number;
  total_gross_utility: number;
  total_penalty: number;
  total_net_utility: number;
  mean_gross_utility: number;
  mean_net_utility: number;
}

export interface Summary {
  overall: Group & { avg_wait_minutes: number; days: number };
  by_type: Record<DriverType, Group>;
  by_strategy: Record<Strategy, Group>;
  actions: Record<string, number>;
}

export interface Settings {
  run_id: string;
  seed: number;
  demand: Demand;
  policy_id: PolicyId;
  policy_name: string;
  fee_per_idle_slot: number;
  control_all_hold: boolean;
  days: number;
  requests: number;
  chargers: number;
  charger_power_kw: number;
  kwh_per_slot: number;
  day_end_boundary: number;
  slot_minutes: number;
  urgent_prior: number;
  generator_seed: number;
  input_dir: string;
  input_files: Record<string, string>;
  utility: string;
  event_order: string[];
}

export interface RunData {
  run_id: string;
  settings: Settings;
  summary: Summary;
  files: Record<string, string>;
}

export interface Visit {
  seed: number;
  demand: Demand;
  policy: PolicyId;
  day: number;
  request_id: string;
  driver_id: string;
  driver_type: DriverType;
  strategy: Strategy;
  arrival: number;
  departure: number;
  charger_id: string | null;
  start: number | null;
  finish: number | null;
  release: number | null;
  requested_kwh: number;
  delivered_kwh: number;
  waiting_slots: number;
  action: string;
  idle_slots: number;
  fee: number;
  penalty: number;
  gross_utility: number;
  net_utility: number;
  fully_served: boolean;
}

export interface StatRow {
  demand: string;
  metric: string;
  P0_mean: number;
  P1_mean: number;
  diff_mean: number;
  diff_min: number;
  diff_max: number;
  seeds_P1_lower: number;
  seeds_P1_higher: number;
}

export interface SeedRow {
  demand: string;
  metric: string;
  seed: number;
  P0: number;
  P1: number;
  diff_P1_minus_P0: number;
}

export interface Comparison {
  demand: Demand;
  by_seed: SeedRow[];
  stats: StatRow[];
}

export interface EvoPoint {
  fee: number;
  update: number;
  x_share_C: number;
  share_H: number;
  fC: number;
  fH: number;
  fC_minus_fH: number;
}

export interface MiniCaseDriver {
  start: number;
  finish: number;
  release: number;
  wait_slots: number;
  utility: number;
}

export interface Meta {
  seeds: number[];
  demands: Demand[];
  policies: PolicyId[];
  manifest: { generated_at_utc: string; main_runs: number; control_runs: number; runs: string[] };
  mini_case: {
    all_match: boolean;
    conditions: Record<string, string | number>;
    cases: Record<string, { match: boolean; simulated: Record<string, MiniCaseDriver | number>; expected: Record<string, MiniCaseDriver | number> }>;
  };
  site: { chargers: number; power_kw: number; kwh_per_slot: number; slot_minutes: number; day_end_boundary: number; days: number };
}

export interface RerunResult {
  run_id: string;
  identical_to_saved: boolean;
  elapsed_ms: number;
  visits: number;
  days: number;
}

// Loose type for game_theory.json; the screen reads a few named fields.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type GameTheory = any;

async function get<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* keep status text */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const runId = (demand: Demand, policy: PolicyId, seed: number) => `${demand}_${policy}_seed${seed}`;

export const api = {
  meta: () => get<Meta>("/api/meta"),
  run: (id: string) => get<RunData>(`/api/runs/${id}`),
  visits: (id: string) => get<Visit[]>(`/api/runs/${id}/visits`),
  rerun: (id: string) => get<RerunResult>(`/api/runs/${id}/rerun`, { method: "POST" }),
  comparison: (d: Demand) => get<Comparison>(`/api/comparison/${d}`),
  control: () => get<{ by_seed: SeedRow[]; stats: StatRow[] }>("/api/control"),
  evolutionary: () => get<EvoPoint[]>("/api/evolutionary"),
  gameTheory: () => get<GameTheory>("/api/game-theory"),
};

export const downloadUrl = (path: string) => `/api/download/${path}`;
