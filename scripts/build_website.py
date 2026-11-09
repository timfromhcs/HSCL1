#!/usr/bin/env python3
"""Build the static HSCL1 website (EN/DE/FR) into website/dist. No dependencies beyond Python 3.

Inputs : themes/tokens/tokens.json (colours), website/content/{en,de,fr}.json (all text), website/data/release.json (REAL release
         metadata written by scripts/fetch_release_meta.py), docs/img (real screenshots).
Output : website/dist/{,de/,fr/}index.html, {,de/,fr/}download/index.html, style.css, img/, robots.txt, and sitemap.xml
         when SITE_URL is set (canonical and hreflang URLs need an absolute origin; without it they are left out, never guessed).

Rules: the download button exists only when release.json names a real release; every download link is an asset URL from that file;
no fabricated numbers, quotes or badges.
"""
from __future__ import annotations

import html
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "website"
LANGS = ["en", "de", "fr"]
REPO = "timfromhcs/HSCL1"


def e(s: object) -> str:
    return html.escape(str(s), quote=True)


def css(tokens: dict) -> str:
    dark, light = tokens["themes"]["hcs-midnight"], tokens["themes"]["hcs-light"]
    var = lambda t: "".join(f"--{k}:{v};" for k, v in t.items())  # noqa: E731
    return f""":root{{{var(dark)}color-scheme:dark light}}
@media (prefers-color-scheme: light){{:root{{{var(light)}}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--surface-0);color:var(--text-primary);font:16px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
a{{color:var(--accent);text-underline-offset:3px}} a:hover{{color:var(--accent-hover)}}
:focus-visible{{outline:3px solid var(--focus-ring);outline-offset:3px;border-radius:4px}}
.skip{{position:absolute;left:-999px;top:0;background:var(--surface-1);color:var(--text-primary);padding:.75rem 1rem;z-index:10}}
.skip:focus{{left:1rem;top:1rem}}
.wrap{{max-width:68rem;margin:0 auto;padding:0 1rem}}
header.site{{border-bottom:1px solid var(--border-subtle);background:var(--surface-1)}}
header.site .wrap{{display:flex;flex-wrap:wrap;gap:.75rem 1.5rem;align-items:center;justify-content:space-between;min-height:3.5rem}}
.brand{{display:inline-flex;align-items:center;gap:.5rem;font-weight:700;letter-spacing:.02em;color:var(--text-primary);text-decoration:none}}
nav ul{{display:flex;flex-wrap:wrap;gap:.25rem 1.25rem;list-style:none;margin:0;padding:0;align-items:center}}
nav a{{display:inline-block;padding:.5rem .25rem;min-height:2.5rem}}
nav a[aria-current=page]{{color:var(--text-primary);font-weight:600}}
.hero{{padding:4rem 0 3rem}}
h1{{font-size:clamp(2rem,6vw,3.5rem);line-height:1.1;margin:0 0 1rem}}
h2{{font-size:1.6rem;margin:3rem 0 1rem}} h3{{margin:.25rem 0}}
.eyebrow{{margin:0 0 .5rem;color:var(--accent);font-weight:600;letter-spacing:.04em}}
.lead{{font-size:1.2rem;color:var(--text-secondary);max-width:42rem}}
.btns{{display:flex;gap:.75rem;flex-wrap:wrap;margin-top:1.5rem}}
.btn{{display:inline-block;padding:.75rem 1.25rem;border-radius:.6rem;background:var(--accent);color:var(--text-inverse);font-weight:600;text-decoration:none;min-height:2.75rem}}
.btn:hover{{background:var(--accent-hover);color:var(--text-inverse)}}
.btn.ghost{{background:transparent;color:var(--text-primary);border:1px solid var(--border-strong)}}
.btn.ghost:hover{{background:var(--accent-soft);color:var(--text-primary)}}
.grid{{display:grid;gap:1rem;grid-template-columns:repeat(auto-fit,minmax(15rem,1fr))}}
.card{{background:var(--surface-1);border:1px solid var(--border-subtle);border-radius:1rem;padding:1.25rem}}
.card p{{margin:.25rem 0 0;color:var(--text-secondary)}}
figure{{margin:0}} figure img{{width:100%;height:auto;border-radius:.75rem;border:1px solid var(--border-subtle);display:block}}
.note{{border-left:4px solid var(--warning);background:var(--surface-1);padding:1rem 1.25rem;border-radius:.5rem}}
.note ul,.card ul{{margin:.5rem 0 0;padding-left:1.25rem}}
dl.meta{{display:grid;grid-template-columns:max-content 1fr;gap:.5rem 1.5rem}} dl.meta dt{{color:var(--text-muted)}} dl.meta dd{{margin:0;overflow-wrap:anywhere}}
code,.mono{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.92em}}
table{{border-collapse:collapse;width:100%}} th,td{{text-align:left;padding:.5rem .75rem;border-bottom:1px solid var(--border-subtle)}}
footer.site{{margin-top:4rem;border-top:1px solid var(--border-subtle);padding:2rem 0;color:var(--text-secondary)}}
@media (max-width:40rem){{dl.meta{{grid-template-columns:1fr}} dl.meta dt{{margin-top:.5rem}}}}
@media (prefers-reduced-motion:no-preference){{.btn{{transition:background .15s}}}}
"""


