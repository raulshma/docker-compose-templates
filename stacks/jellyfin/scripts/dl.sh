#!/bin/bash
# Resumable manifest downloader.   Usage: dl.sh <manifest.tsv> [logfile]
# Manifest lines: <url><TAB><dest>
# - skips files already complete (content-length match)
# - validates mp4 magic (ftyp) after download
MANIFEST="$1"
LOG="${2:-${MANIFEST%.tsv}.log}"
total=$(wc -l < "$MANIFEST")
i=0; fail=0; skip=0
while IFS=$'\t' read -r url dest; do
  [ -z "$url" ] && continue
  dest="${dest%$'\r'}"
  url="${url%$'\r'}"
  i=$((i+1))
  mkdir -p "$(dirname "$dest")"
  expected=$(curl -sIL "$url" | tr -d '\r' | awk 'tolower($1)=="content-length:"{len=$2} END{print len}')
  if [ -n "$expected" ] && [ -f "$dest" ] && [ "$(stat -c%s "$dest" 2>/dev/null || echo 0)" = "$expected" ]; then
    echo "[$i/$total] skip (complete): $dest" >> "$LOG"
    skip=$((skip+1))
    continue
  fi
  echo "[$i/$total] $url" >> "$LOG"
  curl -sS -L --fail --retry 3 --retry-delay 5 -C - --output "$dest" "$url" >> "$LOG" 2>&1
  rc=$?
  if [ $rc -eq 33 ] && [ -s "$dest" ]; then
    echo "  already-complete" >> "$LOG"
    skip=$((skip+1))
  elif [ $rc -ne 0 ]; then
    echo "  FAILED rc=$rc" >> "$LOG"
    fail=$((fail+1))
  else
    if [ "${dest##*.}" = "mp4" ]; then
      magic=$(head -c 12 "$dest" | od -An -c | tr -d ' \n')
      case "$magic" in
        *f*t*y*p*) echo "  ok" >> "$LOG" ;;
        *) echo "  BAD-MP4-HEADER" >> "$LOG"; fail=$((fail+1)); continue ;;
      esac
    else
      echo "  ok" >> "$LOG"
    fi
  fi
done < "$MANIFEST"
echo "DONE manifest=$MANIFEST files=$total failures=$fail skipped=$skip" >> "$LOG"
echo "DONE files=$total failures=$fail skipped=$skip"
