# cern-site

Source for my CERN personal website (EOS-hosted at
`lxplus:/eos/user/a/akallits/Post_Doc_Saclay/MyWebsite/`). Static HTML only.

```
index.html              front page (personal / professional site)
assets/site.css         shared stylesheet (front page, hub, notes)
notes/                  every *.html here is a note; sub-folders become categories
notes/index.html        GENERATED public hub (do not edit)
notes/notes.json        GENERATED manifest (used by index.html "latest notes")
notes/unlisted/         notes deployed but hidden from the public hub
notes/hub-all-*.html    GENERATED private hub listing everything (keep the URL to yourself)
templates/note.html     scaffold used by scripts/new_note.py
scripts/build_hub.py    scans notes → hub + manifest (title, category, tags, dates)
scripts/new_note.py     scaffold a note
scripts/deploy.sh       build + rsync to lxplus
site.config.json        site name, deploy target, category keyword rules, private hub path
.claude/skills/publish-note   Claude Code skill: write → build → commit → deploy
```

## Everyday use

```bash
make note TITLE="Test-beam summary" ARGS='--desc "..." --tags "picosec,tb" --category Analysis'
#   → notes/2026-08-16-test-beam-summary.html   (edit it)
make hub          # regenerate hub/manifest, prints category+date per note
make serve        # preview at http://localhost:8000
git add -A && git commit -m "note: test-beam summary"
make deploy       # rsync to lxplus (needs kinit akallits@CERN.CH or password)
```

Or in Claude Code: `/publish-note Test-beam summary of the June PICOSEC run, --unlisted`.

## Metadata (all optional)

```html
<title>…</title>
<meta name="description" content="one line">
<meta name="category"    content="Detector R&D">        <!-- else: folder name → keyword rules -->
<meta name="keywords"    content="micromegas,fem">
<meta name="date"        content="2026-08-16">          <!-- else: git first commit → mtime -->
<meta name="updated"     content="2026-08-16">          <!-- else: git last commit → mtime -->
<meta name="visibility"  content="unlisted">            <!-- or put the file in notes/unlisted/ -->
```

Big exports (Plotly / JSROOT / notebook HTML) can be dropped into `notes/` untouched — the builder
reads only the first 200 kB for metadata and never modifies note files.

## Deploy details

`scripts/deploy.sh` rsyncs the tree minus tooling (`scripts/`, `templates/`, `.claude/`, `.git/`,
`Makefile`, `README.md`, `site.config.json`) with world-readable permissions. It **adds/updates only**;
`scripts/deploy.sh --delete` removes remote files that are not in the repo (asks first).
`--dry-run` shows what would change.
