# jellyfin (Docker Compose)

Self-hosted [Jellyfin](https://jellyfin.org) media server for testing: web UI,
REST API, and LAN/DLNA discovery, seeded with public-domain / Creative Commons
content from archive.org — not intended as a production media library. Ships with
a one-shot initializer that completes the first-run wizard automatically, so the
server is usable the moment `docker compose up` finishes.

## Setup

```bash
cd stacks/jellyfin
cp .env.example .env
# set JELLYFIN_ADMIN_PASS (optionally JELLYFIN_ADMIN_USER, MEDIA_DIR)

docker compose up -d
# open http://localhost:8096 and log in with the admin credentials
```

Compose refuses to start without `JELLYFIN_ADMIN_PASS` — the setup container would
otherwise seed a known default password.

## How it works

- **Media** lives in `./media` by default (one folder with subfolders per library
  type works well), or anywhere on the host via `MEDIA_DIR`.
- **`jellyfin-setup`** is a one-shot container that waits for the server to boot,
  completes the startup wizard, and creates the admin user. It exits when done and
  skips itself on later runs if the wizard was already completed (e.g. admin created
  manually in the UI). Re-run any time with `docker compose up jellyfin-setup`.
- **Config, metadata, and cache** live in named volumes (`jellyfin-config`,
  `jellyfin-cache`) and survive image upgrades.

## Media pipeline (host-side)

`scripts/` + `queue/` also carry a small archive.org → Jellyfin pipeline for
public-domain / CC content — the source of the test library. Bundled example
manifests cover movies, shows, music, music videos, and books.

```bash
# 1. optional: search archive.org and pick files
python scripts/archive_org.py search "night of the living dead"
python scripts/archive_org.py pick <identifier>

# 2. (re)generate download manifests into queue/
python scripts/build_manifest.py all

# 3. download — resumable, skips files already complete
./scripts/dl.sh queue/movies.tsv

# 4. create the five libraries and trigger a scan
python scripts/jellyfin_setup.py -p "$(sed -n 's/^JELLYFIN_ADMIN_PASS=//p' .env)"
```

- `build_manifest.py` writes into `MEDIA_DIR` (default `media`, the folder the
  compose stack mounts) and `QUEUE_DIR` (default `queue`); both overridable
  via environment variables.
- `dl.sh` skips completed downloads (content-length match), resumes partial
  ones, and validates mp4 headers; log lands next to the manifest.
- `jellyfin_setup.py` is idempotent: it only adds libraries that don't exist
  and waits for the scan item count to settle.
- `scripts/jellyfin-init.sh` is the container-side wizard completer used by
  the `jellyfin-setup` compose service — nothing to run by hand.

## Endpoints

| What              | URL                              |
|-------------------|----------------------------------|
| Web UI / REST API | `http://localhost:8096`          |
| Health probe      | `http://localhost:8096/health`   |

`GET /System/Info/Public` is unauthenticated and useful for scripting; everything
else needs an API key or user token.

## Optional: local plugin development

Set `PLUGINS_DIR` in `.env` to mount a folder to `/config/plugins`, drop a plugin
build output in it, and restart the container:

```bash
docker compose restart jellyfin
```
