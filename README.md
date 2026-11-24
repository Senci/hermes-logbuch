# Logbuch

![Logbuch](docs/assets/cover.jpg)

A value-ranked list of your real-work Hermes sessions. Interactive sessions (desktop and CLI) of the profile the backend runs in, compression chains folded into their root, grouped by topic and ranked by business value, then by shipped output (commit calls plus MR calls). The tab is called "Logbuch" on purpose.

## Install

Needs Hermes 0.21.5 or newer; the pane and page need Hermes Desktop. Put the `logbuch` directory into `~/.hermes/plugins/` (or `hermes plugins install Senci/hermes-logbuch`), then run `hermes plugins enable logbuch`.

With no further setup the plugin runs on a built-in neutral set of topics and no rules. Point it at your own topics and rules with a data file (below).

## Settings

Settings live in Hermes Desktop under Settings, Plugins, Logbuch, and are stored under `plugins.entries.logbuch.settings` in `config.yaml`. A value of the wrong type falls back to its default.

| Key | Default | Use |
|---|---|---|
| `data_file` | empty | path of the data file; empty means `$HERMES_HOME/logbuch/data.json` when it exists, else the built-in default |
| `classify_model` | `claude-haiku-5-5` | model that `POST /classify` labels sessions with |
| `provider` | `anthropic` | Hermes provider for that model |
| `profile` | `default` | Hermes profile the classify call runs under |
| `classify_limit` | `20` | sessions labelled per `POST /classify` when the request names no `limit`; a request never labels more than 50 |

## Data file

One JSON file holds everything that is about your work rather than about the plugin. `examples/data.example.json` is a complete starting point. Only `topics` is required; a missing section takes the built-in default.

| Key | Meaning |
|---|---|
| `topics` | `{KEY: name}`: the topics a session can carry. Every label, the classify prompt and the digest use exactly these keys |
| `loose_end` | regex (case-insensitive) matched on the first 320 characters of a session's last reply; a match sets the `loose end` mark |
| `open_states` | `{waiting_go, not_merged, todo: regex}`: the phrases that put a session into that state, tried in file order (see States) |
| `rubric` | the value rubric sentence in the classify prompt, for example `3 = shipped for others; 2 = ...; 0 = personal.` |
| `rules` | list of rules that label or hint without a model call |

