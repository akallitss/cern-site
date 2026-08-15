.PHONY: hub note deploy dry-run serve clean

# Rebuild notes/index.html, notes/notes.json and the private hub
hub:
	python3 scripts/build_hub.py

# make note TITLE="My note" [ARGS="--category Analysis --tags a,b --unlisted"]
note:
	python3 scripts/new_note.py "$(TITLE)" $(ARGS)

# Build + rsync to lxplus (never deletes remote files; use scripts/deploy.sh --delete for that)
deploy:
	scripts/deploy.sh

dry-run:
	scripts/deploy.sh --dry-run

# Preview locally at http://localhost:8000
serve: hub
	python3 -m http.server 8000

clean:
	rm -f notes/notes.json
	find . -name __pycache__ -type d -exec rm -rf {} +
