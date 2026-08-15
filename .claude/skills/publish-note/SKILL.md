---
name: publish-note
description: Write an HTML note for the CERN personal site (notes/), register it in the auto-generated hub, commit, and deploy to lxplus. Use whenever the user asks to "publish", "write up", "put on my site", "make a note/page about", or "add to the hub" — including unlisted/private pages.
---

# publish-note

Turn content (a write-up, meeting minutes, analysis summary, how-to, personal page…) into a
self-contained HTML note under `notes/`, rebuild the hub, commit, and deploy to
`lxplus:/eos/user/a/akallits/Post_Doc_Saclay/MyWebsite/`.

Arguments (`$ARGUMENTS`) may contain: a title / topic / source file to write up, and flags
`--unlisted`, `--category "X"`, `--tags a,b`, `--subdir dir`, `--no-deploy`, `--no-commit`.
Ask nothing you can infer; the only real questions are *what should the note say* and
*public or unlisted* (default public unless the content is obviously personal).

## 1. Scaffold

```bash
python3 scripts/new_note.py "Title" --desc "one-line summary" --tags "tag1,tag2" [--category "Detector R&D"] [--unlisted] [--subdir talks]
```

- Prints the created path, e.g. `notes/2026-08-16-title.html` (or `notes/unlisted/…` with `--unlisted`).
- Omit `--category` to let the hub auto-categorise from keywords in `site.config.json`
  (Detector R&D · Analysis · Software · Talks & Papers · Meetings · How-to · Personal · Miscellaneous).
  Pass it explicitly when the topic is clear — explicit beats heuristics.
- `--subdir X` makes the folder name the default category (e.g. `notes/talks/…` → "Talks").
- Never write directly to `notes/index.html`, `notes/notes.json`, or the private hub file — they are generated.

## 2. Write the content

Edit the scaffolded file. Rules:

- Keep the `<meta>` block at the top of `<head>` intact — the hub reads `title`, `description`,
  `category`, `keywords`, `date`, `updated`, `visibility`. Update `updated` when you edit an existing note.
- Fill `<h1>`, the summary `<p class="muted">`, and replace the placeholder inside `<div class="note-body">`.
- Plain semantic HTML; the shared stylesheet `assets/site.css` already styles headings, tables, code,
  `<figure>`, `<details>`, `.callout` / `.callout.warn` / `.callout.ok`, `.pill`, `.card`, `.grid`.
- Self-contained: no CDN scripts/fonts. Images: put files next to the note in `notes/<slug>_files/`
  (or embed small ones as data URIs); plots as inline SVG are ideal. Big HTML exports (Plotly, ROOT
  JSROOT, notebooks) can just be dropped into `notes/` as-is — the hub will still index them
  (title from `<title>`, date from git). Optionally prepend the meta block to them.
- Long tables/wide content: wrap in a scrolling container (`<div style="overflow-x:auto">`).
- Math: keep it light (Unicode / `<sup>`/`<sub>`); no MathJax from CDN.
- If the note is personal/private, make sure `visibility` is `unlisted` **and** it lives under
  `notes/unlisted/`. Unlisted notes are deployed but excluded from `notes/index.html`; they appear
  only in the private hub (`private_hub` in `site.config.json`) — treat that URL as a secret.

## 3. Build, check, commit, deploy

```bash
python3 scripts/build_hub.py            # regenerates hub + manifest; prints category/date per note
```

Sanity-check the printed line for the new note (category, date, listed/unlisted). If the category
guess is wrong, set `<meta name="category">` explicitly and rebuild.

Optional local preview: `make serve` → http://localhost:8000/notes/

```bash
git add -A && git commit -m "note: <title>"    # skip if --no-commit
scripts/deploy.sh                              # skip if --no-deploy; use --dry-run first if unsure
```

`deploy.sh` rsyncs the tree (minus repo tooling) to lxplus. It needs a valid Kerberos ticket
(`kinit akallits@CERN.CH`) or a password prompt. It never deletes remote files unless `--delete`.

If `git push` is wanted, push to `origin main` afterwards — but the deploy to EOS is what makes the
note live; GitHub is only the backup/organizer.

## 4. Report

Reply with: the note path, its category/date as printed by the build, the public URL
(`<site_url>/notes/<file>`) and whether it is listed or unlisted, and whether it was deployed.
