"""Browser check of the running results screen (python -m shared_charge serve).

    python scripts/ui_check.py [--url http://127.0.0.1:8000] [--out results/ui_check]

Loads the page at four widths, records console/page errors, exercises the
controls and confirms the numbers on screen equal the saved summary files.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
WIDTHS = {"desktop_1440": 1440, "laptop_1280": 1280, "tablet_768": 768, "mobile_390": 390}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--out", default=str(ROOT / "results" / "ui_check"))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    problems: list[str] = []
    report: dict = {"url": a.url, "checks": {}}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, width in WIDTHS.items():
            page = browser.new_page(viewport={"width": width, "height": 900})
            errors: list[str] = []
            page.on("console", lambda m, e=errors: e.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda exc, e=errors: e.append(str(exc)))
            page.goto(a.url, wait_until="networkidle")
            page.wait_for_selector("main dl")
            page.wait_for_selector("[aria-busy=false]")
            overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
            if overflow > 1:
                problems.append(f"{name}: page scrolls sideways by {overflow}px")
            page.screenshot(path=str(out / f"{name}.png"), full_page=True)
            if errors:
                problems.append(f"{name}: console errors {errors}")
            report["checks"][name] = {"horizontal_overflow_px": overflow, "console_errors": errors}
            page.close()

        # Interaction checks at desktop width
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(a.url, wait_until="networkidle")
        page.wait_for_selector("main dl")
        for tab in ("Overview", "Site", "Drivers", "Game theory", "Data"):
            page.get_by_role("button", name=tab, exact=True).click()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(400)
            page.screenshot(path=str(out / f"tab_{tab.lower().replace(' ', '_')}.png"), full_page=True)
        page.get_by_role("button", name="Overview", exact=True).click()
        page.get_by_role("button", name="High", exact=True).click()
        page.get_by_role("button", name="P1 only", exact=True).click()
        page.get_by_role("button", name="3", exact=True).click()
        page.wait_for_timeout(150)
        page.wait_for_selector("[aria-busy=false]")
        page.wait_for_load_state("networkidle")
        saved = json.loads((ROOT / "results/runs/high_P1_seed3/summary.json").read_text())["overall"]
        strip = page.locator("main dl").first.inner_text()
        expect_wait = f"{saved['avg_wait_slots']:.2f}"
        expect_idle = f"{saved['idle_slots']:,}"
        expect_served = f"{saved['completion_rate'] * 100:.1f}%"
        for label, value in (("wait", expect_wait), ("idle", expect_idle), ("served", expect_served)):
            ok = value in strip
            report["checks"][f"ui_matches_saved_{label}"] = {"expected": value, "ok": ok}
            if not ok:
                problems.append(f"metric strip missing saved {label} value {value}: {strip!r}")
        page.get_by_role("button", name="Run experiment").click()
        page.wait_for_selector("[role=status]", timeout=20000)
        toast = page.locator("[role=status]").inner_text()
        report["checks"]["rerun_toast"] = toast
        if "Identical to the saved results" not in toast:
            problems.append(f"rerun toast: {toast}")
        page.get_by_role("button", name="Site", exact=True).click()
        page.wait_for_selector("main figure svg")
        bar = page.locator("main g[role=button]").nth(3)
        bar.scroll_into_view_if_needed()
        page.wait_for_timeout(300)
        page.mouse.move(0, 0)
        bar.hover()
        page.wait_for_timeout(200)
        report["checks"]["tooltip_visible"] = page.locator("[role=tooltip]").is_visible()
        if not report["checks"]["tooltip_visible"]:
            problems.append("site plan tooltip did not appear on hover")
        page.screenshot(path=str(out / "interaction_high_P1_seed3.png"), full_page=False)
        # Sidebar expands on hover to show labels
        page.mouse.move(0, 0)
        nav = page.locator("nav[aria-label=Views]").first
        collapsed = nav.bounding_box()["width"]
        nav.hover()
        page.wait_for_timeout(400)
        expanded = nav.bounding_box()["width"]
        report["checks"]["sidebar_width_collapsed_expanded"] = [collapsed, expanded]
        page.screenshot(path=str(out / "sidebar_expanded.png"), full_page=False)
        if not expanded > collapsed + 100:
            problems.append(f"sidebar did not expand on hover: {collapsed} -> {expanded}")
        browser.close()

    report["problems"] = problems
    (out / "ui_check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
