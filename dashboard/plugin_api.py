"""logbuch backend, mounted at /api/plugins/logbuch/.

GET  /sessions        interactive sessions of this profile (compression chains folded into their root)
                      that did real work, each with a label (rule, llm or manual) or null
PUT  /labels/{id}     manual override of topic, value, summary and the loose-end mark
GET  /digest          Markdown digest of the P1 and P2 sessions of one ISO week (?week=YYYY-Www)
POST /digest/file     the same digest written to $HERMES_HOME/logbuch/digests/, returns {path, name}
POST /classify        label unlabelled sessions with a model through the hermes CLI (classify.py), 409 while one runs

state.db is only ever opened read-only; labels live in $HERMES_HOME/logbuch/labels.db, created on the
first write. Handlers are plain `def` so the threadpool runs the scan, never the event loop. The logic
sits in the lb_* modules beside this file; the dashboard imports this file by path, so the directory is
put on sys.path first.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Response

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import classify as lb_classify  # noqa: E402
import lb_service as svc  # noqa: E402

log = logging.getLogger(__name__)
router = APIRouter()


def _home() -> Path:
    try:
        from hermes_constants import get_hermes_home

        return Path(get_hermes_home())
    except ImportError:
        return Path(os.environ.get("HERMES_HOME") or Path.home() / ".hermes")


def _profile(home: Path) -> str:
    try:
        from hermes_cli.profiles import get_active_profile_name

        return str(get_active_profile_name())
    except Exception:
        log.debug("logbuch: profile name falls back to the home directory name", exc_info=True)
        return "default" if home.name == ".hermes" else home.name


def _guard(call, *args):
    try:
        return call(*args)
    except svc.ServiceError as exc:
        raise HTTPException(exc.status, exc.detail) from exc


@router.get("/sessions")
def sessions() -> dict:
    home = _home()
    return svc.sessions_payload(home, _profile(home))


@router.put("/labels/{session_id}")
def put_label(session_id: str, body: dict) -> dict:
    return _guard(svc.put_label, _home(), session_id, body)


@router.get("/digest")
def digest(week: str | None = Query(None)) -> Response:
    _week, text = _guard(svc.digest_markdown, _home(), week)
    return Response(content=text, media_type="text/markdown")


@router.post("/digest/file")
def digest_file(body: dict) -> dict:
    return _guard(svc.digest_file, _home(), body.get("week"))


@router.post("/classify")
def classify(body: dict | None = None) -> dict:
    home = _home()
    return _guard(lb_classify.run_body, home, body)
