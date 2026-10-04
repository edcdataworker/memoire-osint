"""Read-only browser layout audit on an explicitly fictional local catalogue."""

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = os.environ["AGENT_BROWSER"]
SCANNER = Path(os.environ["BUTTON_SCANNER"]).read_text()


def browser(*args):
    if args[0] == "eval" and "const audit=" in args[1]:
        args = (
            "eval",
            "(()=>{" + args[1].replace(";JSON.stringify", ";return JSON.stringify") + "})()",
        )
    return subprocess.check_output([CLI, "--session", "memoire-cloture", *args], text=True)


def main():
    browser("open", "http://127.0.0.1:18745/")
    browser(
        "eval",
        'document.querySelector("[data-tab=corpus]").click();for(const id of ["corpus-start","corpus-end"]){document.getElementById(id).value="2023-11-26";}document.getElementById("corpus-form").requestSubmit()',
    )
    browser("wait", "500")
    results = []
    sizes = (
        [
            (w, 900, 1)
            for w in (
                320,
                390,
                560,
                649,
                650,
                651,
                700,
                775,
                849,
                850,
                851,
                1024,
                1149,
                1150,
                1151,
                1280,
                1440,
            )
        ]
        + [(1280, 450, 1)]
        + [(1440, 1000, z) for z in (1.25, 1.5, 2)]
    )
    for width, height, zoom in sizes:
        browser("set", "viewport", str(width), str(height))
        browser("open", "http://127.0.0.1:18745/")
        browser(
            "eval",
            'document.querySelector("[data-tab=corpus]").click();for(const id of ["corpus-start","corpus-end"]){document.getElementById(id).value="2023-11-26";}document.getElementById("corpus-form").requestSubmit()',
        )
        browser("wait", "250")
        for view in ("collecte", "suivi", "corpus"):
            for position in ("top", "bottom"):
                expression = (
                    "document.body.style.zoom="
                    + str(zoom)
                    + ';document.querySelector("[data-tab='
                    + view
                    + ']").click();window.scrollTo(0,'
                    + ("0" if position == "top" else "document.documentElement.scrollHeight")
                    + ");globalThis.__buttonAuditOptions={};const audit="
                    + SCANNER
                    + ";JSON.stringify({horizontal:document.documentElement.scrollWidth>innerWidth+1,audit})"
                )
                raw = browser("eval", expression)
                value = json.loads(raw)
                if isinstance(value, str):
                    value = json.loads(value)
                results.append(
                    {
                        "width": width,
                        "height": height,
                        "css_zoom": zoom,
                        "view": view,
                        "position": position,
                        **value,
                    }
                )
        browser(
            "eval",
            'document.querySelector("[data-tab=corpus]").click();document.querySelector("[data-article]").click()',
        )
        expression = (
            'globalThis.__buttonAuditOptions={rootSelector:"#article-dialog"};const audit='
            + SCANNER
            + ";JSON.stringify({audit})"
        )
        value = json.loads(browser("eval", expression))
        if isinstance(value, str):
            value = json.loads(value)
        results.append(
            {"width": width, "height": height, "css_zoom": zoom, "view": "article_dialog", **value}
        )
        browser("press", "Escape")
    browser("set", "viewport", "390", "900")
    browser(
        "eval",
        'document.body.style.zoom=1;document.querySelector("[data-tab=collecte]").click();window.scrollTo(0,0)',
    )
    browser("press", "Tab")
    focus = json.loads(
        browser(
            "eval",
            "JSON.stringify({focus:document.activeElement.tagName,outline:getComputedStyle(document.activeElement).outlineStyle})",
        )
    )
    browser("screenshot", str(ROOT / "Preuves/Collecte_TASS/Cloture_mobile.png"))
    report = {
        "fixture": True,
        "matrix": results,
        "focus": focus,
        "zoom_method": "CSS body zoom, not native browser zoom",
        "browser": "Chrome on macOS",
        "scanner_limit": "Visible button geometry heuristic; other browsers not tested",
    }
    (ROOT / "Preuves/Collecte_TASS/Responsive_final.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    failures = [r for r in results if r.get("horizontal") or r["audit"]["issues"]]
    print(json.dumps({"states": len(results), "failures": failures}))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