def human_size(n: int) -> str:
    return f"{n / 1e9:.2f} GB" if n >= 1e9 else f"{n / 1e6:.1f} MB"


def prefix(lang: str) -> str:
    return "" if lang == "en" else f"/{lang}"


def page(lang: str, c: dict, path: str, title: str, body: str, site: str | None) -> str:
    n = c["nav"]
    home, dl = f"{prefix(lang)}/" if prefix(lang) else "/", f"{prefix(lang)}/download/"
    cur = lambda p: ' aria-current="page"' if path == p else ""  # noqa: E731
    langs = "".join(
        f'<li><a href="{prefix(l)}{path or "/"}" hreflang="{l}" lang="{l}"{" aria-current=true" if l == lang else ""}>{e(l.upper())}</a></li>'
        for l in LANGS)
    alt = ""
    if site:
        alt = f'<link rel="canonical" href="{e(site + prefix(lang) + path)}">' + "".join(
            f'<link rel="alternate" hreflang="{l}" href="{e(site + prefix(l) + path)}">' for l in LANGS
        ) + f'<link rel="alternate" hreflang="x-default" href="{e(site + path)}">'
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(c["description"])}">
<meta name="color-scheme" content="dark light">
{alt}
<link rel="icon" href="/img/favicon.ico">
<link rel="stylesheet" href="/style.css">
</head>
<body>
<a class="skip" href="#main">{e(n["skip"])}</a>
<header class="site"><div class="wrap">
<a class="brand" href="{home}"><picture><source srcset="/img/hscl1-mark-light.svg" media="(prefers-color-scheme: light)"><img src="/img/hscl1-mark-dark.svg" alt="" width="28" height="28"></picture> HSCL1</a>
<nav aria-label="Main"><ul>
<li><a href="{home}"{cur("/")}>{e(n["home"])}</a></li>
<li><a href="{dl}"{cur("/download/")}>{e(n["download"])}</a></li>
<li><a href="{prefix(lang)}/install/vm/"{cur("/install/vm/")}>{e(n["vm"])}</a></li>
<li><a href="{prefix(lang)}/security/"{cur("/security/")}>{e(n["security"])}</a></li>
</ul></nav>
<nav aria-label="{e(n["lang"])}"><ul>{langs}</ul></nav>
</div></header>
<main id="main" class="wrap">
{body}
</main>
<footer class="site"><div class="wrap">
<p><strong>HSCL1</strong> = {e(c["expansion"])}</p>
<p>{e(c["footer"]["credit"])} &middot; {e(c["footer"]["license"])}</p>
<p><a href="https://github.com/{REPO}">{e(c["footer"]["source"])}</a> &middot; <a href="https://github.com/{REPO}/issues">{e(c["footer"]["issues"])}</a></p>
</div></footer>
</body>
</html>
"""


def home(lang: str, c: dict, rel: dict | None) -> str:
    h = c["hero"]
    cta = f'<a class="btn" href="{prefix(lang)}/download/">{e(h["cta"])}</a>' if rel else ""
    modes = "".join(f'<div class="card"><h3>{e(m["t"])}</h3><p>{e(m["d"])}</p></div>' for m in c["modes"])
    shots = "".join(f'<figure><img src="/{e(s["src"])}" alt="{e(s["alt"])}" loading="lazy" width="1280" height="800"></figure>' for s in c["shots"])
    honest = "".join(f"<li>{e(x)}</li>" for x in c["honest"])
    return f"""<section class="hero"><p class="eyebrow">HSCL1 &middot; {e(c["expansion"])}</p><h1>{e(h["h1"])}</h1><p class="lead">{e(h["sub"])}</p>
