# cern-site — working notes for Claude

Static personal site at https://alexandra-kallitsopoulou.web.cern.ch/, deployed to CERN EOS (`lxplus:/eos/user/a/akallits/Post_Doc_Saclay/MyWebsite/`).
See README.md for layout. Key rules:

- `notes/index.html`, `notes/notes.json`, `notes/unlisted/index.html` and the `private_hub` file are
  **generated** by `scripts/build_hub.py` — never hand-edit; rebuild with `make hub`.
- New notes: `python3 scripts/new_note.py "Title" …` (or the `/publish-note` skill), then fill in the body.
- Notes must be self-contained (no CDNs); shared styling lives in `assets/site.css`.
- Deploy: `scripts/deploy.sh` (rsync, add/update only; `--delete` is opt-in and asks). Needs Kerberos or a password.
- The remote link to lxplus is slow (~15 kB/s at times) — run large uploads in the background.
- `notes/unlisted/` is behind CERN SSO (owner only) via `notes/unlisted/.htaccess`; its `index.html` is the private hub.
  Private notes must live physically in that folder — a `visibility=unlisted` tag elsewhere only hides, never protects.
- Adding a note = drop/scaffold an HTML file under `notes/` → `make hub` → commit → `scripts/deploy.sh` → `git push`.
