#!/usr/bin/env python3
"""Helper to search archive.org and inspect item files.

Usage:
  python archive_org.py search "night of the living dead"        # advancedsearch, top results
  python archive_org.py item <identifier>                        # file list for one item
  python archive_org.py pick <identifier> [max_mb] [min_mb]      # best single movie file in item
"""
import json
import sys
import urllib.request
import urllib.parse

UA = {"User-Agent": "Mozilla/5.0 (library-builder; personal use)"}


def get_json(url: str):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def human(n):
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


def search(query: str, rows: int = 8):
    q = urllib.parse.quote(query)
    url = (
        "https://archive.org/advancedsearch.php?q=" + q
        + f"&fl%5B%5D=identifier&fl%5B%5D=title&fl%5B%5D=size&fl%5B%5D=downloads"
        + f"&fl%5B%5D=mediatype&sort%5B%5D=downloads+desc&rows={rows}&page=1&output=json"
    )
    data = get_json(url)
    for d in data.get("response", {}).get("docs", []):
        size = d.get("size")
        size_s = human(size) if size else "-"  # search index often has no size; check via `item`
        print(f"{d.get('identifier','?'):45s} {size_s:>10s} "
              f"dl={d.get('downloads',0):>10,d} [{d.get('mediatype','?')}] {d.get('title','?')[:60]}")


def item(identifier: str):
    data = get_json(f"https://archive.org/metadata/{urllib.parse.quote(identifier)}")
    md = data.get("metadata", {})
    print(f"== {identifier} | {md.get('title','?')} | licenseurl={md.get('licenseurl','-')}")
    files = data.get("files", [])
    total = 0
    for f in files:
        name = f.get("name", "")
        size = int(f.get("size") or 0)
        total += size
        fmt = f.get("format", f.get("extension", "?"))
        # only show av-ish formats to keep output readable
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext in ("mp4", "mkv", "avi", "mpg", "mpeg", "ogv", "webm", "mp3", "flac", "ogg", "epub", "pdf"):
            print(f"  {human(size):>10s}  [{fmt}]  {name}")
    print(f"  TOTAL item size: {human(total)}  ({len(files)} files)")


def pick(identifier: str, max_mb: int = 3000, min_mb: int = 100):
    data = get_json(f"https://archive.org/metadata/{urllib.parse.quote(identifier)}")
    md = data.get("metadata", {})
    print(f"== {identifier} | {md.get('title','?')}")
    best = []
    for f in data.get("files", []):
        name = f.get("name", "")
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext not in ("mp4", "mkv", "ogv", "avi", "mpeg", "mpg"):
            continue
        size_mb = int(f.get("size") or 0) / 1e6
        if min_mb <= size_mb <= max_mb:
            best.append((size_mb, f.get("format", "?"), name))
    best.sort(reverse=True)
    for size_mb, fmt, name in best[:5]:
        print(f"  {size_mb:8.0f}MB [{fmt}] {name}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "search":
        search(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 8)
    elif cmd == "item":
        item(sys.argv[2])
    elif cmd == "pick":
        pick(sys.argv[2], *(int(x) for x in sys.argv[3:]))
    else:
        print(__doc__)
