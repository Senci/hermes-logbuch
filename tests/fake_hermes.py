#!/usr/bin/env python3
"""Stand-in for the `hermes` CLI, copied to <tmp>/bin/hermes by test_classify.py.

Appends two JSON lines to $FAKE_HERMES_LOG per call (event start with argv, the query file text and its
modes; event end) and answers by the `MODE:<name>` marker found in the query text. Synthetic data only.
"""

import json
import os
import re
import stat
import subprocess
import sys
import time

VALID = {"topic": "OPS", "value": 3, "summary": "Fixed the production issue"}
PLAIN = {
    "ok": lambda: (json.dumps(VALID) + "\n\nsession_id: fake_%d\n" % os.getpid(), ""),
    "ok_stderr": lambda: (json.dumps(VALID) + "\n", "\nsession_id: fake_%d\n" % os.getpid()),
    "prose": lambda: ("This session looks like infra work.\n\nsession_id: fake_1\n", ""),
    "bad_topic": lambda: (json.dumps(dict(VALID, topic="NOPE")) + "\n", ""),
    "value5": lambda: (json.dumps(dict(VALID, value=5)) + "\n", ""),
    "extra_keys": lambda: (json.dumps(dict(VALID, confidence=0.9)) + "\n", ""),
    "fenced": lambda: ("```json\n" + json.dumps(VALID) + "\n```\n", ""),
}
SLEEP = {"slow": 1.0, "hold": 2.5, "hang": 60.0}


def log(path, record):
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(fd, (json.dumps(record) + "\n").encode())
    finally:
        os.close(fd)


def main() -> int:
    args = sys.argv[1:]
    query_file = args[args.index("--query-file") + 1] if "--query-file" in args else None
    text = ""
    modes = {}
    if query_file and os.path.exists(query_file):
        with open(query_file, encoding="utf-8") as fh:
            text = fh.read()
        modes = {"file": stat.S_IMODE(os.stat(query_file).st_mode), "dir": stat.S_IMODE(os.stat(os.path.dirname(query_file)).st_mode)}
    found = re.search(r"MODE:(\w+)", text)
    mode = found.group(1) if found else "ok"
    path = os.environ["FAKE_HERMES_LOG"]
    log(path, {"event": "start", "pid": os.getpid(), "t": time.time(), "mode": mode, "argv": args,
               "query_file": query_file, "query_text": text, "modes": modes,
               "hermes_home": os.environ.get("HERMES_HOME")})
    if mode == "fail":
        sys.stderr.write("boom\n")
        return 3
    if mode == "grandchild":
        child = subprocess.Popen(["sleep", "60"])
        log(path, {"event": "grandchild", "pid": child.pid})
        time.sleep(60)
    if mode in SLEEP:
        time.sleep(SLEEP[mode])
    out, err = PLAIN.get(mode, PLAIN["ok"])()
    sys.stdout.write(out)
    sys.stderr.write(err)
    log(path, {"event": "end", "pid": os.getpid(), "t": time.time()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
