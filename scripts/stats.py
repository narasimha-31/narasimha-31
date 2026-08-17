#!/usr/bin/env python3
"""Generate the four activity SVGs at the repo root from the GitHub API.

    python scripts/stats.py

Writes stats.svg, langs.svg, streak.svg and year.svg. Public repositories
only, no third-party image service anywhere in the chain.

Two collectors feed one data model. With GH_STATS_TOKEN set the GraphQL API
is used, which is what the scheduled Action runs. Without a token it falls
back to public endpoints, so a fresh clone can regenerate every file and the
README never ends up pointing at an SVG that does not exist yet.

The token should carry read:user and nothing else. A token without repo scope
cannot see private contributions, which is what makes "public only" true by
construction rather than by filtering after the fact.

Output is deterministic: no timestamps, no generation dates, sorted iteration
throughout. Identical data produces byte-identical files, so the workflow's
change check does not manufacture no-op commits.
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).parent))

import palette
from fontkit import FaceSet, advance

ROOT = Path(__file__).parent.parent
LOGIN = "narasimha-31"
UA = "narasimha-31-profile-stats"

CARD_W = 880           # full width; the README stacks these rather than pairing them
RAMP = ":+#@"          # quiet to loud, one character per day
TOP_LANGS = 6

ANIM_DUR = 0.5
ANIM_STAGGER = 0.07


# --------------------------------------------------------------------------
# Data model
# --------------------------------------------------------------------------

@dataclass
class Day:
    day: date
    count: int


@dataclass
class Stats:
    total_contributions: int = 0
    commits: int = 0
    prs: int = 0
    issues: int = 0
    days: list = field(default_factory=list)          # last 365, chronological
    langs_bytes: list = field(default_factory=list)   # [(name, bytes)]
    langs_repos: list = field(default_factory=list)   # [(name, repo count)]
    current_streak: int = 0
    current_span: tuple = None
    longest_streak: int = 0
    longest_span: tuple = None
    source: str = ""


def _get(url, headers=None, timeout=60, attempts=5):
    """GET with backoff on rate limiting.

    Unauthenticated search allows only ~10 requests a minute, and a full public
    collection runs well over twenty calls. Retry rather than return a default:
    a swallowed 403 here silently renders a card reading zero, which looks like
    a real number and is worse than a crash.
    """
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            retryable = exc.code in (403, 429, 502, 503)
            if not retryable or attempt == attempts - 1:
                raise
            wait = exc.headers.get("Retry-After")
            if wait is None and exc.headers.get("X-RateLimit-Remaining") == "0":
                reset = int(exc.headers.get("X-RateLimit-Reset", 0))
                wait = max(0, reset - int(time.time())) + 1
            delay = min(float(wait or 2 ** (attempt + 1)), 90)
            print(f"    rate limited ({exc.code}), waiting {delay:.0f}s")
            time.sleep(delay)
    raise SystemExit(f"giving up on {url}")


# --------------------------------------------------------------------------
# Streaks
# --------------------------------------------------------------------------

def compute_streaks(days):
    """Longest run of consecutive active days, and the run ending today.

    Dates come from GitHub already bucketed in the profile's own timezone, so
    they are compared as plain dates with no further conversion.
    """
    if not days:
        return 0, None, 0, None

    longest, longest_span = 0, None
    run, run_start = 0, None
    for entry in days:
        if entry.count > 0:
            if run == 0:
                run_start = entry.day
            run += 1
            if run > longest:
                longest, longest_span = run, (run_start, entry.day)
        else:
            run = 0

    # Walk back from the end. An idle today does not break the streak -- the day
    # may simply not have started yet in the profile's timezone -- but an idle
    # yesterday does.
    idx = len(days) - 1
    if days[idx].count == 0:
        idx -= 1

    current, end = 0, None
    while idx >= 0 and days[idx].count > 0:
        end = end or days[idx].day
        current += 1
        idx -= 1

    current_span = (days[idx + 1].day, end) if current else None
    return current, current_span, longest, longest_span


# --------------------------------------------------------------------------
# Collector: GraphQL (used by the scheduled Action)
# --------------------------------------------------------------------------

GRAPHQL = """
query($login:String!, $from:DateTime!, $to:DateTime!) {
  user(login:$login) {
    contributionsCollection(from:$from, to:$to) {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""

GRAPHQL_REPOS = """
query($login:String!, $cursor:String) {
  user(login:$login) {
    repositories(first:100, after:$cursor, ownerAffiliations:OWNER,
                 privacy:PUBLIC, isFork:false) {
      pageInfo { hasNextPage endCursor }
      nodes {
        languages(first:20, orderBy:{field:SIZE, direction:DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}
"""


def _graphql(query, variables, token):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": UA,
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if "errors" in payload:
        raise SystemExit("GraphQL error: " + json.dumps(payload["errors"], indent=2))
    return payload["data"]


def _window(token, start, end):
    return _graphql(
        GRAPHQL,
        {
            "login": LOGIN,
            "from": start.isoformat() + "T00:00:00Z",
            "to": end.isoformat() + "T23:59:59Z",
        },
        token,
    )["user"]["contributionsCollection"]


def collect_graphql(token):
    stats = Stats(source="graphql")
    today = datetime.now(timezone.utc).date()

    recent = _window(token, today - timedelta(days=364), today)
    stats.total_contributions = recent["contributionCalendar"]["totalContributions"]
    stats.days = [
        Day(date.fromisoformat(d["date"]), d["contributionCount"])
        for week in recent["contributionCalendar"]["weeks"]
        for d in week["contributionDays"]
    ]
    stats.days.sort(key=lambda d: d.day)

    # contributionsCollection caps at one year per call, so the longest streak
    # needs one call per calendar year the account has existed.
    created = _account_created()
    history = []
    for year in range(created.year, today.year + 1):
        start = max(date(year, 1, 1), created)
        end = min(date(year, 12, 31), today)
        if start > end:
            continue
        window = _window(token, start, end)
        # Accumulate here rather than reading the last-365 window, so the
        # commit/PR/issue tiles are all-time and match what the public
        # collector's search totals report under the same label.
        stats.commits += window["totalCommitContributions"]
        stats.prs += window["totalPullRequestContributions"]
        stats.issues += window["totalIssueContributions"]
        cal = window["contributionCalendar"]
        history += [
            Day(date.fromisoformat(d["date"]), d["contributionCount"])
            for week in cal["weeks"]
            for d in week["contributionDays"]
        ]
    history = sorted({d.day: d for d in history}.values(), key=lambda d: d.day)
    stats.current_streak, stats.current_span, stats.longest_streak, stats.longest_span = (
        compute_streaks(history)
    )

    by_bytes, by_repo = Counter(), Counter()
    cursor = None
    while True:
        page = _graphql(GRAPHQL_REPOS, {"login": LOGIN, "cursor": cursor}, token)
        repos = page["user"]["repositories"]
        for node in repos["nodes"]:
            for edge in node["languages"]["edges"]:
                by_bytes[edge["node"]["name"]] += edge["size"]
                by_repo[edge["node"]["name"]] += 1
        if not repos["pageInfo"]["hasNextPage"]:
            break
        cursor = repos["pageInfo"]["endCursor"]

    stats.langs_bytes = _rank(by_bytes)
    stats.langs_repos = _rank(by_repo)
    return stats


def _account_created():
    data = json.loads(_get(f"https://api.github.com/users/{LOGIN}"))
    return datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")).date()


# --------------------------------------------------------------------------
# Collector: public endpoints (no token, for bootstrap and local runs)
# --------------------------------------------------------------------------

DAY_RE = re.compile(r'data-date="(\d{4}-\d\d-\d\d)"[^>]*data-level="(\d)"')
TIP_RE = re.compile(r"<tool-tip[^>]*>([^<]+)</tool-tip>")
COUNT_RE = re.compile(r"^(No|[\d,]+) contribution")


def _public_days(params=""):
    html = _get(f"https://github.com/users/{LOGIN}/contributions{params}")
    dates = [m[0] for m in DAY_RE.findall(html)]
    counts = []
    for tip in TIP_RE.findall(html):
        m = COUNT_RE.match(tip.strip())
        counts.append(0 if not m or m.group(1) == "No" else int(m.group(1).replace(",", "")))
    if len(counts) != len(dates):
        counts = [0] * len(dates)  # tooltip shape changed; levels still drive the ramp
    return [Day(date.fromisoformat(d), c) for d, c in zip(dates, counts)]


def _search_total(query):
    data = json.loads(
        _get(
            f"https://api.github.com/search/{query}",
            headers={"Accept": "application/vnd.github+json"},
        )
    )
    if "total_count" not in data:
        raise SystemExit(f"search returned no total_count: {data.get('message', data)}")
    return int(data["total_count"])


def collect_public():
    stats = Stats(source="public")
    today = datetime.now(timezone.utc).date()

    stats.days = sorted(_public_days(), key=lambda d: d.day)[-365:]
    stats.total_contributions = sum(d.count for d in stats.days)

    stats.commits = _search_total(f"commits?q=author:{LOGIN}&per_page=1")
    stats.prs = _search_total(f"issues?q=author:{LOGIN}+type:pr&per_page=1")
    stats.issues = _search_total(f"issues?q=author:{LOGIN}+type:issue&per_page=1")

    created = _account_created()
    history = []
    for year in range(created.year, today.year + 1):
        history += _public_days(f"?from={year}-01-01&to={year}-12-31")
    history = sorted({d.day: d for d in history}.values(), key=lambda d: d.day)
    stats.current_streak, stats.current_span, stats.longest_streak, stats.longest_span = (
        compute_streaks(history)
    )

    repos = json.loads(_get(f"https://api.github.com/users/{LOGIN}/repos?per_page=100&type=owner"))
    by_bytes, by_repo = Counter(), Counter()
    for repo in sorted(repos, key=lambda r: r["name"]):
        if repo["fork"] or repo["private"]:
            continue
        langs = json.loads(_get(repo["languages_url"]))
        for name, size in langs.items():
            by_bytes[name] += size
            by_repo[name] += 1

    stats.langs_bytes = _rank(by_bytes)
    stats.langs_repos = _rank(by_repo)
    return stats


def _rank(counter):
    ranked = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
    top = ranked[:TOP_LANGS]
    rest = sum(v for _, v in ranked[TOP_LANGS:])
    if rest:
        top.append(("Other", rest))
    return top


# --------------------------------------------------------------------------
# Rendering helpers
# --------------------------------------------------------------------------

def _lerp(a, b, t):
    ah, bh = a.lstrip("#"), b.lstrip("#")
    out = []
    for i in (0, 2, 4):
        x, y = int(ah[i:i + 2], 16), int(bh[i:i + 2], 16)
        out.append(round(x + (y - x) * t))
    return "#%02x%02x%02x" % tuple(out)


def gradient_samples(n):
    """n colors spread across the brand gradient, so series stay on-palette."""
    if n == 1:
        return [palette.PURPLE]
    stops = palette.GRADIENT
    out = []
    for i in range(n):
        t = i / (n - 1)
        for (o1, c1), (o2, c2) in zip(stops, stops[1:]):
            if o1 <= t <= o2:
                out.append(_lerp(c1, c2, (t - o1) / (o2 - o1) if o2 > o1 else 0))
                break
    return out


def fmt(n):
    return f"{n:,}"


def anim_css(count, selector="g.a"):
    """Staggered rise-and-fade, disabled under prefers-reduced-motion.

    Written 'not all and (...)' rather than the Level 4 'not (...)' form: a
    media query that fails to parse takes its whole block with it, which would
    silently strip the animation rather than degrade it.
    """
    delays = "".join(
        f"{selector}{i}{{animation-delay:{i * ANIM_STAGGER:.3f}s}}" for i in range(count)
    )
    return (
        "@keyframes rise{from{opacity:0;transform:translateY(6px)}"
        "to{opacity:1;transform:translateY(0)}}"
        f"@media not all and (prefers-reduced-motion: reduce){{"
        f"{selector.split('.')[0]}.a{{opacity:0;animation:rise {ANIM_DUR}s ease-out forwards}}"
        f"{delays}}}"
    )


def svg_open(width, height, label):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(label)}">'
    )


# --------------------------------------------------------------------------
# stats.svg
# --------------------------------------------------------------------------

def render_stats(s):
    tiles = [
        ("contributions", fmt(s.total_contributions), "last 365 days"),
        ("commits", fmt(s.commits), "all time, public"),
        ("pull requests", fmt(s.prs), "all time, public"),
        ("issues", fmt(s.issues), "all time, public"),
    ]
    height = 132
    col = CARD_W / len(tiles)
    colors = gradient_samples(len(tiles))
    faces = FaceSet(500, 800)

    body = []
    for i, ((label, value, sub), color) in enumerate(zip(tiles, colors)):
        faces[800].use(value)
        faces[500].use(label, sub)
        cx = col * i + col / 2
        vw = advance(value, 34)
        body.append(
            f'<g class="a a{i}">'
            f'<text x="{cx:.1f}" y="52" text-anchor="middle" fill="{color}" '
            f'font-family={faces[800].stack()!r} font-size="34" font-weight="800">{escape(value)}</text>'
            f'<rect x="{cx - vw / 2:.1f}" y="62" width="{vw:.1f}" height="3" rx="1.5" '
            f'fill="{color}" opacity="{palette.RULE_OPACITY}"/>'
            f'<text x="{cx:.1f}" y="88" text-anchor="middle" fill="{palette.INK}" '
            f'font-family={faces[500].stack()!r} font-size="13" font-weight="500">{escape(label)}</text>'
            f'<text x="{cx:.1f}" y="106" text-anchor="middle" fill="{palette.DIM}" '
            f'font-family={faces[500].stack()!r} font-size="10" font-weight="500">{escape(sub)}</text>'
            f"</g>"
        )

    return (
        svg_open(CARD_W, height, "Contribution, commit, pull request and issue totals")
        + f"<style>{faces.css()}{anim_css(len(tiles))}</style>"
        + "".join(body)
        + "</svg>\n"
    )


# --------------------------------------------------------------------------
# langs.svg
# --------------------------------------------------------------------------

def render_langs(s):
    groups = [("by bytes", s.langs_bytes, True), ("by repository count", s.langs_repos, False)]
    faces = FaceSet(500, 600)
    pad, bar_h, row_h = 4, 16, 88
    height = 30 + row_h * len(groups)
    body = []
    idx = 0

    for gi, (title, data, as_bytes) in enumerate(groups):
        total = sum(v for _, v in data) or 1
        colors = gradient_samples(max(len(data), 2))
        top = 24 + gi * row_h
        faces[600].use(title)
        body.append(
            f'<text x="0" y="{top}" fill="{palette.INK}" font-family={faces[600].stack()!r} '
            f'font-size="12" font-weight="600">{escape(title)}</text>'
        )

        x = 0.0
        segs = []
        for (name, value), color in zip(data, colors):
            w = (value / total) * CARD_W
            segs.append(
                f'<rect x="{x:.2f}" y="{top + 10}" width="{max(w - 1.5, 0.5):.2f}" '
                f'height="{bar_h}" rx="3" fill="{color}"/>'
            )
            x += w
        body.append(f'<g class="a a{idx}">' + "".join(segs) + "</g>")
        idx += 1

        legend_y = top + bar_h + 26
        lx = 0.0
        for (name, value), color in zip(data, colors):
            pct = value / total * 100
            if as_bytes:
                shown = f"{value / 1024:,.0f} KB" if value < 1024 ** 2 else f"{value / 1024 ** 2:,.1f} MB"
            else:
                shown = f"{value} repo" + ("s" if value != 1 else "")
            text = f"{name} {pct:.0f}% · {shown}"
            faces[500].use(text)
            width = advance(text, 10.5) + 16
            if lx + width > CARD_W:
                break
            body.append(
                f'<g class="a a{idx}">'
                f'<rect x="{lx:.1f}" y="{legend_y - 7}" width="7" height="7" rx="2" fill="{color}"/>'
                f'<text x="{lx + 11:.1f}" y="{legend_y}" fill="{palette.DIM}" '
                f'font-family={faces[500].stack()!r} font-size="10.5" '
                f'font-weight="500">{escape(text)}</text></g>'
            )
            idx += 1
            lx += width

    return (
        svg_open(CARD_W, height, "Top languages by bytes and by repository count")
        + f"<style>{faces.css()}{anim_css(idx)}</style>"
        + "".join(body)
        + "</svg>\n"
    )


# --------------------------------------------------------------------------
# streak.svg
# --------------------------------------------------------------------------

def _span_text(span):
    if not span:
        return "none yet"
    a, b = span
    fmt_d = lambda d: d.strftime("%b %-d, %Y") if os.name != "nt" else d.strftime("%b %#d, %Y")
    return fmt_d(a) if a == b else f"{fmt_d(a)} - {fmt_d(b)}"


def render_streak(s):
    active = sum(1 for d in s.days if d.count > 0)
    tiles = [
        ("current streak", f"{s.current_streak}", _span_text(s.current_span)),
        ("longest streak", f"{s.longest_streak}", _span_text(s.longest_span)),
        ("active days", f"{active}", "of the last 365"),
    ]
    height = 132
    col = CARD_W / len(tiles)
    colors = gradient_samples(len(tiles))
    faces = FaceSet(500, 800)
    body = []

    for i, ((label, value, sub), color) in enumerate(zip(tiles, colors)):
        faces[800].use(value)
        faces[500].use(label, sub, "days")
        cx = col * i + col / 2
        unit = " days" if value != "1" else " day"
        faces[500].use(unit)
        body.append(
            f'<g class="a a{i}">'
            f'<text x="{cx:.1f}" y="54" text-anchor="middle" fill="{color}" '
            f'font-family={faces[800].stack()!r} font-size="38" font-weight="800">{escape(value)}</text>'
            f'<text x="{cx:.1f}" y="80" text-anchor="middle" fill="{palette.INK}" '
            f'font-family={faces[500].stack()!r} font-size="13" font-weight="500">{escape(label)}</text>'
            f'<text x="{cx:.1f}" y="99" text-anchor="middle" fill="{palette.DIM}" '
            f'font-family={faces[500].stack()!r} font-size="10" font-weight="500">{escape(sub)}</text>'
            f"</g>"
        )

    rule = (
        f'<rect x="0" y="116" width="{CARD_W}" height="2" rx="1" fill="{palette.PURPLE}" '
        f'opacity="{palette.GRID_OPACITY}"/>'
    )
    return (
        svg_open(CARD_W, height, "Current streak, longest streak and active days")
        + f"<style>{faces.css()}{anim_css(len(tiles))}</style>"
        + "".join(body) + rule
        + "</svg>\n"
    )


# --------------------------------------------------------------------------
# year.svg
# --------------------------------------------------------------------------

def render_year(s):
    """One character per day, laid out the way GitHub lays out its calendar:
    columns are weeks, rows are days of the week. No reveal animation here --
    it sits far enough down the README that it would finish before anyone
    scrolled to it."""
    days = s.days
    if not days:
        raise SystemExit("no contribution days collected")

    nonzero = sorted(d.count for d in days if d.count > 0)
    if nonzero:
        cuts = [nonzero[int(len(nonzero) * q)] for q in (0.5, 0.8, 0.95)]
    else:
        cuts = [1, 2, 3]

    def glyph(count):
        if count <= 0:
            return RAMP[0]
        for i, cut in enumerate(cuts):
            if count <= cut:
                return RAMP[min(i + 1, len(RAMP) - 1)]
        return RAMP[-1]

    first = days[0].day
    offset = (first.weekday() + 1) % 7          # Sunday is row 0, matching GitHub
    cols = (offset + len(days) + 6) // 7
    grid = [[None] * cols for _ in range(7)]
    for i, entry in enumerate(days):
        grid[(i + offset) % 7][(i + offset) // 7] = entry

    fs, lh = 14, 1.10
    cw = fs * 0.600
    gutter, top = 30, 30
    width = round(gutter + cols * cw + 4, 2)
    height = round(top + 7 * fs * lh + 8, 2)

    faces = FaceSet(400, 500)
    faces[400].use(RAMP)

    body, months = [], []
    seen = set()
    for c in range(cols):
        for r in range(7):
            entry = grid[r][c]
            if entry and (entry.day.year, entry.day.month) not in seen and entry.day.day <= 7:
                seen.add((entry.day.year, entry.day.month))
                label = entry.day.strftime("%b")
                faces[500].use(label)
                months.append(
                    f'<text x="{gutter + c * cw:.1f}" y="18" fill="{palette.DIM}" '
                    f'font-family={faces[500].stack()!r} font-size="10" '
                    f'font-weight="500">{escape(label)}</text>'
                )
            break

    for r, name in enumerate(("", "Mon", "", "Wed", "", "Fri", "")):
        if name:
            faces[500].use(name)
            y = top + r * fs * lh + fs * 0.8
            body.append(
                f'<text x="0" y="{y:.1f}" fill="{palette.DIM}" '
                f'font-family={faces[500].stack()!r} font-size="9" '
                f'font-weight="500">{name}</text>'
            )

    for r in range(7):
        row = "".join(glyph(grid[r][c].count) if grid[r][c] else " " for c in range(cols))
        y = round(top + r * fs * lh, 2)
        body.append(
            f'<text x="{gutter}" y="{y}" xml:space="preserve" dominant-baseline="hanging" '
            f'fill="{palette.PURPLE}" font-family={faces[400].stack()!r} '
            f'font-size="{fs}px" font-weight="400">{escape(row)}</text>'
        )

    legend = f"{RAMP[0]} none   {RAMP[1]} low   {RAMP[2]} mid   {RAMP[3]} high"
    faces[500].use(legend)
    body.append(
        f'<text x="{gutter}" y="{height - 2:.1f}" xml:space="preserve" fill="{palette.DIM}" '
        f'font-family={faces[500].stack()!r} font-size="9" font-weight="500">{escape(legend)}</text>'
    )

    label = f"Contribution activity for the last {len(days)} days"
    return (
        svg_open(width, height + 6, label)
        + f"<style>{faces.css()}</style>"
        + "".join(months) + "".join(body)
        + "</svg>\n"
    )


# --------------------------------------------------------------------------

def main():
    token = os.environ.get("GH_STATS_TOKEN")
    if token:
        print("collecting via GraphQL (GH_STATS_TOKEN set)")
        stats = collect_graphql(token)
    else:
        print("GH_STATS_TOKEN unset -- collecting from public endpoints")
        stats = collect_public()

    for name, svg in (
        ("stats.svg", render_stats(stats)),
        ("langs.svg", render_langs(stats)),
        ("streak.svg", render_streak(stats)),
        ("year.svg", render_year(stats)),
    ):
        dest = ROOT / name
        dest.write_text(svg, encoding="utf-8")
        print(f"  {name:12} {dest.stat().st_size:>7,}B")

    print(
        f"\nsource={stats.source}  contributions={stats.total_contributions}  "
        f"commits={stats.commits}  prs={stats.prs}  issues={stats.issues}\n"
        f"streak current={stats.current_streak} longest={stats.longest_streak}  "
        f"languages={len(stats.langs_bytes)}"
    )


if __name__ == "__main__":
    main()
