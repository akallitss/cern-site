#!/usr/bin/env python3
"""
build_hub.py — scan notes/**/*.html, extract metadata, and generate:

  notes/index.html      public hub (all *listed* notes)
  notes/notes.json      machine-readable manifest of the same
  <private_hub>         hub listing *everything* incl. unlisted notes (path from site.config.json)
  notes/unlisted/index.html   redirect stub so the folder never shows a directory listing

Metadata sources, in priority order:
  title        <meta name="title">  ->  <title>  ->  first <h1>  ->  filename
  description  <meta name="description">  ->  first <p> (trimmed)
  category     <meta name="category">  ->  sub-directory name  ->  keyword rules  ->  default
  tags         <meta name="keywords"> (comma separated)
  date         <meta name="date">  ->  git first-commit date  ->  file mtime
  updated      <meta name="updated">  ->  git last-commit date  ->  file mtime
  visibility   <meta name="visibility" content="unlisted">  or  living in notes/unlisted/  -> unlisted

Only the standard library is used.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "site.config.json").read_text(encoding="utf-8"))
NOTES_DIR = ROOT / CONFIG.get("notes_dir", "notes")
UNLISTED_SUBDIR = CONFIG.get("unlisted_subdir", "unlisted")
DEFAULT_CATEGORY = CONFIG.get("default_category", "Miscellaneous")
GENERATED = {"index.html", "notes.json"}  # files inside notes/ that we write ourselves


# --------------------------------------------------------------------------- helpers
def _git(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return ""


def git_first_date(rel: str) -> str:
    out = _git("log", "--diff-filter=A", "--follow", "--format=%aI", "--", rel)
    return out.splitlines()[-1][:10] if out else ""


def git_last_date(rel: str) -> str:
    out = _git("log", "-1", "--format=%aI", "--", rel)
    return out[:10] if out else ""


def mtime_date(p: Path) -> str:
    return dt.date.fromtimestamp(p.stat().st_mtime).isoformat()


META_RE = re.compile(r'<meta\s+[^>]*?name\s*=\s*["\']([^"\']+)["\'][^>]*?content\s*=\s*["\']([^"\']*)["\'][^>]*>', re.I | re.S)
META_RE_REV = re.compile(r'<meta\s+[^>]*?content\s*=\s*["\']([^"\']*)["\'][^>]*?name\s*=\s*["\']([^"\']+)["\'][^>]*>', re.I | re.S)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)
P_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<(script|style)\b.*?(</\1\s*>|$)", re.I | re.S)
WS_RE = re.compile(r"\s+")


def strip_tags(s: str) -> str:
    return WS_RE.sub(" ", html.unescape(TAG_RE.sub(" ", s))).strip()


def read_head(p: Path, limit: int = 200_000) -> str:
    """Read only the beginning of a (possibly huge) file — enough for <head> and first paragraphs."""
    with p.open("r", encoding="utf-8", errors="replace") as fh:
        return fh.read(limit)


def parse_meta(text: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    for name, content in META_RE.findall(text):
        meta.setdefault(name.lower(), html.unescape(content).strip())
    for content, name in META_RE_REV.findall(text):
        meta.setdefault(name.lower(), html.unescape(content).strip())
    return meta


def guess_category(title: str, desc: str, body: str, tags: list[str]) -> str:
    hay = " ".join([title, desc, " ".join(tags), body[:20_000]]).lower()
    best, best_score = DEFAULT_CATEGORY, 0
    for rule in CONFIG.get("categories", []):
        score = sum(hay.count(k.lower()) for k in rule.get("keywords", []))
        if score > best_score:
            best, best_score = rule["name"], score
    return best


def human_size(n: int) -> str:
    for unit in ("B", "kB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


# --------------------------------------------------------------------------- scan
def scan() -> list[dict]:
    notes: list[dict] = []
    private_hub = CONFIG.get("private_hub")
    private_hub_path = (ROOT / private_hub).resolve() if private_hub else None

    for p in sorted(NOTES_DIR.rglob("*.html")):
        rel_notes = p.relative_to(NOTES_DIR).as_posix()
        if p.name in GENERATED and p.parent == NOTES_DIR:
            continue
        if private_hub_path and p.resolve() == private_hub_path:
            continue
        if p.parent.name == UNLISTED_SUBDIR and p.name == "index.html":
            continue  # our redirect stub

        rel_root = p.relative_to(ROOT).as_posix()
        text = read_head(p)
        meta = parse_meta(text)
        # for fallback title/description/category, ignore inline scripts & styles (huge in Plotly/JSROOT exports)
        prose = SCRIPT_RE.sub(" ", text)
        subdir = p.parent.relative_to(NOTES_DIR).as_posix()
        subdir = "" if subdir == "." else subdir

        title = meta.get("title") or ""
        if not title:
            m = TITLE_RE.search(text)
            title = strip_tags(m.group(1)) if m else ""
        if not title:
            m = H1_RE.search(prose)
            title = strip_tags(m.group(1)) if m else ""
        if not title:
            title = p.stem.replace("_", " ").replace("-", " ").strip()

        desc = meta.get("description") or ""
        if not desc:
            for m in P_RE.finditer(prose):
                cand = strip_tags(m.group(1))
                if len(cand) > 30:
                    desc = cand[:220] + ("…" if len(cand) > 220 else "")
                    break

        tags = [t.strip() for t in re.split(r"[,;]", meta.get("keywords", "")) if t.strip()]

        unlisted = meta.get("visibility", "").lower() in {"unlisted", "private", "hidden"} or \
            subdir.split("/")[0] == UNLISTED_SUBDIR

        category = meta.get("category") or ""
        if not category and subdir and subdir.split("/")[0] != UNLISTED_SUBDIR:
            category = subdir.split("/")[0].replace("_", " ").replace("-", " ").title()
        if not category:
            category = guess_category(title, desc, strip_tags(prose), tags)

        date = meta.get("date") or git_first_date(rel_root) or mtime_date(p)
        updated = meta.get("updated") or git_last_date(rel_root) or mtime_date(p)
        if updated < date:
            updated = date

        notes.append({
            "title": title,
            "description": desc,
            "category": category,
            "tags": tags,
            "date": date[:10],
            "updated": updated[:10],
            "unlisted": unlisted,
            "path": rel_notes,               # relative to notes/
            "url": "/" + rel_root,           # absolute on the site
            "size": p.stat().st_size,
            "size_h": human_size(p.stat().st_size),
        })

    notes.sort(key=lambda n: (n["date"], n["updated"], n["title"]), reverse=True)
    return notes


# --------------------------------------------------------------------------- render
def render_hub(notes: list[dict], *, title: str, private: bool, base_rel: str) -> str:
    """base_rel: relative path prefix from the hub file to the notes/ directory (e.g. '' or '')."""
    cats: dict[str, list[dict]] = {}
    for n in notes:
        cats.setdefault(n["category"], []).append(n)
    cat_names = sorted(cats, key=lambda c: (-len(cats[c]), c))
    esc = html.escape
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    chips = ['<button class="chip active" data-cat="*">All <span class="cnt">%d</span></button>' % len(notes)]
    chips += ['<button class="chip" data-cat="%s">%s <span class="cnt">%d</span></button>' % (esc(c), esc(c), len(cats[c])) for c in cat_names]

    items = []
    for n in notes:
        tags = "".join(f'<span class="pill gray">{esc(t)}</span>' for t in n["tags"])
        badge = '<span class="pill" style="background:#fde8e8;color:#b42318">unlisted</span>' if n["unlisted"] else ""
        upd = f' · updated {esc(n["updated"])}' if n["updated"] != n["date"] else ""
        search = esc(" ".join([n["title"], n["description"], n["category"], " ".join(n["tags"]), n["path"]]).lower())
        items.append(f'''
      <li class="note" data-cat="{esc(n["category"])}" data-search="{search}" data-date="{esc(n["date"])}">
        <div class="note-main">
          <a class="note-title" href="{esc(base_rel + n["path"])}">{esc(n["title"])}</a>
          {('<p class="note-desc">' + esc(n["description"]) + '</p>') if n["description"] else ""}
          <div class="meta-row small">
            <span class="pill">{esc(n["category"])}</span>{badge}{tags}
            <span class="faint">{esc(n["path"])} · {esc(n["size_h"])}</span>
          </div>
        </div>
        <time class="note-date" datetime="{esc(n["date"])}">{esc(n["date"])}<span class="faint small">{upd}</span></time>
      </li>''')

    robots = '<meta name="robots" content="noindex,nofollow">' if private else ""
    site = esc(CONFIG.get("site_name", "Notes"))
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{robots}
<title>{esc(title)} — {site}</title>
<link rel="stylesheet" href="{esc(base_rel)}../assets/site.css">
<style>
  .hub-head {{ display:flex; align-items:baseline; justify-content:space-between; gap:1rem; flex-wrap:wrap; }}
  .search {{ width:100%; padding:.7em .9em; font:inherit; border:1px solid var(--border); border-radius:8px; background:var(--bg-elev); color:var(--fg); margin:1rem 0 .8rem; }}
  .search:focus {{ outline:2px solid var(--accent-soft); border-color:var(--accent); }}
  .chips {{ display:flex; flex-wrap:wrap; gap:.4rem; margin-bottom:1.2rem; }}
  .chip {{ font:inherit; font-size:.85rem; padding:.35em .8em; border-radius:999px; border:1px solid var(--border); background:var(--bg-elev); color:var(--fg-muted); cursor:pointer; }}
  .chip .cnt {{ color:var(--fg-faint); margin-left:.25em; }}
  .chip:hover {{ border-color:var(--accent); color:var(--accent); }}
  .chip.active {{ background:var(--accent); border-color:var(--accent); color:#fff; }}
  .chip.active .cnt {{ color:rgba(255,255,255,.75); }}
  .notes {{ list-style:none; padding:0; margin:0; }}
  .note {{ display:flex; gap:1rem; justify-content:space-between; align-items:flex-start; padding:1rem 0; border-bottom:1px solid var(--border); }}
  .note.hidden {{ display:none; }}
  .note-title {{ font-weight:600; font-size:1.05rem; }}
  .note-desc {{ margin:.25rem 0 .4rem; color:var(--fg-muted); font-size:.95rem; }}
  .note-date {{ white-space:nowrap; color:var(--fg-muted); font-size:.9rem; font-variant-numeric:tabular-nums; text-align:right; padding-top:.2rem; }}
  .note-date .faint {{ display:block; }}
  .cat-h {{ margin:2rem 0 .2rem; font-size:1rem; text-transform:uppercase; letter-spacing:.06em; color:var(--fg-muted); }}
  .empty {{ padding:2rem 0; color:var(--fg-muted); display:none; }}
  .toolbar {{ display:flex; gap:1rem; align-items:center; flex-wrap:wrap; font-size:.9rem; color:var(--fg-muted); }}
  .toolbar label {{ cursor:pointer; }}
  @media (max-width:560px) {{ .note {{ flex-direction:column; gap:.3rem; }} .note-date {{ text-align:left; }} }}
</style>
</head>
<body>
<header class="site-header"><div class="wrap">
  <a class="brand" href="{esc(base_rel)}../">{site}</a>
  <nav class="nav"><a href="{esc(base_rel)}../">Home</a><a class="active" href="{esc(base_rel)}index.html">Notes</a></nav>
</div></header>

<main class="wrap">
  <div class="hub-head">
    <h1>{esc(title)}</h1>
    <span class="muted small">{len(notes)} notes · {len(cats)} categories · built {now}</span>
  </div>
  <p class="muted">Everything I have written up as an HTML page, newest first. Filter by category or search by title, tag or text.</p>

  <input class="search" id="q" type="search" placeholder="Search notes…" autocomplete="off">
  <div class="chips" id="chips">{"".join(chips)}</div>
  <div class="toolbar">
    <label><input type="checkbox" id="grouped" checked> group by category</label>
    <span id="shown"></span>
  </div>

  <ul class="notes" id="list">{"".join(items)}
  </ul>
  <p class="empty" id="empty">No notes match.</p>
</main>

<footer class="site-footer"><div class="wrap">
  <span>Generated by <code>scripts/build_hub.py</code></span>
  <span><a href="{esc(base_rel)}notes.json">notes.json</a></span>
</div></footer>

<script>
(function () {{
  const q = document.getElementById('q'), list = document.getElementById('list'),
        chips = document.getElementById('chips'), grouped = document.getElementById('grouped'),
        empty = document.getElementById('empty'), shown = document.getElementById('shown');
  const notes = Array.from(list.querySelectorAll('.note'));
  let cat = '*';

  function apply() {{
    const needle = q.value.trim().toLowerCase();
    let n = 0;
    notes.forEach(el => {{
      const ok = (cat === '*' || el.dataset.cat === cat) && (!needle || el.dataset.search.includes(needle));
      el.classList.toggle('hidden', !ok); if (ok) n++;
    }});
    empty.style.display = n ? 'none' : 'block';
    shown.textContent = n === notes.length ? '' : n + ' shown';
    layout();
  }}
  function layout() {{
    list.querySelectorAll('.cat-h').forEach(h => h.remove());
    if (!grouped.checked || cat !== '*') return;
    const seen = new Set();
    // group: move visible notes under headers, keeping date order inside each group
    const byCat = {{}};
    notes.forEach(el => {{ (byCat[el.dataset.cat] ||= []).push(el); }});
    const order = Object.keys(byCat).sort((a, b) => byCat[b].length - byCat[a].length || a.localeCompare(b));
    order.forEach(c => {{
      const vis = byCat[c].filter(el => !el.classList.contains('hidden'));
      if (!vis.length) return;
      const h = document.createElement('li'); h.className = 'cat-h'; h.textContent = c + ' (' + vis.length + ')';
      list.appendChild(h); byCat[c].forEach(el => list.appendChild(el));
    }});
  }}
  function ungroupOrder() {{ notes.forEach(el => list.appendChild(el)); }}
  chips.addEventListener('click', e => {{
    const b = e.target.closest('.chip'); if (!b) return;
    chips.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    b.classList.add('active'); cat = b.dataset.cat; ungroupOrder(); apply();
  }});
  grouped.addEventListener('change', () => {{ ungroupOrder(); apply(); }});
  q.addEventListener('input', apply);
  if (location.hash.length > 1) {{ q.value = decodeURIComponent(location.hash.slice(1)); }}
  apply();
}})();
</script>
</body>
</html>
'''


REDIRECT_STUB = """<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow">
<meta http-equiv="refresh" content="0; url=../"><title>Redirecting…</title></head><body></body></html>
"""


def main() -> int:
    if not NOTES_DIR.exists():
        print(f"notes dir {NOTES_DIR} does not exist", file=sys.stderr)
        return 1
    notes = scan()
    listed = [n for n in notes if not n["unlisted"]]

    (NOTES_DIR / "index.html").write_text(render_hub(listed, title="Notes", private=False, base_rel=""), encoding="utf-8")
    manifest = {"generated": dt.datetime.now().isoformat(timespec="seconds"), "count": len(listed), "notes": listed}
    (NOTES_DIR / "notes.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    private_hub = CONFIG.get("private_hub")
    if private_hub:
        out = ROOT / private_hub
        out.parent.mkdir(parents=True, exist_ok=True)
        # base_rel: path from the private hub's folder to notes/
        base_rel = os.path.relpath(NOTES_DIR, out.parent).replace(os.sep, "/")
        base_rel = "" if base_rel == "." else base_rel + "/"
        out.write_text(render_hub(notes, title="All notes (incl. unlisted)", private=True, base_rel=base_rel), encoding="utf-8")

    unl = NOTES_DIR / UNLISTED_SUBDIR
    if unl.exists():
        (unl / "index.html").write_text(REDIRECT_STUB, encoding="utf-8")

    n_unl = len(notes) - len(listed)
    print(f"hub: {len(listed)} listed, {n_unl} unlisted, {len({n['category'] for n in notes})} categories")
    for n in notes:
        flag = " (unlisted)" if n["unlisted"] else ""
        print(f"  {n['date']}  [{n['category']}]  {n['title']}{flag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
