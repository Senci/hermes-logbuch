"""logbuch: value-ranked view of the profile's interactive Hermes sessions.

The surface is dashboard/plugin_api.py (backend routes) and desktop/plugin.js (pane, page, sidebar
badge). The agent half registers no tools or hooks; state.db is only read, labels live in
$HERMES_HOME/logbuch/labels.db.
"""


def register(ctx) -> None:
    return None
