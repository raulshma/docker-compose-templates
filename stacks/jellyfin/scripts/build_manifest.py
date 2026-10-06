#!/usr/bin/env python3
"""Build download manifests (url<TAB>dest) for the Jellyfin library from archive.org."""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

MEDIA = Path(os.environ.get("MEDIA_DIR", "media"))
QUEUE = Path(os.environ.get("QUEUE_DIR", "queue"))
QUEUE.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (library-builder; personal use)"}
def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


_cache = {}


def meta(identifier):
    if identifier not in _cache:
        url = f"https://archive.org/metadata/{urllib.parse.quote(identifier)}"
        req = urllib.request.Request(url, headers=UA)
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    _cache[identifier] = json.loads(r.read().decode("utf-8", "replace"))
                break
            except Exception as e:
                if attempt == 2:
                    raise
                time.sleep(5)
        time.sleep(0.4)
    return _cache[identifier]


def files_of(identifier):
    return meta(identifier).get("files", [])


def dl_url(identifier, name):
    return "https://archive.org/download/" + urllib.parse.quote(identifier) + "/" + urllib.parse.quote(name)


def write_manifest(name, rows):
    p = QUEUE / f"{name}.tsv"
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        for url, dest in rows:
            f.write(f"{url}\t{dest}\n")
    print(f"[{name}] {len(rows)} files -> {p}")


def pick_movie_file(identifier, max_mb=3500, min_mb=150):
    """Prefer h.264 mp4; return (name, size_mb)."""
    cands = []
    for f in files_of(identifier):
        n = f.get("name", "")
        ext = n.rsplit(".", 1)[-1].lower() if "." in n else ""
        if ext not in ("mp4", "mkv"):
            continue
        mb = int(f.get("size") or 0) / 1e6
        if min_mb <= mb <= max_mb:
            cands.append((mb, n))
    if not cands:
        return None
    cands.sort(reverse=True)
    # among near-equal sizes, plain .mp4 over derivative suffixes
    return cands[0][1], cands[0][0]


MOVIES = [
    ("Night.Of.The.Living.Dead_1080p", "NightOfTheLivingDead_720p.mp4", "Night of the Living Dead", 1968),
    ("his_girl_friday", "his_girl_friday.mp4", "His Girl Friday", 1940),
    ("charade-1963-cary-grant-audrey-hepburn-comedy-mystery-romance-thriller-full-movie", "Charade_READY.mp4", "Charade", 1963),
    ("Nosferatu_most_complete_version_93_mins.", "Nosferatu_1922_Symphony_of_Horror_512kb.mp4", "Nosferatu", 1922),
    ("mclintok_widescreen", "McLintock.mp4", "McLintock!", 1963),
    ("Detour", "Detour.mp4", "Detour", 1945),
    ("CarnivalofSouls", "CarnivalOfSouls.mp4", "Carnival of Souls", 1962),
    ("ThePhantomoftheOpera", "Phantom_of_the_Opera_512kb.mp4", "The Phantom of the Opera", 1925),
    ("DasKabinettdesDoktorCaligariTheCabinetofDrCaligari", "The_Cabinet_of_Dr._Caligari_512kb.mp4", "The Cabinet of Dr. Caligari", 1920),
    ("meet_john_doe", "meet_john_doe.mp4", "Meet John Doe", 1941),
    ("TheGeneral_201312", "The-General-v2.mp4", "The General", 1926),
    ("SteamboatBillJr", "Steamboat_Bill.Jr_512kb.mp4", "Steamboat Bill, Jr.", 1928),
    ("Metropolis1927EnglishVersion", "Metropolis_1927_English_Version.mp4", "Metropolis", 1927),
]


def build_movies():
    rows = []
    for ident, fname, title, year in MOVIES:
        found = pick_movie_file(ident)
        if found is None:
            print(f"!! no usable mp4 in {ident}", file=sys.stderr)
            continue
        name, mb = found
        if fname and name != fname:
            # stick to verified file unless missing
            names = {f.get("name") for f in files_of(ident)}
            if fname in names:
                name = fname
        dest = MEDIA / "movies" / f"{title} ({year})" / f"{title} ({year}).mp4"
        rows.append((dl_url(ident, name), dest))
        print(f"  {title} ({year}): {name} ~{mb:.0f}MB")
    write_manifest("movies", rows)


