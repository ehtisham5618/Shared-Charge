import { BadgeCheck, LayoutDashboard, Network, PlugZap, Table2, Users, type LucideIcon } from "lucide-react";

export type Tab = "overview" | "site" | "drivers" | "theory" | "data";

export const TABS: { id: Tab; label: string; icon: LucideIcon }[] = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "site", label: "Site", icon: PlugZap },
  { id: "drivers", label: "Drivers", icon: Users },
  { id: "theory", label: "Game theory", icon: Network },
  { id: "data", label: "Data", icon: Table2 },
];

/**
 * Floating navigation. Collapsed it shows icons only; on hover or keyboard
 * focus it widens to show each label. On small screens it becomes a bottom bar.
 */
export function Sidebar({ tab, onSelect, status }: { tab: Tab; onSelect: (t: Tab) => void; status?: { ok: boolean; text: string } }) {
  return (
    <>
      {/* Desktop and tablet: left rail that expands on hover */}
      <nav aria-label="Views"
        className="group fixed top-1/2 left-4 z-40 hidden w-[60px] -translate-y-1/2 overflow-hidden rounded-2xl border border-stone bg-paper/95 p-2 shadow-[0_18px_50px_-18px_rgba(0,0,0,.85)] backdrop-blur transition-[width] duration-200 ease-out hover:w-[212px] has-[:focus-visible]:w-[212px] md:block">
        <ul className="flex flex-col gap-1">
          {TABS.map(({ id, label, icon: Icon }) => {
            const active = tab === id;
            return (
              <li key={id}>
                <button onClick={() => onSelect(id)} aria-current={active ? "page" : undefined} title={label}
                  className={`flex h-11 w-full items-center gap-3 rounded-xl px-[11px] text-left transition-colors ${
                    active ? "bg-pine text-mineral" : "text-slate hover:bg-raised hover:text-ink"}`}>
                  <Icon className="size-[22px] shrink-0" strokeWidth={active ? 2.2 : 1.8} aria-hidden="true" />
                  <span className={`whitespace-nowrap text-[0.95rem] opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-has-[:focus-visible]:opacity-100 ${active ? "font-semibold" : "font-medium"}`}>
                    {label}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
        {status && (
          <div className="mt-2 flex h-11 items-center gap-3 border-t border-stone px-[11px] pt-2" title={status.text}>
            <BadgeCheck className={`size-[22px] shrink-0 ${status.ok ? "text-pine-deep" : "text-loss"}`} strokeWidth={1.8} aria-hidden="true" />
            <span className="whitespace-nowrap text-sm text-slate opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-has-[:focus-visible]:opacity-100">
              {status.text}
            </span>
          </div>
        )}
      </nav>

      {/* Phones: bottom bar with icons and short labels */}
      <nav aria-label="Views"
        className="fixed inset-x-3 bottom-3 z-40 flex justify-between rounded-2xl border border-stone bg-paper/95 p-1.5 shadow-[0_18px_50px_-18px_rgba(0,0,0,.85)] backdrop-blur md:hidden">
        {TABS.map(({ id, label, icon: Icon }) => {
          const active = tab === id;
          return (
            <button key={id} onClick={() => onSelect(id)} aria-current={active ? "page" : undefined}
              className={`flex min-w-0 flex-1 flex-col items-center gap-0.5 rounded-xl py-1.5 text-[0.7rem] ${active ? "bg-pine text-mineral font-semibold" : "text-slate"}`}>
              <Icon className="size-5" strokeWidth={active ? 2.2 : 1.8} aria-hidden="true" />
              <span className="truncate">{label === "Game theory" ? "Theory" : label}</span>
            </button>
          );
        })}
      </nav>
    </>
  );
}
