import { useEffect, useMemo, useState } from "react";
import type { PolicyId, Visit } from "../api";
import { ACTION_LABEL, STRATEGY_LABEL, clock, fmt } from "../format";

const SLOTS = 16;
const W = 1000;
const GUTTER = 74;
const SLOT_W = (W - GUTTER - 26) / SLOTS;
const LANE_H = 40;
const AXIS_H = 26;
const QUEUE_H = 54;
const BAYS = ["C01", "C02", "C03", "C04", "C05", "C06"];

const x = (b: number) => GUTTER + b * SLOT_W;

interface Hover {
  v: Visit;
  left: number;
  top: number;
  below: boolean;
}

/** Side-view car silhouette, drawn on idle holds: the car is parked but not charging. */
function Car({ cx, cy }: { cx: number; cy: number }) {
  return (
    <g transform={`translate(${cx - 11} ${cy - 6})`} aria-hidden="true">
      <path d="M1 9 L3 5 Q5 2 9 2 L14 2 Q17 2 19 5 L21 6 Q22 7 22 9 Z" fill="#E6EAF0" />
      <circle cx="6" cy="10" r="2" fill="#E6EAF0" stroke="#171C24" strokeWidth="1" />
      <circle cx="17" cy="10" r="2" fill="#E6EAF0" stroke="#171C24" strokeWidth="1" />
    </g>
  );
}

/** Charging post drawn at the head of each bay lane. */
function Post({ y }: { y: number }) {
  return (
    <g transform={`translate(52 ${y - 12})`} aria-hidden="true">
      <rect x="0" y="0" width="10" height="24" rx="2" fill="#5F6B7B" />
      <rect x="2.5" y="3" width="5" height="5" rx="1" fill="#E8B04A" />
      <path d="M10 15 q6 0 6 6 v3" stroke="#5F6B7B" strokeWidth="1.6" fill="none" />
    </g>
  );
}

