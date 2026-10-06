#!/bin/sh
# First-boot Jellyfin initializer: completes the startup wizard so the server
# is reachable with the credentials defined here. Skips itself if the wizard
# was already completed (or credentials were set manually in the UI).
# Every step retries: the API answers 503 until the server finishes booting.
# Jellyfin 12 seeds a placeholder user ("root"); POST /Startup/User only works
# after GET /Startup/FirstUser, and Complete must never run if User failed
# (otherwise the wizard locks with no admin account).
set -u
BASE="http://jellyfin:8096"
USER_NAME="${JELLYFIN_ADMIN_USER:-admin}"
USER_PASS="${JELLYFIN_ADMIN_PASS:-admin}"

echo "waiting for jellyfin to come up..."
i=0
until curl -sf "$BASE/System/Info/Public" >/dev/null 2>&1; do
  i=$((i + 1))
  if [ "$i" -gt 120 ]; then
    echo "jellyfin did not come up in time" >&2
    exit 1
  fi
  sleep 2
done

if curl -sf "$BASE/System/Info/Public" | grep -q '"StartupWizardCompleted":true'; then
  echo "startup already completed; nothing to do"
  exit 0
fi

# post <path> <json-body> — retry up to ~4 min until a 2xx comes back
post() {
  path="$1"; body="$2"
  i=0
  while [ "$i" -lt 120 ]; do
    code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE$path" \
      -H "Content-Type: application/json" -d "$body")
    case "$code" in
      2*) echo "  POST $path -> $code"; return 0 ;;
    esac
    i=$((i + 1))
    sleep 2
  done
  echo "  POST $path kept failing (last code $code)" >&2
  return 1
}

post /Startup/Configuration '{"UICulture":"en-US","MetadataCountryCode":"us","PreferredMetadataLanguage":"en"}' || exit 1

# initialize the seeded first-user state (required before /Startup/User)
i=0
until curl -sf "$BASE/Startup/FirstUser" >/dev/null 2>&1; do
  i=$((i + 1))
  [ "$i" -gt 60 ] && { echo "FirstUser GET kept failing" >&2; exit 1; }
  sleep 2
done
echo "  GET /Startup/FirstUser ok"

# if the first user is already our admin (previous partial run), skip creation
if curl -sf "$BASE/Startup/FirstUser" | grep -q "\"Name\":\"$USER_NAME\""; then
  echo "  user '$USER_NAME' already present; skipping creation"
else
  post /Startup/User "{\"Name\":\"$USER_NAME\",\"Password\":\"$USER_PASS\"}" || exit 1
fi
post /Startup/RemoteAccess '{"EnableRemoteAccess":true,"EnablePortMapping":false}' || exit 1
post /Startup/Complete '{}' || exit 1

echo "done: user '$USER_NAME' created (wizard complete)"
