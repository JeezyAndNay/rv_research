#!/usr/bin/env python3
"""
RV Research Viewer
Zero dependencies — Python 3 stdlib only.

Usage:
    python3 app.py                        # serves current directory on :8080
    python3 app.py /path/to/rv_research   # explicit repo path
    python3 app.py /path/to/rv_research 9000  # custom port

Quick start on Debian:
    git clone https://github.com/JeezyAndNay/rv_research
    cd rv_research
    python3 app.py
    # open http://localhost:8080
"""

import os
import sys
import json
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, unquote, parse_qs

REPO = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8080

BRAND_ORDER = ["Alliance", "Ember RV", "Grand Design", "Keystone RV", "Lance", "Outdoors RV"]

BRAND_COLORS = {
    "Overview":    "#58a6ff",
    "Alliance":    "#f0883e",
    "Ember RV":    "#e05c2e",
    "Grand Design":"#3fb950",
    "Keystone RV": "#79c0ff",
    "Lance":       "#a371f7",
    "Outdoors RV": "#56d364",
}

# External links per brand.
# NOTE: model-specific URLs follow common manufacturer patterns — verify any that 404.
BRAND_LINKS = {
    "Alliance": {
        "logo":   "https://yt3.googleusercontent.com/gb_r4UJPxdM-2MIK5HdWuDNaMoqN5Qsp4F1C9_K2a0iVpDSKswcX9aoVfNZwh-f7ZzDtB1zpqw=s900-c-k-c0x00ffffff-no-rj",
        "site":   {"label": "Alliance RV",     "url": "https://alliancerv.com/product-lines/delta/"},
        "models": [
            {"label": "Delta 281BH", "url": "https://alliancerv.com/floorplan/delta/281bh/"},
            {"label": "Delta 284RK", "url": "https://alliancerv.com/floorplan/delta/284rk/"},
        ],
        "forum":  {"label": "iRV2 Alliance",   "url": "https://www.irv2.com/forums/f447/"},
    },
    "Ember RV": {
        "logo":   "https://logo.clearbit.com/emberrv.com",
        "site":   {"label": "Ember RV",        "url": "https://emberrv.com/travel-trailers/"},
        "models": [
            {"label": "221MSL",  "url": "https://emberrv.com/travel-trailers/221msl/"},
            {"label": "26ETS",   "url": "https://emberrv.com/travel-trailers/26ets/"},
            {"label": "2500RDL", "url": "https://emberrv.com/travel-trailers/2500rdl/"},
        ],
        "forum":  {"label": "iRV2 Ember",      "url": "https://www.irv2.com/forums/f504/"},
    },
    "Grand Design": {
        "logo":   "https://logo.clearbit.com/granddesignrv.com",
        "site":   {"label": "GD Imagine",      "url": "https://granddesignrv.com/product-lines/imagine/"},
        "models": [
            {"label": "2970RL", "url": "https://granddesignrv.com/travel-trailers/imagine/2970rl/"},
            {"label": "2810BH", "url": "https://granddesignrv.com/travel-trailers/imagine/2810bh/"},
            {"label": "2800BH", "url": "https://granddesignrv.com/travel-trailers/imagine/2800bh/"},
            
                    ],
        "forum":  {"label": "GD Forum",        "url": "https://www.granddesignforum.com/"},
    },
    "Keystone RV": {
        "logo":   "https://logo.clearbit.com/keystonerv.com",
        "site":   {"label": "Keystone Outback", "url": "https://keystonerv.com/product/outback/"},
        "models": [
            {"label": "28BHWE", "url": "https://keystonerv.com/product/cougar-western-elevation/premium-travel-trailers/floorplans/28BHWE"},
            {"label": "28BHS",  "url": "https://keystonerv.com/product/cougar-western-elevation/premium-travel-trailers/floorplans/28BHS"},
            {"label": "29RLP",  "url": "https://keystonerv.com/product/cougar-western-elevation/premium-travel-trailers/floorplans/29RLP"},
            {"label": "252RD",  "url": "https://keystonerv.com/product/cougar-western-elevation/premium-travel-trailers/floorplans/252RD"},
        ],
        "forum":  {"label": "Keystone Forum",  "url": "https://www.keystonerv.net/"},
    },
    "Lance": {
        "logo":   "https://logo.clearbit.com/lancecamper.com",
        "site":   {"label": "Lance",            "url": "https://lancecamper.com/travel-trailers/"},
        "models": [
            {"label": "Evolve 2685", "url": "https://lancecamper.com/evolve/travel-trailers/2685/"},
            {"label": "2465",        "url": "https://lancecamper.com/travel-trailers/2465/"},
            {"label": "2565",        "url": "https://lancecamper.com/travel-trailers/2565/"},
        ],
        "forum":  {"label": "iRV2 Lance",       "url": "https://www.irv2.com/forums/f184/"},
    },
    "Outdoors RV": {
        "logo":   "https://logo.clearbit.com/outdoorsrvmfg.com",
        "site":   {"label": "Outdoors RV",      "url": "https://www.outdoorsrvmfg.com/"},
        "models": [
            {"label": "BC 25DVS",  "url": "https://www.outdoorsrvmfg.com/back-country-25dvs/"},
            {"label": "BC 26RPS",  "url": "https://www.outdoorsrvmfg.com/back-country-26rps/"},
            {"label": "BS 250RKS", "url": "https://www.outdoorsrvmfg.com/black-stone-250rks/"},
            {"label": "BS 250RDS", "url": "https://www.outdoorsrvmfg.com/black-stone-250rds/"},
            {"label": "BS 260KRS", "url": "https://www.outdoorsrvmfg.com/black-stone-260krs/"},
            {"label": "BS 280RKS", "url": "https://www.outdoorsrvmfg.com/black-stone-280rks/"},
        ],
        "forum":  {"label": "iRV2 Outdoors RV", "url": "https://www.irv2.com/forums/f370/"},
    },
}