SUPERMAN = [  # episode -> candidate identifiers, first with a usable mp4 wins
    (("superman_1941",), "Superman"),
    (("superman_the_mechanical_monsters",), "The Mechanical Monsters"),
    (("superman_billion_dollar_limited",), "Billion Dollar Limited"),
    (("superman_arctic_giant", "superman_the_arctic_giant"), "The Arctic Giant"),
    (("superman_bulleteers", "superman_the_bulleteers"), "The Bulleteers"),
    (("Superman_The_Magnetic_Telescope", "superman_the_magnetic_telescope"), "The Magnetic Telescope"),
    (("superman_electric_earthquake",), "Electric Earthquake"),
    (("superman_volcano",), "Volcano"),
    (("superman_terror_on_the_midway",), "Terror on the Midway"),
    (("dom-6741japoteurssupermanepisode1", "superman_japoteurs"), "Japoteurs"),
    (("dom-6744showdownsupermanepisode2", "SupermanShowdown1942"), "Showdown"),
    (("superman_eleventh_hour",), "Eleventh Hour"),
    (("superman_destruction_inc",), "Destruction, Inc."),
    (("dom-6731mummystrikesnew", "superman-the-mummy-strikes-public-domain"), "The Mummy Strikes"),
    (("superman_jungle_drums",), "Jungle Drums"),
    (("superman_underground_world", "superman_the_underground_world"), "The Underground World"),
    (("dom-6743secretagentsupermanepisode8",), "Secret Agent"),
]


def build_shows():
    rows = []
    # --- The Adventures of Sherlock Holmes (1954), 39 episodes
    show = "The Adventures of Sherlock Holmes (1954)"
    pat = re.compile(r"^Sherlock Holmes (\d{1,2}) (.+)\.mp4$", re.I)
    eps = []
    for f in files_of("SherlockHolmes1954"):
        m = pat.match(f.get("name", ""))
        if m:
            eps.append((int(m.group(1)), m.group(2).strip(), f.get("name"), int(f.get("size") or 0)))
    eps.sort()
    for num, title, name, _ in eps:
        dest = MEDIA / "shows" / show / "Season 01" / f"The Adventures of Sherlock Holmes S01E{num:02d} - {title}.mp4"
        rows.append((dl_url("SherlockHolmes1954", name), dest))
    print(f"  Sherlock Holmes 1954: {len(eps)} episodes")
    # --- Superman (1941-1943) cartoons
    sm_show = "Superman (1941)"
    ok = 0
    for i, (idents, title) in enumerate(SUPERMAN, start=1):
        done = False
        for ident in idents:
            try:
                best = None
                for f in files_of(ident):
                    n = f.get("name", "")
                    if n.lower().endswith(".mp4"):
                        mb = int(f.get("size") or 0) / 1e6
                        if 3 <= mb <= 300:
                            score = (0 if "512kb" in n else 1, mb)
                            if best is None or score > best[0]:
                                best = (score, n, mb)
                if best:
                    dest = MEDIA / "shows" / sm_show / "Season 01" / f"Superman (1941) S01E{i:02d} - {title}.mp4"
                    rows.append((dl_url(ident, best[1]), dest))
                    ok += 1
                    done = True
                    break
            except Exception as e:
                print(f"!! superman lookup failed: {ident}: {e}", file=sys.stderr)
        if not done:
            print(f"!! superman ep unavailable: {title} ({idents})", file=sys.stderr)
    print(f"  Superman: {ok}/17 episodes")
    write_manifest("shows", rows)


