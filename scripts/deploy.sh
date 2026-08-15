#!/usr/bin/env bash
# deploy.sh — rebuild the hub and rsync the site to the CERN EOS web folder.
#
#   scripts/deploy.sh            # build + sync (adds/updates only, never deletes remote files)
#   scripts/deploy.sh --dry-run  # show what would change
#   scripts/deploy.sh --delete   # also delete remote files that are not in the repo (asks first)
#
# Host/path come from site.config.json → deploy.host / deploy.path.
# Needs a working `ssh <host>` (Kerberos ticket via `kinit akallits@CERN.CH`, or password).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

HOST=$(python3 -c 'import json;print(json.load(open("site.config.json"))["deploy"]["host"])')
DEST=$(python3 -c 'import json;print(json.load(open("site.config.json"))["deploy"]["path"])')

DRY=""; DELETE=""
for arg in "$@"; do
  case "$arg" in
    --dry-run|-n) DRY="--dry-run" ;;
    --delete)     DELETE="--delete" ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

echo "▸ building hub"
python3 scripts/build_hub.py

if [[ -n "$DELETE" && -z "$DRY" ]]; then
  read -r -p "This will DELETE remote files not present in the repo. Continue? [y/N] " ans
  [[ "$ans" == [yY] ]] || { echo "aborted"; exit 1; }
fi

echo "▸ syncing to $HOST:$DEST"
# -r recursive, -l links, -t times, -z compress, --chmod: world-readable files/dirs (web server needs it)
rsync -rltvz $DRY $DELETE \
  --chmod=Du=rwx,Dgo=rx,Fu=rw,Fgo=r \
  --exclude '.git/' --exclude '.gitignore' --exclude '.claude/' \
  --exclude 'scripts/' --exclude 'templates/' --exclude 'Makefile' \
  --exclude 'README.md' --exclude 'CLAUDE.md' --exclude 'site.config.json' \
  --exclude '__pycache__/' --exclude '.DS_Store' \
  ./ "$HOST:$DEST"

SITE=$(python3 -c 'import json;print(json.load(open("site.config.json")).get("site_url",""))')
[[ -n "$DRY" ]] && echo "▸ dry run — nothing uploaded" || echo "▸ done → $SITE"
