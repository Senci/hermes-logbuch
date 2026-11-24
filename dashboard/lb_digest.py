"""Weekly digest: P1 (value 3) and P2 (value 2) sessions of one ISO week, grouped by topic, as Markdown."""

from __future__ import annotations

import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path

WEEK_RE = re.compile(r"^(\d{4})-W(\d{2})$")
DIGEST_VALUES = (3, 2)


class BadWeek(ValueError):
    pass


def parse_week(week: str) -> tuple[float, float, date]:
    """(start epoch, end epoch, monday) for `YYYY-Www`, local time of the backend; BadWeek otherwise."""
    m = WEEK_RE.match(week or "")
    if not m:
        raise BadWeek(f"week must look like YYYY-Www, got {week!r}")
    try:
        monday = date.fromisocalendar(int(m.group(1)), int(m.group(2)), 1)
    except ValueError as exc:
        raise BadWeek(f"no such ISO week: {week}") from exc
    start = time.mktime(datetime(monday.year, monday.month, monday.day).timetuple())
    nxt = monday + timedelta(days=7)
    end = time.mktime(datetime(nxt.year, nxt.month, nxt.day).timetuple())
    return start, end, monday


def current_week(now: float | None = None) -> str:
    iso = datetime.fromtimestamp(now if now is not None else time.time()).isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def file_name(week: str) -> str:
    parse_week(week)
    return f"logbuch-{week}.md"


def digest_path(home: Path, week: str) -> Path:
    return Path(home) / "logbuch" / "digests" / file_name(week)


def render(week: str, items: list[dict], topics: dict) -> str:
    start, end, monday = parse_week(week)
    sunday = monday + timedelta(days=6)
    picked = [i for i in items if start <= i["started_at"] < end and i["label"] and i["label"]["value"] in DIGEST_VALUES]
    p1 = sum(1 for i in picked if i["label"]["value"] == 3)
    p2 = len(picked) - p1
    commits = sum(i["commit_calls"] for i in picked)
    mrs = sum(i["mr_calls"] for i in picked)
    out = [
        f"# Logbuch {week}",
        "",
        f"Sessions started {monday.isoformat()} to {sunday.isoformat()} (local time).",
        f"P1: {p1}, P2: {p2}, commit calls: {commits}, MR calls: {mrs}.",
        "",
    ]
    if not picked:
        out.append("No P1 or P2 sessions in this week.")
        return "\n".join(out) + "\n"
    by_topic: dict[str, list[dict]] = {}
    for item in picked:
        by_topic.setdefault(item["label"]["topic"], []).append(item)
    order = [k for k in topics if k in by_topic] + [k for k in by_topic if k not in topics]
    for key in order:
        group = sorted(by_topic[key], key=lambda i: (-i["label"]["value"], i["started_at"]))
        out.append(f"## {topics.get(key, key)} ({key})")
        out.append("")
        for i in group:
            day = datetime.fromtimestamp(i["started_at"]).strftime("%Y-%m-%d")
            mark = " (loose end open)" if i["loose_end"] and not i["loose_end_done"] else ""
            summary = " ".join(i["label"]["summary"].split())
            out.append(
                f"- P{4 - i['label']['value']} {day} {summary} "
                f"[commit calls {i['commit_calls']}, MR calls {i['mr_calls']}]{mark}"
            )
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


def write_file(home: Path, week: str, text: str) -> Path:
    path = digest_path(home, week)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