SOUNDIES = [  # identifier, artist, song
    ("SoundieF", "Reg Kehoe and His Marimba Queens", "A Study in Brown"),
    ("soundie_1", "Soundies (1940s)", "The Hut Sut Song"),
    ("WhosYourHoot", "Soundies (1940s)", "Who's Yehudi?"),
    ("SoundieJ", "Soundies (1940s)", "Stardust"),
    ("SoundieO", "Soundies (1940s)", "I Can't Give You Anything but Love"),
    ("SoundieH", "Soundies (1940s)", "Beyond the Blue Horizon"),
    ("soundie_12", "Soundies (1940s)", "Hollywood Boogie"),
    ("SoundieB", "Soundies (1940s)", "Sweet Sue (Just You)"),
    ("SoundieL", "Soundies (1940s)", "Lullaby of Broadway"),
    ("soundie_10", "Soundies (1940s)", "A Jazz Etude"),
    ("0838_Musical_Review_11_Louis_Armstrong_Soundie_11_33_03_18", "Louis Armstrong", "Musical Review #11 (Soundie)"),
]


def build_musicvideos():
    rows = []
    ok = 0
    for ident, artist, song in SOUNDIES:
        try:
            best = None
            for f in files_of(ident):
                n = f.get("name", "")
                if n.lower().endswith(".mp4"):
                    mb = int(f.get("size") or 0) / 1e6
                    if 5 <= mb <= 200:
                        score = (2 if n.lower().endswith("_edit.mp4") else (1 if "512kb" not in n.lower() else 0), mb)
                        if best is None or score > best[0]:
                            best = (score, n, mb)
            if best:
                safe_song = re.sub(r'[<>:"/\\|?*]', "_", song)
                safe_artist = re.sub(r'[<>:"/\\|?*]', "_", artist)
                # one folder per song: Jellyfin groups same-folder videos into a
                # single item with multiple "versions"
                dest = MEDIA / "musicvideos" / safe_artist / safe_song / f"{safe_song}.mp4"
                rows.append((dl_url(ident, best[1]), dest))
                ok += 1
            else:
                print(f"!! soundie missing mp4: {ident}", file=sys.stderr)
        except Exception as e:
            print(f"!! soundie lookup failed: {ident}: {e}", file=sys.stderr)
    print(f"  Soundies: {ok}/{len(SOUNDIES)} videos")
    write_manifest("musicvideos", rows)


def build_music():
    rows = []
    # --- Kimiko Ishizaka - The Open Goldberg Variations (CC0)
    artist = "Kimiko Ishizaka"
    album = "The Open Goldberg Variations"
    for f in files_of("The_Open_Goldberg_Variations-11823"):
        n = f.get("name", "")
        if n.lower().endswith(".mp3"):
            track = re.sub(r"^Kimiko_Ishizaka_-_\d+_-_", "", n).replace(".mp3", "").replace("_", " ")
            num = re.search(r"^Kimiko_Ishizaka_-_(\d+)_-_", n)
            pref = f"{int(num.group(1)):02d} - " if num else ""
            dest = MEDIA / "music" / artist / album / f"{pref}{track}.mp3"
            rows.append((dl_url("The_Open_Goldberg_Variations-11823", n), dest))
    # --- Kimiko Ishizaka - Bach: Well-Tempered Clavier Book 1 (CC0)
    album = "Bach - Well-Tempered Clavier, Book 1"
    count = 0
    for f in files_of("bach-well-tempered-clavier-book-1"):
        n = f.get("name", "")
        if n.lower().endswith(".mp3"):
            m = re.match(r"^Kimiko Ishizaka - Bach- Well-Tempered Clavier, Book 1 - (\d{1,2}) (.+)\.mp3$", n)
            if m:
                dest = MEDIA / "music" / artist / album / f"{int(m.group(1)):02d} - {m.group(2)}.mp3"
            else:
                dest = MEDIA / "music" / artist / album / n
            rows.append((dl_url("bach-well-tempered-clavier-book-1", n), dest))
            count += 1
    print(f"  Open Goldberg + WTC1: {count + 32} tracks")
    # --- Musopen Chopin: selected works, cap ~140 mp3s
    artist = "Frederic Chopin"
    album = "The Complete Chopin Collection (Musopen)"
    cats = ["Nocturne", "Prelude", "Etude", "Waltz", "Mazurka", "Polonaise",
            "Sonata", "Scherzo", "Ballade", "Impromptu", "Barcarolle", "Fantaisie", "Rondo", "Concerto"]
    chosen = []
    for cat in cats:
        n_cat = 0
        for f in files_of("musopen-chopin"):
            n = f.get("name", "")
            if n.lower().endswith(".mp3") and cat.lower() in n.lower() and n not in [c[1] for c in chosen]:
                chosen.append((f, n))
                n_cat += 1
                if n_cat >= 10:
                    break
    for f, n in chosen:
        title = n.replace(".mp3", "").replace("_", " ").strip()
        dest = MEDIA / "music" / artist / album / f"{title}.mp3"
        rows.append((dl_url("musopen-chopin", n), dest))
    print(f"  Chopin: {len(chosen)} tracks")
    write_manifest("music", rows)