def doc_type(stem: str) -> str:
    s = stem.lower()
    if s == "readme":         return ""
    if "index"      in s:    return "index"
    if "comparison" in s:    return "compare"
    if "deep_dive"  in s:    return "dive"
    if "pdi_addition" in s:  return "pdi"
    if "pdi_checklist" in s: return "pdi"
    if "walkthrough" in s:   return "script"
    if "maintenance" in s:   return "maint"
    if "product"    in s:    return "products"
    return ""

LABELS = {
    "README":                                              "Overview",
    "00_index":                                            "Master Index",
    "01_comparison_alliance_delta_vs_outdoors_rv_backcountry": "Alliance vs ORV Comparison",
    # Alliance
    "02_deep_dive_281bh_284rk":                            "Deep Dive — 281BH & 284RK",
    "03_pdi_checklist_281bh_284rk":                        "PDI Checklist",
    "04_pdi_walkthrough_script":                           "PDI Walkthrough Script",
    "05_seasonal_maintenance_schedule":                    "Maintenance Schedule",
    "06_product_list":                                     "Product List",
    # Shared pattern (Ember, GD, Keystone, Lance)
    "01_deep_dive_221msl_26ets_2500rdl":                   "Deep Dive — 221MSL, 26ETS, 2500RDL",
    "01_deep_dive_2970rl_2810bh_2800bh":                   "Deep Dive — 2970RL, 2810BH, 2800BH",
    "01_deep_dive_28bhwe_28bhs_29rlp_252rd":               "Deep Dive — 28BHWE, 28BHS, 29RLP, 252RD",
    "01_deep_dive_evolve2685_2465_2565":                   "Deep Dive — Evolve 2685, 2465, 2565",
    "02_pdi_checklist":                                    "PDI Checklist",
    "03_pdi_walkthrough_script":                           "PDI Walkthrough Script",
    "04_seasonal_maintenance_schedule":                    "Maintenance Schedule",
    "05_product_list":                                     "Product List",
    # Outdoors RV extras
    "01_deep_dive_all_4_floor_plans":                      "Deep Dive — Original 4 Plans",
    "06_deep_dive_250rks_250rds_260krs_25dvs":             "Deep Dive — New Floor Plans",
    "07_pdi_additions_250rks_250rds_260krs_25dvs":         "PDI Additions — New Floor Plans",
}

def label(path: Path) -> str:
    stem = path.stem
    return LABELS.get(stem) or re.sub(r"^\d+_", "", stem).replace("_", " ").title()

