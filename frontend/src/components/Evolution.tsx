import { CartesianGrid, Legend, Line, LineChart, ReferenceDot, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { EvoPoint } from "../api";
import { fmt } from "../format";

export function Evolution({ points }: { points: EvoPoint[] }) {
  const f0 = points.filter((p) => p.fee === 0);
  const f2 = points.filter((p) => p.fee === 2);
  const data = f0.map((p, i) => ({ update: p.update, f0: p.x_share_C, f2: f2[i].x_share_C }));
  const first0 = f0[1];
  const first2 = f2[1];
  const inBounds = points.every((p) => p.x_share_C >= 0 && p.x_share_C <= 1);

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
      <figure className="panel p-4">
        <figcaption className="mb-1 text-sm text-slate">Share of the population choosing C (release), x, over 30 updates</figcaption>
        <div className="h-[340px]" role="img"
          aria-label={`Evolutionary trajectories from x = 0.5: with no fee x falls to ${fmt(f0[30].x_share_C, 3)}; with fee 2 x rises to ${fmt(f2[30].x_share_C, 3)}.`}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 16, right: 24, bottom: 18, left: 0 }}>
              <CartesianGrid stroke="#2A3240" vertical={false} />
              <XAxis dataKey="update" type="number" domain={[0, 30]} ticks={[0, 5, 10, 15, 20, 25, 30]}
                tick={{ fill: "#9AA5B4", fontSize: 12 }} tickLine={false} axisLine={{ stroke: "#2A3240" }}
                label={{ value: "Update", position: "insideBottom", offset: -10, fill: "#9AA5B4", fontSize: 12 }} />
              <YAxis domain={[0, 1]} ticks={[0, 0.25, 0.5, 0.75, 1]} tick={{ fill: "#9AA5B4", fontSize: 12 }}
                tickLine={false} axisLine={false} width={44} />
              <Tooltip
                formatter={(v: number, name: string) => [fmt(v, 5), name]}
                labelFormatter={(l) => `Update ${l}`}
                contentStyle={{ background: "#171C24", borderRadius: 6, borderColor: "#2A3240", color: "#E6EAF0", fontSize: 13 }} labelStyle={{ color: "#9AA5B4" }} />
              <Legend verticalAlign="top" align="right" iconType="plainline" wrapperStyle={{ fontSize: 13, paddingBottom: 8 }} />
              <Line name="F = 0, no fee" dataKey="f0" stroke="#58A0D8" strokeWidth={2} dot={{ r: 2.5 }} activeDot={{ r: 5 }} isAnimationActive={false} />
              <Line name="F = 2, idle fee" dataKey="f2" stroke="#C48A22" strokeWidth={2} dot={{ r: 2.5 }} activeDot={{ r: 5 }} isAnimationActive={false} />
              <ReferenceDot x={0} y={0.5} r={6} fill="#E6EAF0" stroke="#171C24" strokeWidth={2}
                label={{ value: "start, x = 0.5", position: "bottom", fill: "#E6EAF0", fontSize: 12, offset: 22, dx: 34 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </figure>
      <div className="space-y-5 text-sm">
        <div>
          <h3 className="font-semibold">The model</h3>
          <p className="num mt-1 text-slate">fC = 4x<br />fH = (6 − F)x + (1 − F)(1 − x)<br />x′ = x + 0.05·x(1 − x)(fC − fH)</p>
        </div>
        <div>
          <h3 className="font-semibold">First update checked</h3>
          <p className="num mt-1 text-slate">
            F = 0: fC = {fmt(f0[0].fC, 1)}, fH = {fmt(f0[0].fH, 1)}, x₁ = {fmt(first0.x_share_C, 5)}<br />
            F = 2: fC = {fmt(f2[0].fC, 1)}, fH = {fmt(f2[0].fH, 1)}, x₁ = {fmt(first2.x_share_C, 5)}
          </p>
        </div>
        <div>
          <h3 className="font-semibold">Result</h3>
          <p className="mt-1 text-slate">
            Release falls to <span className="num text-p0">{fmt(f0[30].x_share_C, 3)}</span> with no fee and rises to{" "}
            <span className="num text-p1">{fmt(f2[30].x_share_C, 3)}</span> with F = 2.
            {inBounds ? " All shares stay in [0, 1]." : " A share left [0, 1]."}
          </p>
        </div>
      </div>
    </div>
  );
}