<div class="btns">{cta}<a class="btn ghost" href="#modes">{e(h["cta2"])}</a></div></section>
<section aria-labelledby="modes"><h2 id="modes">{e(c["modes_h"])}</h2><div class="grid">{modes}</div></section>
<section aria-labelledby="shots"><h2 id="shots">{e(c["shots_h"])}</h2><div class="grid">{shots}</div></section>
<section aria-labelledby="honest"><h2 id="honest">{e(c["honest_h"])}</h2><div class="note"><ul>{honest}</ul></div></section>"""


def download(lang: str, c: dict, rel: dict | None) -> str:
    d = c["dl"]
    if not rel:
        return f'<section class="hero"><h1>{e(d["h1"])}</h1><p class="note">{e(d["none"])}</p></section>'
    parts = [a for a in rel["assets"]]
    total = sum(a["size"] for a in parts if ".part" in a["name"])
    whole = rel.get("whole_image")
    rows = "".join(f'<tr><td><a href="{e(a["url"])}">{e(a["name"])}</a></td><td>{e(human_size(a["size"]))}</td></tr>' for a in parts)
    sha = f'<dt>{e(d["sha"])}</dt><dd class="mono">{e(whole["sha256"])}</dd>' if whole else ""
    pre = f'<p class="note"><strong>{e(d["pre"])}</strong></p>' if rel["prerelease"] else ""
    ver = "".join(f"<li>{e(x)}</li>" for x in d["verify"])
    lim = "".join(f"<li>{e(x)}</li>" for x in d["limits"])
    return f"""<section class="hero"><h1>{e(d["h1"])}</h1>{pre}
<dl class="meta"><dt>{e(d["version"])}</dt><dd>{e(rel["tag"])}</dd><dt>{e(d["released"])}</dt><dd>{e(rel["published_at"][:10])}</dd>
<dt>{e(d["size"])}</dt><dd>{e(human_size(total))}</dd>{sha}</dl>
<p><a class="btn ghost" href="{e(rel["url"])}">{e(d["tag"])}</a></p></section>
<section aria-labelledby="files"><h2 id="files">{e(d["parts"])}</h2><p>{e(d["parts_note"])}</p>
<table><tbody>{rows}</tbody></table></section>
<section aria-labelledby="verify"><h2 id="verify">{e(d["verify_h"])}</h2><ol>{ver}</ol></section>
<section aria-labelledby="limits"><h2 id="limits">{e(d["limits_h"])}</h2><div class="note"><ul>{lim}</ul></div></section>"""


def security(lang: str, c: dict) -> str:
    x = c["sec"]
    lst = lambda items: "<ul>" + "".join(f"<li>{e(i)}</li>" for i in items) + "</ul>"  # noqa: E731
    links = "".join(f'<li><a href="{e(l["u"])}">{e(l["t"])}</a></li>' for l in x["docs_links"])
    return f"""<section class="hero"><h1>{e(x["h1"])}</h1><p class="lead">{e(x["intro"])}</p></section>