def build_tree() -> list:
    tree = []
    root_files = [f for f in sorted(REPO.glob("*.md")) if f.name != "README.md"]
    if root_files:
        tree.append({
            "label": "Overview",
            "color": BRAND_COLORS["Overview"],
            "files": [{"name": label(f), "path": f.name, "badge": doc_type(f.stem)} for f in root_files],
        })
    for brand in BRAND_ORDER:
        folder = REPO / brand
        if not folder.is_dir():
            continue
        files = sorted(folder.glob("*.md"), key=lambda f: (f.stem != "README", f.name))
        tree.append({
            "label": brand,
            "color": BRAND_COLORS.get(brand, "#58a6ff"),
            "files": [{"name": label(f), "path": f"{brand}/{f.name}", "badge": doc_type(f.stem)} for f in files],
            "links": BRAND_LINKS.get(brand),
        })
    return tree

def safe_read(rel: str) -> bytes | None:
    try:
        p = (REPO / unquote(rel)).resolve()
        p.relative_to(REPO)          # raises if outside repo
        if p.suffix == ".md" and p.is_file():
            return p.read_bytes()
    except Exception:
        pass
    return None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # silence access log

    def do_GET(self):
        parsed = urlparse(self.path)
        route  = parsed.path

        if route in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", PAGE.encode())
        elif route == "/api/tree":
            self._send(200, "application/json", json.dumps(build_tree()).encode())
        elif route == "/api/file":
            rel  = parse_qs(parsed.query).get("p", [""])[0]
            body = safe_read(rel)
            if body is None:
                self.send_error(404)
            else:
                self._send(200, "text/plain; charset=utf-8", body)
        else:
            self.send_error(404)

    def _send(self, code: int, ctype: str, body: bytes):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


# ---------------------------------------------------------------------------
# Single-page HTML — all CSS/JS inline, one CDN dependency (marked.js ~50 KB)
# ---------------------------------------------------------------------------
PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>RV Research</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0f1117;--side:#161b22;--border:#30363d;
  --text:#c9d1d9;--muted:#8b949e;--accent:#58a6ff;
  --head:#e6edf3;--code:#161b22;--row:#ffffff08;
}
body{display:flex;height:100vh;font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
     background:var(--bg);color:var(--text);overflow:hidden}

/* ── sidebar ── */
#sidebar{width:255px;min-width:255px;background:var(--side);
         border-right:1px solid var(--border);display:flex;flex-direction:column;overflow:hidden}
#sidebar-hd{padding:14px 16px;border-bottom:1px solid var(--border);flex-shrink:0}
#sidebar-hd h1{font-size:13px;font-weight:700;color:var(--head);text-transform:uppercase;letter-spacing:.6px}
#sidebar-hd p{font-size:11px;color:var(--muted);margin-top:2px}
#nav{overflow-y:auto;flex:1;padding:6px 0}
.g-label{padding:10px 14px 3px 13px;font-size:10px;font-weight:700;
          color:var(--muted);text-transform:uppercase;letter-spacing:.8px;
          border-left:3px solid transparent;margin-bottom:1px;
          display:flex;align-items:center;justify-content:space-between}
.nav-btn{display:flex;align-items:center;gap:6px;width:100%;
         padding:5px 10px 5px 22px;background:none;border:none;
         text-align:left;color:var(--muted);font-size:13px;cursor:pointer}
.nav-btn:hover{background:rgba(255,255,255,.05);color:var(--text)}
.nav-btn.active{color:#fff}
.nav-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;min-width:0}
/* ── doc-type badges ── */
.badge{flex-shrink:0;font-size:9px;font-weight:700;letter-spacing:.4px;
       text-transform:uppercase;padding:1px 5px;border-radius:3px}
