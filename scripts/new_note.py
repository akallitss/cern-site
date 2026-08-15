#!/usr/bin/env python3
"""
new_note.py — scaffold a new HTML note from templates/note.html.

usage:
  scripts/new_note.py "Title of the note" [--slug my-slug] [--category "Detector R&D"]
                      [--tags "a,b,c"] [--desc "one-liner"] [--unlisted] [--subdir sub/dir]
                      [--date YYYY-MM-DD] [--force]

Prints the path of the created file. Slug defaults to a kebab-cased title,
prefixed with the date (YYYY-MM-DD-slug.html) so notes sort naturally on disk.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "site.config.json").read_text(encoding="utf-8"))
NOTES_DIR = ROOT / CONFIG.get("notes_dir", "notes")
UNLISTED_SUBDIR = CONFIG.get("unlisted_subdir", "unlisted")
TEMPLATE = ROOT / "templates" / "note.html"


def slugify(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", s.lower()).strip()
    return re.sub(r"[\s_]+", "-", s)[:80].strip("-") or "note"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("title")
    ap.add_argument("--slug")
    ap.add_argument("--category", default="")
    ap.add_argument("--tags", default="")
    ap.add_argument("--desc", default="")
    ap.add_argument("--unlisted", action="store_true", help="put in notes/unlisted/ and mark visibility=unlisted")
    ap.add_argument("--subdir", default="", help="sub-directory under notes/ (its name becomes the default category)")
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--no-date-prefix", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    slug = a.slug or slugify(a.title)
    fname = slug if slug.endswith(".html") else f"{slug}.html"
    if not a.no_date_prefix and not re.match(r"^\d{4}-\d{2}-\d{2}-", fname):
        fname = f"{a.date}-{fname}"

    parts = []
    if a.unlisted:
        parts.append(UNLISTED_SUBDIR)
    if a.subdir:
        parts.append(a.subdir.strip("/"))
    out_dir = NOTES_DIR.joinpath(*parts) if parts else NOTES_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / fname
    if out.exists() and not a.force:
        print(f"refusing to overwrite {out} (use --force)", file=sys.stderr)
        return 1

    depth = len(out.relative_to(ROOT).parts) - 1   # how many dirs deep below repo root
    css_rel = "../" * depth

    category = a.category or (a.subdir.split("/")[0].replace("_", " ").replace("-", " ").title() if a.subdir else "")
    repl = {
        "{{TITLE}}": html.escape(a.title),
        "{{DESCRIPTION}}": html.escape(a.desc),
        "{{CATEGORY}}": html.escape(category),
        "{{TAGS}}": html.escape(a.tags),
        "{{DATE}}": a.date,
        "{{VISIBILITY}}": "unlisted" if a.unlisted else "public",
        "{{CSS_REL}}": css_rel,
        "{{SITE_NAME}}": html.escape(CONFIG.get("site_name", "")),
    }
    text = TEMPLATE.read_text(encoding="utf-8")
    for k, v in repl.items():
        text = text.replace(k, v)
    if not category:  # let the hub auto-categorise: drop the empty tag so it doesn't override
        text = re.sub(r'\s*<meta name="category" content="">', "", text)
    out.write_text(text, encoding="utf-8")
    print(out.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