BOOKS = [  # gutenberg number, title, author
    (1342, "Pride and Prejudice", "Jane Austen"),
    (84, "Frankenstein", "Mary Shelley"),
    (345, "Dracula", "Bram Stoker"),
    (11, "Alice's Adventures in Wonderland", "Lewis Carroll"),
    (2701, "Moby Dick", "Herman Melville"),
    (35, "The Time Machine", "H. G. Wells"),
    (76, "Adventures of Huckleberry Finn", "Mark Twain"),
    (120, "Treasure Island", "Robert Louis Stevenson"),
    (1661, "The Adventures of Sherlock Holmes", "Arthur Conan Doyle"),
    (64317, "The Great Gatsby", "F. Scott Fitzgerald"),
    (174, "The Picture of Dorian Gray", "Oscar Wilde"),
    (43, "The Strange Case of Dr. Jekyll and Mr. Hyde", "Robert Louis Stevenson"),
    (16, "Peter Pan", "J. M. Barrie"),
    (5200, "Metamorphosis", "Franz Kafka"),
]


def build_books():
    rows = []
    ok = 0
    for num, title, author in BOOKS:
        safe = re.sub(r'[<>:"/\\|?*]', "_", title)
        dest = MEDIA / "books" / f"{safe} - {author}.epub"
        chosen = None  # (url, note)
        # 1) direct gutenberg_<num> item
        candidates = [f"gutenberg_{num}"]
        # 2) search gutenberg collection for items carrying this pg number
        try:
            q = urllib.parse.quote(f'collection:gutenberg AND mediatype:texts AND ("{title}")')
            url = ("https://archive.org/advancedsearch.php?q=" + q
                   + "&fl%5B%5D=identifier&rows=20&output=json")
            for d in get_json(url).get("response", {}).get("docs", []):
                ident = d.get("identifier", "")
                m = re.search(r"(\d+)gut$", ident)
                if m and int(m.group(1)) == num:
                    candidates.append(ident)
        except Exception as e:
            print(f"!! search failed for pg{num}: {e}", file=sys.stderr)
        for ident in candidates:
            try:
                epubs = [f for f in files_of(ident) if f.get("name", "").lower().endswith(".epub")]
                if epubs:
                    epubs.sort(key=lambda f: int(f.get("size") or 0), reverse=True)
                    chosen = (dl_url(ident, epubs[0]["name"]), f"archive.org:{ident}")
                    break
            except Exception:
                continue
        # 3) gutenberg.org fallback (same public-domain text)
        if chosen is None:
            chosen = (f"https://www.gutenberg.org/ebooks/{num}.epub3.images", "gutenberg.org")
        url, note = chosen
        rows.append((url, dest))
        ok += 1
        print(f"  pg{num} {title}: {note}")
    write_manifest("books", rows)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("movies", "all"):
        build_movies()
    if which in ("shows", "all"):
        build_shows()
    if which in ("musicvideos", "all"):
        build_musicvideos()
    if which in ("music", "all"):
        build_music()
    if which in ("books", "all"):
        build_books()