.b-dive    {background:#0d2d6b;color:#79c0ff}
.b-pdi     {background:#4a2500;color:#f0883e}
.b-script  {background:#2a1a45;color:#a371f7}
.b-maint   {background:#0a2a0a;color:#56d364}
.b-products{background:#0d2040;color:#58a6ff}
.b-compare {background:#0a2828;color:#39c9bb}
.b-index   {background:#202020;color:#8b949e}

/* ── external links ── */
.link-icons{display:flex;gap:5px;padding-right:2px;flex-shrink:0}
.link-icon{font-size:12px;opacity:.4;text-decoration:none;line-height:1;transition:opacity .15s}
.link-icon:hover{opacity:1}
.model-row{display:flex;flex-wrap:wrap;gap:3px;padding:2px 10px 8px 22px}
.model-tag{font-size:9px;font-weight:600;letter-spacing:.3px;padding:2px 7px;
           border-radius:3px;border:1px solid var(--border);color:var(--muted);
           background:transparent;text-decoration:none;white-space:nowrap;transition:all .15s}
.model-tag:hover{color:var(--text);border-color:var(--muted);background:rgba(255,255,255,.05)}

/* ── main ── */
#main{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0;position:relative}
#bar{padding:9px 20px;border-bottom:1px solid var(--border);
     display:flex;align-items:center;flex-shrink:0;min-height:40px}
#doc-title{font-size:13px;font-weight:600;color:var(--muted)}
/* logo watermark — sits behind content, adjust opacity here (default .10) */
#logo-bg{position:absolute;top:40px;left:0;right:0;bottom:0;
         background-repeat:no-repeat;background-position:center;background-size:45%;
         opacity:.10;pointer-events:none;transition:background-image .35s,opacity .35s}
#scroll{flex:1;overflow-y:auto;padding:32px 48px}
#md{max-width:840px}

/* ── markdown ── */
#md h1{font-size:22px;color:var(--head);margin-bottom:16px;padding-bottom:8px;border-bottom:1px solid var(--border)}
#md h2{font-size:17px;color:var(--head);margin:28px 0 10px;padding-bottom:4px;border-bottom:1px solid var(--border)}
#md h3{font-size:14px;color:var(--head);margin:20px 0 8px}
#md h4{font-size:12px;color:var(--muted);margin:16px 0 6px;text-transform:uppercase;letter-spacing:.5px}
#md p{margin-bottom:12px;line-height:1.7}
#md ul,#md ol{margin:0 0 12px 20px;line-height:1.7}
#md li{margin-bottom:3px}
#md a{color:var(--accent);text-decoration:none}
#md a:hover{text-decoration:underline}
#md code{background:var(--code);border:1px solid var(--border);padding:1px 5px;
         border-radius:4px;font:12px/1.4 "SF Mono","Fira Code",monospace}
#md pre{background:var(--code);border:1px solid var(--border);border-radius:6px;
        padding:14px;overflow-x:auto;margin-bottom:16px}
#md pre code{border:none;padding:0;background:none}
#md blockquote{border-left:3px solid var(--accent);margin:0 0 14px;
               padding:8px 16px;background:rgba(88,166,255,.06);border-radius:0 4px 4px 0}
#md blockquote p{margin:0;color:var(--muted)}
#md table{width:100%;border-collapse:collapse;margin-bottom:20px;font-size:13px}
#md th{background:var(--side);color:var(--head);padding:8px 12px;
       text-align:left;border:1px solid var(--border);font-weight:600}
#md td{padding:7px 12px;border:1px solid var(--border);vertical-align:top}
#md tr:nth-child(even) td{background:var(--row)}
#md hr{border:none;border-top:1px solid var(--border);margin:24px 0}
#md input[type=checkbox]{margin-right:6px;accent-color:var(--accent)}

/* ── empty state ── */
#empty{display:flex;flex-direction:column;align-items:center;justify-content:center;
       height:100%;color:var(--muted);gap:12px}
#empty span{font-size:40px;opacity:.35}

/* ── scrollbar ── */
::-webkit-scrollbar{width:5px}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
</style>
</head>
<body>

<div id="sidebar">
  <div id="sidebar-hd">
    <h1>&#127958;&#65039; RV Research</h1>
    <p>Jeezy &amp; Renay</p>
  </div>
  <div id="nav" id="nav"></div>
</div>

<div id="main">
  <div id="bar"><span id="doc-title">Select a document</span></div>
  <div id="logo-bg"></div>
  <div id="scroll">
    <div id="md">
      <div id="empty"><span>&#128196;</span><p>Select a document from the sidebar</p></div>
    </div>
  </div>
</div>

<script>
marked.use({ breaks: true, gfm: true });

let active = null;

function rgba(hex, a) {
  const r = parseInt(hex.slice(1,3),16);
  const g = parseInt(hex.slice(3,5),16);
  const b = parseInt(hex.slice(5,7),16);
  return `rgba(${r},${g},${b},${a})`;
}