export function SitePlan({ visits, day, policy, label }: { visits: Visit[]; day: number; policy: PolicyId; label: string }) {
  const [hover, setHover] = useState<Hover | null>(null);
  useEffect(() => {
    const hide = () => setHover(null);
    window.addEventListener("scroll", hide, { passive: true });
    return () => window.removeEventListener("scroll", hide);
  }, []);
  const dayVisits = useMemo(() => visits.filter((v) => v.day === day), [visits, day]);

  // Drivers waiting during each slot [t, t+1): arrived and not yet started (or never started)
  const queue = useMemo(
    () =>
      Array.from({ length: SLOTS }, (_, t) =>
        dayVisits
          .filter((v) => v.arrival <= t && t < (v.start ?? v.departure))
          .sort((a, b) => a.arrival - b.arrival || a.driver_id.localeCompare(b.driver_id)),
      ),
    [dayVisits],
  );
  const maxQueue = Math.max(1, ...queue.map((q) => q.length));
  const H = AXIS_H + BAYS.length * LANE_H + 14 + QUEUE_H;
  const queueTop = AXIS_H + BAYS.length * LANE_H + 14;

  const show = (v: Visit) => (e: React.MouseEvent<SVGElement> | React.FocusEvent<SVGElement>) => {
    // Fixed positioning keeps the tooltip clear of the scroll container's clipping.
    const r = e.currentTarget.getBoundingClientRect();
    const below = r.top < 260;
    const left = Math.min(Math.max(r.left + r.width / 2, 140), window.innerWidth - 140);
    setHover({ v, left, top: below ? r.bottom + 8 : r.top - 8, below });
  };

  const held = dayVisits.reduce((s, v) => s + v.idle_slots, 0);
  const waited = dayVisits.reduce((s, v) => s + v.waiting_slots, 0);
  const served = dayVisits.filter((v) => v.fully_served).length;

  return (
    <figure className="relative">
      <figcaption className="mb-2 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
        <span className="flex items-center gap-2 font-semibold">
          <span className="swatch" style={{ background: policy === "P0" ? "var(--color-p0)" : "var(--color-p1)" }} />
          <span className="font-display text-xl">{policy}</span>
          <span className="text-slate">{label}</span>
        </span>
        <span className="num text-sm text-slate">
          {served} of {dayVisits.length} fully served, {waited} waiting slots, {held} idle slots
        </span>
      </figcaption>
      <div className="overflow-x-auto">
        <div className="relative min-w-[720px]" onMouseLeave={() => setHover(null)}>
          <svg viewBox={`0 0 ${W} ${H}`} className="block w-full" role="img"
            aria-label={`Charger occupancy on day ${day} under ${policy}: ${served} of ${dayVisits.length} requests fully served, ${held} idle slots.`}>
            <defs>
              <pattern id={`hatch-${policy}`} width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                <rect width="6" height="6" fill="#222935" />
                <rect width="2.2" height="6" fill="#8E99A8" />
              </pattern>
            </defs>

            {/* time axis */}
            {Array.from({ length: SLOTS + 1 }, (_, b) => (
              <g key={b}>
                <line x1={x(b)} x2={x(b)} y1={AXIS_H - 4} y2={queueTop + QUEUE_H}
                  stroke={b % 2 === 0 ? "#2A3240" : "#1B212A"} strokeWidth={1} />
                {b % 2 === 0 && (
                  <text x={x(b)} y={14} textAnchor="middle" fontSize="12" fill="#9AA5B4" className="num">{clock(b)}</text>
                )}
              </g>
            ))}

            {/* bays: painted lines + post + number */}
            {BAYS.map((bay, i) => {
              const y = AXIS_H + i * LANE_H;
              return (
                <g key={bay}>
                  <line x1={8} x2={W - 8} y1={y + LANE_H} y2={y + LANE_H} stroke="#2A3240" strokeDasharray={i === BAYS.length - 1 ? undefined : "0"} />
                  <text x={8} y={y + LANE_H / 2 + 6} fontSize="18" fontWeight={600} fill="#E6EAF0"
                    style={{ fontFamily: "var(--font-display)" }}>{bay.replace("C0", "")}</text>
                  <Post y={y + LANE_H / 2} />
                </g>
              );
            })}
            <line x1={8} x2={W - 8} y1={AXIS_H} y2={AXIS_H} stroke="#2A3240" />

            {/* visits on bays */}
            {dayVisits.filter((v) => v.charger_id && v.start != null).map((v, k) => {
              const lane = BAYS.indexOf(v.charger_id!);
              const y = AXIS_H + lane * LANE_H + 6;
              const h = LANE_H - 12;
              const chargeEnd = v.finish ?? v.release!;
              const holdEnd = v.release!;
              const urgent = v.driver_type === "urgent";
              const w = x(chargeEnd) - x(v.start!) - 2;
              return (
                <g key={v.request_id} tabIndex={0} role="button" aria-label={`${v.driver_id}, ${v.driver_type}, ${ACTION_LABEL[v.action]}`}
                  onMouseEnter={show(v)} onFocus={show(v)} onBlur={() => setHover(null)} className="cursor-default outline-none">
                  <g className="plan-bar" style={{ animationDelay: `${Math.min(k, 30) * 12}ms` }}>
                    <rect x={x(v.start!) + 1} y={y} width={Math.max(w, 2)} height={h} rx={3}
                      fill={v.action === "departed_incomplete" ? "#2C3644" : "#1F9688"} />
                    {urgent && <rect x={x(v.start!) + 1} y={y} width={4} height={h} rx={1} fill="#E6EAF0" />}
                    {w > 46 && (
                      <text x={x(v.start!) + (urgent ? 10 : 7)} y={y + h / 2 + 4.5} fontSize="12.5"
                        fill={v.action === "departed_incomplete" ? "#CDD3DC" : "#FFFFFF"} fontWeight={600} className="num">
                        {v.driver_id}
                      </text>
                    )}
                    {v.action === "departed_incomplete" && (
                      <path d={`M${x(chargeEnd) - 1} ${y - 3} v${h + 6}`} stroke="#F2806B" strokeWidth={2.5} />
                    )}
                    {v.idle_slots > 0 && (
                      <>
                        <rect x={x(chargeEnd) + 1} y={y} width={x(holdEnd) - x(chargeEnd) - 2} height={h} rx={3}
                          fill={`url(#hatch-${policy})`} stroke="#9AA5B4" strokeWidth={1} />
                        <Car cx={(x(chargeEnd) + x(holdEnd)) / 2} cy={y + h / 2} />
                      </>
                    )}
                  </g>
                </g>
              );
            })}

            {/* queue lane */}
            <text x={8} y={queueTop + 18} fontSize="13" fill="#E6EAF0" fontWeight={600}>Queue</text>
            <text x={8} y={queueTop + 34} fontSize="11.5" fill="#9AA5B4">waiting</text>
            {queue.map((q, t) => {
              const per = Math.max(1, Math.ceil(maxQueue / 3));
              return (
                <g key={t}>
                  {q.map((v, j) => {
                    const col = j % per;
                    const row = Math.floor(j / per);
                    const size = Math.min(9, (SLOT_W - 10) / per - 2);
                    return (
                      <rect key={v.request_id} x={x(t) + 5 + col * (size + 2)} y={queueTop + 6 + row * (size + 3)}
                        width={size} height={size} rx={1.5}
                        fill={v.start == null ? "none" : "#7C93B3"}
                        stroke={v.start == null ? "#F2806B" : "none"} strokeWidth={1.4}
                        onMouseEnter={show(v)} />
                    );
                  })}
                  {q.length > 0 && (
                    <text x={x(t + 1) - 4} y={queueTop + QUEUE_H - 4} textAnchor="end" fontSize="11" fill="#9AA5B4" className="num">{q.length}</text>
                  )}
                </g>
              );
            })}
          </svg>

          {hover && (
            <div role="tooltip"
              className={`pointer-events-none fixed z-50 w-64 -translate-x-1/2 ${hover.below ? "" : "-translate-y-full"} rounded-[3px] border border-stone bg-paper p-3 text-sm shadow-[0_10px_30px_-10px_rgba(0,0,0,.7)]`}
              style={{ left: hover.left, top: hover.top }}>
              <div className="flex items-baseline justify-between">
                <span className="font-display text-lg font-semibold">{hover.v.driver_id}</span>
                <span className="text-slate capitalize">{hover.v.driver_type}, {STRATEGY_LABEL[hover.v.strategy]}</span>
              </div>
              <dl className="num mt-1 grid grid-cols-2 gap-x-3 gap-y-0.5">
                <dt className="text-slate">Arrived</dt><dd>{clock(hover.v.arrival)}</dd>
                <dt className="text-slate">Must leave</dt><dd>{clock(hover.v.departure)}</dd>
                <dt className="text-slate">Started</dt><dd>{clock(hover.v.start)}</dd>
                <dt className="text-slate">Energy</dt><dd>{fmt(hover.v.delivered_kwh, 0)} / {fmt(hover.v.requested_kwh, 0)} kWh</dd>
                <dt className="text-slate">Waited</dt><dd>{hover.v.waiting_slots} slots</dd>
                <dt className="text-slate">Outcome</dt><dd>{ACTION_LABEL[hover.v.action]}</dd>
                <dt className="text-slate">Net utility</dt><dd>{fmt(hover.v.net_utility, 0)} pts</dd>
              </dl>
            </div>
          )}
        </div>
      </div>
    </figure>
  );
}

export function SitePlanLegend() {
  return (
    <ul className="flex flex-wrap gap-x-5 gap-y-1 text-sm text-slate">
      <li><span className="swatch" style={{ background: "#1F9688" }} /> Charging</li>
      <li><span className="swatch" style={{ background: "#1F9688", boxShadow: "inset 3px 0 0 #E6EAF0" }} /> Urgent driver charging</li>
      <li><span className="swatch hatch" /> Full, holding the bay (idle)</li>
      <li><span className="swatch" style={{ background: "#2C3644", boxShadow: "inset -2px 0 0 #F2806B" }} /> Left before full</li>
      <li><span className="swatch" style={{ background: "#7C93B3" }} /> Waiting, served later</li>
      <li><span className="swatch" style={{ border: "1.5px solid #F2806B" }} /> Waiting, never served</li>
    </ul>
  );
}