A rule is `{name, field, pattern, topic, value}`. `field` is `path` (the session's git root and working directory) or `text` (its title plus the first 600 characters of its first prompt); `pattern` is a case-insensitive regex; `topic` is a key of `topics`. `value` is optional: left out or `null` the rule is a topic hint the model layer may take on; an integer from 0 to 3 makes it a label (source `rule`, summary = the session title); `{"mr_calls_at_least": 5, "value": 3, "otherwise": 2}` labels 3 when the session has five or more MR calls, else 2. The first rule with a value wins, otherwise the first hint stands.

The file is read on every request and cached by modification time, so an edit applies without a restart. A file that cannot be read or fails validation logs one error and the built-in default stands in, so the routes keep answering.

## What it shows

- **Pane** (340px, tab "Logbuch" stacked with Files and Review). Three filter rows: value chips `P1`, `P2`, `P3`, `none` with a `Loose ends` chip; the state chips (see States); then search, sort and collapse-all. Topic groups collapse. A row has two lines: the priority pill, the state icon and the summary, then the date, `N commit calls`, `N MR calls` and a `loose end` mark. The header link `Page` opens the full page; the footer holds the weekly digest.
- **Page** at `/logbuch`: the same list in the `sessions-by-value` layout (adds the session title, turns, tool calls and the id), with the digest control in the header.
- **Sidebar badge**: `P1` or `P2` at the end of a session row in the left Sessions list, with the session's state icon inside the pill (a plain pill when the state is `none`). A critical session gets a red pill with the critical icon. Every other row (P3, none, not labelled yet) shows nothing. The badge reads the pane's cached answer, so rows cost no request.
- **Default filter** is P1 plus P2. `none` also covers sessions that have no label yet (shown with a `?`).
- Filters, search text, sort and collapsed topics are remembered in the plugin's storage.

## States

Every session has one state, set by the backend from how the chain ended and what it shipped. The highest applicable state wins, in this order:

| Icon | State | Colour | Meaning |
|---|---|---|---|
| alert triangle, pulsing | `critical` | red | a P1 session whose last assistant message was a provider problem: a failed turn (not a content-policy block) or a Hermes interrupt line (`Operation interrupted: waiting for model response`, `handling API error`, `retrying API call after error`) |
| bell, swinging | `waiting_go` | orange | the last reply matches a `waiting_go` phrase (default: needs your go, waiting on you, decisions open) |
| circled exclamation mark | `interrupted` | orange | the same provider-problem end on a session that is not P1 (or a P1 without a label yet) |
| upload arrow | `not_merged` | yellow | the last reply matches a `not_merged` phrase (default: none is merged, not merged, a Draft) |
| clipboard | `todo` | blue | the last reply matches a `todo` phrase (default: still open, still to do) |
| circled check | `shipped` | green | commit or MR calls and nothing open |
| empty circle | `none` | grey | nothing open and nothing shipped |

Marking the loose end done turns every open state (the first five) into `shipped` (when the session has commit or MR calls) or `none`. A bare `Operation interrupted.` has no cause and does not count as a provider problem. Only the last assistant message is read, never tool output.

Hover an icon for its state name and the text the backend matched (redacted, 120 characters at most); a state with no match shows what it means. Only `critical` and `waiting_go` move, and under `prefers-reduced-motion: reduce` they show a static frame (the setting is followed live). The state chip row under the value chips filters by state: no chip pressed shows every state, pressed chips combine with OR and with the value, loose-end and search filters. The count on each chip ignores the chips themselves. An older backend that sends no state shows `none` everywhere.

Icons are Iconify `line-md` (Material Line Icons, MIT, Vjacheslav Trushkin), vendored in `desktop/src/icons/` with the JSON, its `.sha256` and the LICENSE; nothing is fetched at runtime.

## Actions

- Click a row (or Enter on it): opens the session through the app (`openSession`), not a link.
- Row menu (the `...` button): set the value (P1, P2, P3, none), edit topic and summary, mark a loose end done or reopen it. Each change is one `PUT /labels/{id}` and the list refetches. A label you save is `manual`: automatic labelling never overwrites it. A session without a label needs a topic and a value, so its menu opens the edit dialog.
- Digest: pick an ISO week with the arrows (current week by default) and press `Digest`. The backend writes `logbuch-<week>.md` under its `logbuch/digests/` directory and the app's save dialog hands you the file. The week is grouped by the backend's local time.

## Keybind and palette

`mod+alt+l` (Ctrl+Alt+L on Linux and Windows, Cmd+Option+L on macOS) and the palette row "Show Logbuch" run one action, `logbuch.reveal`. It fronts the Logbuch tab and is safe to repeat. Rebind it in the keybinds panel. On a desktop too old to have `revealPane` it opens the page instead.

## Hiding the tab

The Logbuch tab is hide-only, so it has no close button and the plugin stays on. Hide or show it from the tab menu or with Ctrl+K (Logbuch); Ctrl+J folds the whole Files zone, Logbuch included. The empty state of the pane says the same. A "Logbuch" row in the sidebar opens the full page.

## Data flow

Only `POST /classify` sends text to a model. The desktop half sends nothing to a model and never writes into a chat: no composer draft, no submit; rows only open sessions. Everything else (the list, rule labels, states, the digest) is computed locally from the sessions database, which is only ever opened read-only.

The labels shown come from the backend in three layers: rules from the data file, then a model call for sessions that have no label yet (only when `POST /classify` is called), then your manual edits. The model call carries only the chain's first user prompt and last assistant reply. A text with any key signal is withheld whole; every other text is redacted (keys, tokens, Bearer values, PEM blocks) and cut to 400 characters. The text goes through `hermes chat --oneshot --safe-mode` in a private query file, never on the command line, using the `classify_model`, `provider` and `profile` settings and your own Hermes login; no API key is involved. The reply must be strict JSON with a topic from your data file, a value from 0 to 3 and a summary, anything else stores nothing.

## Routes

Desktop: page `/logbuch`, pane `logbuch:pane`, action `logbuch.reveal`.

Backend (`/api/plugins/logbuch/`, from the spec):

| Route | Use |
|---|---|
| `GET /sessions` | the list, `profile`, `schema_ok`, `topics` |
| `PUT /labels/{id}` | set value, topic, summary, `loose_end_done` (merged over the stored label, `422` on a bad topic or value) |
| `POST /classify` | label sessions that have no label (not called from the desktop half) |
| `GET /digest?week=YYYY-Www` | the digest as Markdown (not called from the desktop half) |
| `POST /digest/file` | writes the digest file, returns `{path, name}` for the save dialog |

The list polls every 60 seconds. Connection and profile are part of every query, so switching the window's gateway or profile never shows another backend's data. If the backend cannot be reached the pane names the backend and profile it asked; a 404 means that backend does not have the plugin. If the sessions database lacks a column Logbuch reads, `schema_ok` is false and a banner says so.

## Development

Source is `desktop/src/`, and the [hermes-plugin-ui-kit](https://www.npmjs.com/package/hermes-plugin-ui-kit) package; `desktop/plugin.js` is built from it with SDK and react external: `sh scripts/rebuild.sh` in the plugin directory (needs node and npm; it installs the pinned esbuild and kit into the gitignored `.build/`), then commit both. `node tests/desktop.test.mjs` runs the tests of the pure modules (`logic.js`, `model.js`).