async function loadTree() {
  const r = await fetch('/api/tree');
  const tree = await r.json();
  const nav = document.getElementById('nav');
  for (const section of tree) {
    const color = section.color || '#58a6ff';
    const lbl = document.createElement('div');
    lbl.className = 'g-label';
    lbl.style.color = color;
    lbl.style.borderLeftColor = color;

    const lblText = document.createElement('span');
    lblText.textContent = section.label;
    lbl.appendChild(lblText);

    if (section.links) {
      const icons = document.createElement('span');
      icons.className = 'link-icons';
      const iconDefs = [
        section.links.site  && { href: section.links.site.url,  title: section.links.site.label,  icon: '🌐' },
        section.links.forum && { href: section.links.forum.url, title: section.links.forum.label, icon: '💬' },
      ].filter(Boolean);
      for (const d of iconDefs) {
        const a = document.createElement('a');
        a.href = d.href; a.target = '_blank'; a.rel = 'noopener noreferrer';
        a.title = d.title; a.className = 'link-icon'; a.textContent = d.icon;
        icons.appendChild(a);
      }
      lbl.appendChild(icons);
    }
    nav.appendChild(lbl);

    if (section.links && section.links.models && section.links.models.length) {
      const row = document.createElement('div');
      row.className = 'model-row';
      for (const m of section.links.models) {
        const a = document.createElement('a');
        a.href = m.url; a.target = '_blank'; a.rel = 'noopener noreferrer';
        a.className = 'model-tag'; a.textContent = m.label;
        row.appendChild(a);
      }
      nav.appendChild(row);
    }

    for (const file of section.files) {
      const btn = document.createElement('button');
      btn.className = 'nav-btn';
      btn.title = file.path;
      btn.dataset.path = file.path;
      btn.dataset.color = color;
      btn.dataset.logo = (section.links && section.links.logo) || '';

      const nameSpan = document.createElement('span');
      nameSpan.className = 'nav-name';
      nameSpan.textContent = file.name;
      btn.appendChild(nameSpan);

      if (file.badge) {
        const badge = document.createElement('span');
        badge.className = 'badge b-' + file.badge;
        badge.textContent = file.badge === 'dive' ? 'Deep Dive'
          : file.badge === 'pdi'      ? 'PDI'
          : file.badge === 'script'   ? 'Script'
          : file.badge === 'maint'    ? 'Maint'
          : file.badge === 'products' ? 'Products'
          : file.badge === 'compare'  ? 'Compare'
          : file.badge === 'index'    ? 'Index'
          : file.badge;
        btn.appendChild(badge);
      }

      btn.onclick = () => openDoc(file.path, file.name, btn, color);
      nav.appendChild(btn);
    }
  }
}

async function openDoc(path, name, btn, color) {
  if (active) {
    active.classList.remove('active');
    active.style.background = '';
    active.style.color = '';
  }
  active = btn;
  btn.classList.add('active');
  btn.style.background = rgba(color, 0.12);
  btn.style.color = color;

  const bar = document.getElementById('bar');
  bar.style.borderBottomColor = rgba(color, 0.4);
  document.getElementById('doc-title').textContent = name;
  document.getElementById('doc-title').style.color = color;

  const lb = document.getElementById('logo-bg');
  lb.style.backgroundImage = btn.dataset.logo ? `url('${btn.dataset.logo}')` : 'none';

  const md = document.getElementById('md');
  md.innerHTML = '<p style="color:var(--muted)">Loading…</p>';
  try {
    const r = await fetch('/api/file?p=' + encodeURIComponent(path));
    if (!r.ok) throw new Error();
    md.innerHTML = marked.parse(await r.text());
    document.getElementById('scroll').scrollTop = 0;
  } catch {
    md.innerHTML = '<p style="color:#f85149">Failed to load document.</p>';
  }
}

loadTree();
</script>
</body>
</html>"""


if __name__ == "__main__":
    print(f"\n  RV Research Viewer")
    print(f"  Repo : {REPO}")
    print(f"  URL  : http://localhost:{PORT}")
    print(f"  Stop : Ctrl+C\n")
    try:
        HTTPServer(("", PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")
