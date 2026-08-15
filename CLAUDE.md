# cern-site — working notes for Claude

Static personal site deployed to CERN EOS (`lxplus:/eos/user/a/akallits/Post_Doc_Saclay/MyWebsite/`).
See README.md for layout. Key rules:

- `notes/index.html`, `notes/notes.json`, `notes/unlisted/index.html` and the `private_hub` file are
  **generated** by `scripts/build_hub.py` — never hand-edit; rebuild with `make hub`.
- New notes: `python3 scripts/new_note.py "Title" …` (or the `/publish-note` skill), then fill in the body.
- Notes must be self-contained (no CDNs); shared styling lives in `assets/site.css`.
- Deploy: `scripts/deploy.sh` (rsync, add/update only; `--delete` is opt-in and asks). Needs Kerberos or a password.
- The remote link to lxplus is slow (~15 kB/s at times) — run large uploads in the background.
- Treat the private hub URL and `notes/unlisted/` as unlisted, not secret.