<section aria-labelledby="report"><h2 id="report">{e(x["report_h"])}</h2><p>{e(x["report"])}</p>
<p><a class="btn ghost" href="https://github.com/{REPO}/security">{e(x["report_link"])}</a></p></section>
<section aria-labelledby="integrity"><h2 id="integrity">{e(x["integrity_h"])}</h2>{lst(x["integrity"])}</section>
<section aria-labelledby="claims"><h2 id="claims">{e(x["claims_h"])}</h2><div class="note">{lst(x["claims"])}</div></section>
<section aria-labelledby="dev"><h2 id="dev">{e(x["dev_h"])}</h2><p>{e(x["dev"])}</p></section>
<section aria-labelledby="docs"><h2 id="docs">{e(x["docs_h"])}</h2><p>{e(x["docs"])}</p><ul>{links}</ul></section>"""


def vm(lang: str, c: dict) -> str:
    x = c["vm"]
    rows = "".join(f"<tr><th scope=\"row\">{e(a)}</th><td>{e(b)}</td></tr>" for a, b in x["rows"])
    lst = lambda items: "<ul>" + "".join(f"<li>{e(i)}</li>" for i in items) + "</ul>"  # noqa: E731
    return f"""<section class="hero"><h1>{e(x["h1"])}</h1><p class="note">{e(x["intro"])}</p></section>
<section aria-labelledby="table"><h2 id="table">{e(x["table_h"])}</h2><table><tbody>{rows}</tbody></table></section>
<section aria-labelledby="steps"><h2 id="steps">{e(x["steps_h"])}</h2>{lst(x["steps"])}</section>
<section aria-labelledby="not"><h2 id="not">{e(x["not_h"])}</h2><div class="note">{lst(x["not"])}</div><p>{e(x["script"])}</p></section>"""


def build(out: Path, site: str | None) -> list[str]:
    tokens = json.loads((ROOT / "themes/tokens/tokens.json").read_text(encoding="utf-8"))
    meta = json.loads((WEB / "data/release.json").read_text(encoding="utf-8"))
    rel = meta.get("release")
    if out.exists():
        shutil.rmtree(out)
    (out / "img").mkdir(parents=True)
    (out / "style.css").write_text(css(tokens), encoding="utf-8")
    for s in ["desktop-rain.png", "control-center.png"]:
        shutil.copy2(ROOT / "docs/img" / s, out / "img" / s)
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:  # brand assets are generated, not committed
        subprocess.run([sys.executable, str(ROOT / "scripts/gen_brand.py"), tmp, "--sizes", "16,32,48,256"], check=True, capture_output=True)
        for f in ["favicon.ico", "hscl1-mark-dark.svg", "hscl1-mark-light.svg"]:
            shutil.copy2(Path(tmp) / f, out / "img" / f)
    urls = []
    for lang in LANGS:
        c = json.loads((WEB / f"content/{lang}.json").read_text(encoding="utf-8"))
        for path, body, title in [("/", home(lang, c, rel), c["title"]), ("/download/", download(lang, c, rel), f'{c["dl"]["h1"]} - HSCL1'),
                            ("/install/vm/", vm(lang, c), c["vm"]["title"]),
                            ("/security/", security(lang, c), c["sec"]["title"])]:
            target = out / (prefix(lang).lstrip("/")) / path.strip("/") / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(page(lang, c, path, title, body, site), encoding="utf-8")
            urls.append(prefix(lang) + path)
    (out / "robots.txt").write_text("User-agent: *\nAllow: /\n" + (f"Sitemap: {site}/sitemap.xml\n" if site else ""), encoding="utf-8")
    if site:
        (out / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                         + "".join(f"<url><loc>{e(site + u)}</loc></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")
    return urls


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Build the HSCL1 landing page into an output directory.")
    ap.add_argument("outdir", nargs="?", default=str(WEB / "dist"), help="output directory (default: website/dist)")
    ap.add_argument("--out", dest="out_flag", help="output directory (same as the positional argument)")
    args = ap.parse_args(argv)
    # Until 2026-11-09 an unknown flag was taken as the output directory and `--help` silently created
    # a directory literally named "--help". argparse now rejects unknown flags.
    out = Path(args.out_flag or args.outdir)
    site = os.environ.get("SITE_URL", "").rstrip("/") or None
    urls = build(out, site)
    print(f"built {len(urls)} pages into {out}" + ("" if site else " (SITE_URL not set: no canonical/hreflang/sitemap)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
