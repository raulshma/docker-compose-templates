#!/usr/bin/env python3
"""Bootstrap a Jellyfin 10.11+/12 server: create the standard five libraries,
trigger a scan, wait for it, and report item counts.

Usage:
  python jellyfin_setup.py                       # admin/admin @ localhost:8096
  python jellyfin_setup.py -u admin -p secret
  python jellyfin_setup.py -b http://host:8096
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

LIBS = [
    ("Movies", "movies", "/media/movies"),
    ("Shows", "tvshows", "/media/shows"),
    ("Music", "music", "/media/music"),
    ("Music Videos", "musicvideos", "/media/musicvideos"),
    ("Books", "books", "/media/books"),
]


class JF:
    def __init__(self, base, user, password):
        self.base = base.rstrip("/")
        self.user = user
        self.password = password
        self.token = None

    def req(self, method, path, body=None):
        headers = {
            "Content-Type": "application/json",
            "Authorization": (
                'MediaBrowser Client="library-tools", Device="cli", '
                'DeviceId="library-tools-1", Version="1.0"'
            ),
        }
        if self.token:
            headers["Authorization"] += f', Token="{self.token}"'
        data = json.dumps(body).encode() if body is not None else (b"{}" if method == "POST" else None)
        r = urllib.request.Request(self.base + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(r, timeout=60) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raise SystemExit(f"{method} {path} -> HTTP {e.code}: {e.read().decode()[:300]}")

    def login(self):
        self.token = self.req("POST", "/Users/AuthenticateByName",
                              {"Username": self.user, "Pw": self.password})["AccessToken"]

    def ensure_libraries(self):
        existing = {f["Name"]: f.get("Locations", []) for f in self.req("GET", "/Library/VirtualFolders")}
        for name, ctype, path in LIBS:
            if name in existing and path in existing[name]:
                print(f"  ok  {name:14s} ({ctype}) {path}")
                continue
            qs = urllib.parse.urlencode({"name": name, "collectionType": ctype, "refreshLibrary": "true"})
            self.req("POST", f"/Library/VirtualFolders?{qs}",
                     {"LibraryOptions": {
                         "PathInfos": [{"Path": path}],
                         "EnableRealtimeMonitor": True,
                         "ExtractChapterImagesDuringLibraryScan": False,
                     }})
            print(f"  add {name:14s} ({ctype}) {path}")

    def scan_and_wait(self, timeout=900):
        """Trigger a scan and wait until ItemCount stops growing.

        Waiting on the ScheduledTasks state races the task registration, so
        poll /Items/Counts instead and require it stable for 3 checks.
        """
        self.req("POST", "/Library/Refresh")
        print("scan triggered; waiting for item count to settle...")
        last, stable = -1, 0
        deadline = time.time() + timeout
        while time.time() < deadline:
            n = self.req("GET", "/Items/Counts").get("ItemCount", 0)
            if n == last and n > 0:
                stable += 1
                if stable >= 3:
                    print(f"scan settled at {n} items")
                    return
            else:
                stable = 0
            last = n
            time.sleep(5)
        print("scan wait timed out (continuing anyway)", file=sys.stderr)

    def counts(self):
        c = self.req("GET", "/Items/Counts")
        return {k.replace("Count", ""): v for k, v in c.items() if k.endswith("Count")}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-u", "--user", default=os.environ.get("JELLYFIN_ADMIN_USER", "admin"))
    ap.add_argument("-p", "--password", default=os.environ.get("JELLYFIN_ADMIN_PASS"))
    ap.add_argument("-b", "--base", default=os.environ.get("JELLYFIN_URL", "http://localhost:8096"))
    args = ap.parse_args()
    if not args.password:
        ap.error("no password: use -p or set JELLYFIN_ADMIN_PASS in .env")

    jf = JF(args.base, args.user, args.password)
    jf.login()
    print("libraries:")
    jf.ensure_libraries()
    jf.scan_and_wait()
    print("counts:", json.dumps(jf.counts(), indent=1))


if __name__ == "__main__":
    main()
