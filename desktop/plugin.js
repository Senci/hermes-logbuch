// desktop/src/index.js
import { KEYBINDS_AREA, PALETTE_AREA, PANES_AREA, ROUTES_AREA, SESSION_ROW_AREAS, SIDEBAR_NAV_AREA } from "@hermes/plugin-sdk";
import { createElement as h3 } from "react";

// desktop/src/kit/theme.js
var ui = (name) => `var(--ui-${name})`;
var TONE = {
  text: ui("text-primary"),
  muted: ui("text-tertiary"),
  secondary: ui("text-secondary"),
  faint: ui("text-quaternary"),
  accent: ui("accent"),
  green: ui("green"),
  red: ui("red"),
  yellow: ui("yellow"),
  blue: ui("blue"),
  purple: ui("purple")
};
var muted = { color: TONE.muted };
function mountStyle(id, css) {
  const style = document.createElement("style");
  style.dataset.plugin = id;
  style.textContent = css;
  document.head.appendChild(style);
  return () => style.remove();
}

// desktop/src/css.js
var CSS = `
.lb{--lb-v3:var(--ui-green);--lb-v2:var(--ui-yellow);--lb-v1:var(--ui-blue);--lb-v0:var(--ui-text-tertiary);
 --lb-lo:color-mix(in srgb,var(--ui-red) 55%,var(--ui-yellow));
 --lb-t3:color-mix(in srgb,var(--lb-v3) 80%,var(--ui-text-primary));--lb-t2:color-mix(in srgb,var(--lb-v2) 80%,var(--ui-text-primary));
 --lb-t1:color-mix(in srgb,var(--lb-v1) 80%,var(--ui-text-primary));--lb-t0:var(--ui-text-tertiary);
 --lb-tlo:color-mix(in srgb,var(--lb-lo) 80%,var(--ui-text-primary));
 display:flex;flex-direction:column;height:100%;min-height:0;font-size:12px;line-height:1.45;color:var(--ui-text-primary)}
.lb *{box-sizing:border-box}
.lb button{font:inherit}
.lb-head{display:flex;align-items:center;gap:6px;padding:8px 10px 2px;flex-wrap:wrap}
.lb-head .lb-grow{flex:1 1 auto}
.lb-title{font-size:13px;font-weight:600}
.lb.wide .lb-title{font-size:17px}
.lb-sub{color:var(--ui-text-tertiary);font-size:11.5px;padding:0 10px 6px}
.lb-bar{display:flex;align-items:center;gap:6px;padding:3px 10px;flex-wrap:wrap}
.lb-bar .lb-search{flex:1 1 110px;min-width:90px}
.lb-foot{border-top:1px solid var(--ui-stroke-tertiary);padding:6px 10px}
.lb-chip{border:1px solid var(--ui-stroke-secondary);background:transparent;color:var(--ui-text-secondary);border-radius:999px;
 padding:1px 9px;font-size:11.5px;cursor:pointer;white-space:nowrap}
.lb-chip:hover{background:var(--ui-row-hover-background)}
.lb-chip[aria-pressed=true]{border-color:currentColor;font-weight:600;background:color-mix(in srgb,currentColor 10%,transparent)}
.lb-chip.v3{color:var(--lb-t3)}.lb-chip.v2{color:var(--lb-t2)}.lb-chip.v1{color:var(--lb-t1)}.lb-chip.v0{color:var(--lb-t0)}
.lb-chip.lo{color:var(--lb-tlo)}
.lb-stats{color:var(--ui-text-tertiary);font-size:11.5px;padding:2px 10px 6px}
.lb-banner{margin:4px 10px;padding:6px 8px;border-radius:6px;font-size:11.5px;
 border:1px solid color-mix(in srgb,var(--ui-yellow) 55%,transparent);background:color-mix(in srgb,var(--ui-yellow) 12%,transparent)}
.lb-banner.bad{border-color:color-mix(in srgb,var(--ui-red) 55%,transparent);background:color-mix(in srgb,var(--ui-red) 12%,transparent)}
.lb-scroll{flex:1 1 auto;min-height:0;overflow:auto;padding:2px 10px 12px}
.lb.wide .lb-scroll{padding:2px 20px 24px}
.lb.wide .lb-head,.lb.wide .lb-sub,.lb.wide .lb-bar,.lb.wide .lb-stats{padding-left:20px;padding-right:20px}
.lb.wide .lb-banner{margin-left:20px;margin-right:20px}
.lb-grp{border:1px solid var(--ui-stroke-tertiary);border-radius:8px;margin-bottom:8px;overflow:hidden}
.lb-gh{display:flex;flex-wrap:wrap;align-items:baseline;gap:2px 10px;width:100%;text-align:left;border:0;background:transparent;
 color:var(--ui-text-primary);padding:6px 8px;cursor:pointer}
.lb-gh:hover{background:var(--ui-row-hover-background)}
.lb-gh .lb-caret{color:var(--ui-text-tertiary);align-self:center}
.lb-gname{font-weight:600}
.lb-gmeta{color:var(--ui-text-tertiary);font-size:11.5px}
.lb-row{position:relative;border-top:1px solid var(--ui-stroke-tertiary);padding:6px 6px 6px 12px;cursor:pointer;outline:none}
.lb-row:hover,.lb-row:focus-visible{background:var(--ui-row-hover-background)}
.lb-row::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--lb-v0)}
.lb-row.v3::before{background:var(--lb-v3)}.lb-row.v2::before{background:var(--lb-v2)}.lb-row.v1::before{background:var(--lb-v1)}
.lb-l1{display:flex;align-items:center;gap:6px;min-width:0}
.lb-pri{flex:none;font-size:10.5px;font-weight:700;border-radius:4px;padding:0 5px;border:1px solid currentColor;color:var(--lb-t0)}
.lb-pri.v3{color:var(--lb-t3)}.lb-pri.v2{color:var(--lb-t2)}.lb-pri.v1{color:var(--lb-t1)}
.lb-sum{flex:1 1 auto;min-width:0;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.lb-menu{flex:none}
.lb-l2{display:flex;flex-wrap:wrap;gap:0 10px;color:var(--ui-text-tertiary);font-size:11.5px;margin-top:1px}
.lb-l2 b{color:var(--ui-text-primary);font-weight:600}
.lb-ttl{font-style:italic;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100%}
.lb-loose{color:var(--lb-tlo);font-weight:600}
.lb-id{font:11px var(--font-mono,ui-monospace,monospace);user-select:all}
.lb-legend{color:var(--ui-text-tertiary);font-size:11px;margin-top:12px}
.lb-note{color:var(--ui-text-tertiary);font-size:11.5px;margin-top:8px;max-width:40ch}
.lb-empty{display:grid;place-items:center;text-align:center;padding:28px 8px}
.lb-wk{display:inline-flex;align-items:center;gap:2px}
.lb-wk code{font:11.5px var(--font-mono,ui-monospace,monospace);min-width:7.4ch;text-align:center}
.lb-form{display:grid;gap:10px;margin-top:8px}
.lb-form label{display:grid;gap:3px;font-size:11.5px;color:var(--ui-text-secondary)}
.lb-form .lb-inline{display:flex;align-items:center;gap:8px}
.lb-st{display:inline-flex;flex:none;width:16px;height:16px;color:var(--st,var(--ui-text-tertiary))}
.lb-st svg{display:block;width:100%;height:100%}
.lb-c-critical{--st:color-mix(in srgb,var(--ui-red) 80%,var(--ui-text-primary))}
.lb-c-waiting_go,.lb-c-interrupted{--st:color-mix(in srgb,var(--ui-orange,#db704b) 80%,var(--ui-text-primary))}
.lb-c-not_merged{--st:color-mix(in srgb,var(--ui-yellow) 80%,var(--ui-text-primary))}
.lb-c-todo{--st:color-mix(in srgb,var(--ui-blue) 80%,var(--ui-text-primary))}
.lb-c-shipped{--st:color-mix(in srgb,var(--ui-green) 80%,var(--ui-text-primary))}
.lb-c-none{--st:var(--ui-text-tertiary)}
.lb-chip.sc{display:inline-flex;align-items:center;gap:3px;padding:1px 8px 1px 5px;color:var(--st)}
.lb-chip.sc .lb-st{width:14px;height:14px}
.lb-n{font-weight:600;opacity:.85;margin-left:1px}
.lb-lg{display:flex;align-items:center;gap:6px;margin-top:3px}
.lb-lg b{color:var(--ui-text-primary);font-weight:600}
.lb-badge .lb-st{width:12px;height:12px;margin:0 2px 0 -1px}
.lb-badge{display:inline-flex;align-items:center;font-size:10px;font-weight:700;line-height:1;border-radius:4px;padding:2px 4px;
 border:1px solid currentColor}
.lb-badge.p1{color:color-mix(in srgb,var(--ui-green) 80%,var(--ui-text-primary))}
.lb-badge.p2{color:color-mix(in srgb,var(--ui-yellow) 80%,var(--ui-text-primary))}
.lb-badge.critical{color:color-mix(in srgb,var(--ui-red) 80%,var(--ui-text-primary));background:color-mix(in srgb,var(--ui-red) 12%,transparent)}
`;

// desktop/src/data.js
import { captureGatewayFileDownload, host as host2, queryClient as queryClient2, useQuery as useQuery2 } from "@hermes/plugin-sdk";

// desktop/src/kit/live.js
import { atom, host, queryClient, useQuery, useValue } from "@hermes/plugin-sdk";
var POLL_FLOOR_MS = 15e3;
var LIVE_SAFETY_MS = 6e4;
function useBackend() {
  return { conn: useValue(host.state.connectionId) ?? "", profile: useValue(host.state.profile) ?? "" };
}
function useLiveQuery({ live = false, pollMs = POLL_FLOOR_MS, liveMs = LIVE_SAFETY_MS, ...query2 }) {
  return useQuery({ ...query2, refetchInterval: live ? liveMs : pollMs });
}

// desktop/src/model.js
var ID = "logbuch";
var PATH = "/logbuch";
var PANE_ID = `${ID}:pane`;
var ACTION_ID = "logbuch.reveal";
var KEYBIND = "mod+alt+l";
var POLL_MS = 6e4;
var NAV_ORDER = 53;
var HIDE_NOTE = "The Logbuch tab only hides: use its tab menu or Ctrl+K (Logbuch) to hide or show it, and Ctrl+J to fold the whole Files zone with it. The plugin stays on.";
var PANE_DATA = {
  placement: "right",
  dock: { pane: "files", pos: "center" },
  collapsible: true,
  hideOnly: true,
  width: "340px",
  minWidth: "15rem",
  maxWidth: "36rem",
  tabTitleText: () => "Logbuch"
};
var NAV_DATA = { path: PATH, label: "Logbuch", codicon: "notebook" };
var STALE_MS = 3e4;
var SUMMARY_MAX = 120;
var VALUES = [
  [3, "P1", "High"],
  [2, "P2", "Medium"],
  [1, "P3", "Low"],
  [0, "none", "No business value"]
];
var VALUE_LABEL = { 3: "P1", 2: "P2", 1: "P3", 0: "-" };
var SORTS = [
  { id: "score", label: "Priority" },
  { id: "date", label: "Newest" },
  { id: "ship", label: "Shipped" }
];
var UNLABELLED = "_unlabelled";
var UNLABELLED_NAME = "Not labelled yet";
var STORE = { filters: "filters", sort: "sort", collapsed: "collapsed" };
var STATES = [
  ["critical", "Critical", "alert-loop", true, "A P1 session that ended on a provider problem"],
  ["waiting_go", "Waiting on go", "bell-alert-loop", true, "The last reply waits for your go or a decision"],
  ["interrupted", "Interrupted", "alert-circle-twotone", false, "Ended on a provider problem, not a P1 session"],
  ["not_merged", "Not merged", "upload-twotone", false, "The last reply says a merge request is not merged or is a draft"],
  ["todo", "To do", "clipboard-list-twotone", false, "The last reply says something is still open or still to do"],
  ["shipped", "Shipped", "confirm-circle-twotone", false, "Commit or MR calls and nothing open"],
  ["none", "None", "circle", false, "Nothing open and nothing shipped"]
];
var STATE_IDS = STATES.map((s) => s[0]);
var DEFAULT_FILTERS = { vals: { 3: true, 2: true, 1: false, 0: false }, loose: false, q: "", states: {} };

// desktop/src/state.js
import { atom as atom2 } from "@hermes/plugin-sdk";

// desktop/src/logic.js
var num = (n) => Number.isFinite(n) ? n : 0;
var valueOf = (it) => it.label && Number.isInteger(it.label.value) ? it.label.value : null;
var bucket = (it) => valueOf(it) ?? 0;
var topicKey = (it) => it.label && it.label.topic || UNLABELLED;
var topicName = (topics, key) => key === UNLABELLED ? UNLABELLED_NAME : topics && topics[key] || key;
var summaryOf = (it) => it.label && it.label.summary || it.title || "(untitled)";
var shipped = (it) => num(it.commit_calls) + num(it.mr_calls);
var isLoose = (it) => !!it.loose_end && !it.loose_end_done;
var stateOf = (it) => STATE_IDS.includes(it.state) ? it.state : "none";
var evidenceOf = (it) => typeof it.state_evidence === "string" && it.state_evidence ? it.state_evidence : null;
var stateTip = (it) => {
  const row = STATES.find((s) => s[0] === stateOf(it)) || STATES[STATES.length - 1];
  return `${row[1]}: ${evidenceOf(it) || row[4]}`;
};
var scoreOf = (it) => bucket(it) * 100 + Math.min(shipped(it), 60) + Math.min(num(it.edits), 40) / 10;
function normalizeFilters(raw) {
  const vals = { ...DEFAULT_FILTERS.vals };
  if (raw && typeof raw === "object" && raw.vals && typeof raw.vals === "object") {
    for (const [v] of VALUES) if (v in raw.vals) vals[v] = !!raw.vals[v];
  }
  const states = {};
  if (raw && typeof raw === "object" && raw.states && typeof raw.states === "object") {
    for (const id of STATE_IDS) if (raw.states[id] === true) states[id] = true;
  }
  return { vals, loose: !!(raw && raw.loose), q: raw && typeof raw.q === "string" ? raw.q : "", states };
}
var normalizeSort = (raw) => SORTS.some((s) => s.id === raw) ? raw : "score";
function normalizeCollapsed(raw) {
  const out = {};
  if (raw && typeof raw === "object") {
    for (const k of Object.keys(raw)) if (raw[k] === true) out[k] = true;
  }
  return out;
}
var nextSort = (cur) => SORTS[(SORTS.findIndex((s) => s.id === cur) + 1) % SORTS.length].id;
function filterBase(items, topics, f) {
  const q = f.q.trim().toLowerCase();
  return items.filter((it) => {
    if (!f.vals[bucket(it)]) return false;
    if (f.loose && !isLoose(it)) return false;
    if (!q) return true;
    return `${summaryOf(it)} ${it.title || ""} ${it.id} ${topicName(topics, topicKey(it))}`.toLowerCase().includes(q);
  });
}
var anyState = (f) => STATE_IDS.some((id) => f.states && f.states[id]);
function filterItems(items, topics, f) {
  const base = filterBase(items, topics, f);
  return anyState(f) ? base.filter((it) => f.states[stateOf(it)]) : base;
}
function stateCounts(items) {
  const out = Object.fromEntries(STATE_IDS.map((id) => [id, 0]));
  for (const it of items) out[stateOf(it)]++;
  return out;
}
var newer = (a, b) => num(b.started_at) - num(a.started_at);
var byId = (a, b) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
function sortItems(items, sort) {
  const cmp = sort === "date" ? (a, b) => newer(a, b) || byId(a, b) : sort === "ship" ? (a, b) => shipped(b) - shipped(a) || scoreOf(b) - scoreOf(a) || newer(a, b) || byId(a, b) : (a, b) => scoreOf(b) - scoreOf(a) || newer(a, b) || byId(a, b);
  return [...items].sort(cmp);
}
function groupItems(items, topics, sort) {
  const by = /* @__PURE__ */ new Map();
  for (const it of items) {
    const k = topicKey(it);
    if (!by.has(k)) by.set(k, []);
    by.get(k).push(it);
  }
  const groups = [...by].map(([key, list]) => {
    const rows = sortItems(list, sort);
    return {
      key,
      name: topicName(topics, key),
      items: rows,
      p1: rows.filter((i) => valueOf(i) === 3).length,
      commit_calls: rows.reduce((t, i) => t + num(i.commit_calls), 0),
      mr_calls: rows.reduce((t, i) => t + num(i.mr_calls), 0),
      score: rows.reduce((t, i) => t + scoreOf(i), 0)
    };
  });
  return groups.sort((a, b) => b.score - a.score || (a.name < b.name ? -1 : a.name > b.name ? 1 : 0));
}
function summarize(items) {
  const byValue = { 3: 0, 2: 0, 1: 0, 0: 0 };
  let commit_calls = 0;
  let mr_calls = 0;
  let loose = 0;
  const topics = /* @__PURE__ */ new Set();
  for (const it of items) {
    byValue[bucket(it)]++;
    commit_calls += num(it.commit_calls);
    mr_calls += num(it.mr_calls);
    if (isLoose(it)) loose++;
    topics.add(topicKey(it));
  }
  return { count: items.length, topics: topics.size, byValue, commit_calls, mr_calls, loose };
}
function badgeIndex(items) {
  const m = /* @__PURE__ */ new Map();
  for (const it of items || []) {
    const v = valueOf(it);
    if (v === 3) m.set(it.id, "P1");
    else if (v === 2) m.set(it.id, "P2");
  }
  return m;
}
var badgeFor = (index, id) => index && index.get(id) || null;
function badgeStates(items) {
  const m = /* @__PURE__ */ new Map();
  for (const it of items || []) {
    const v = valueOf(it);
    if (v === 3 || v === 2) m.set(it.id, { state: stateOf(it), evidence: evidenceOf(it), tip: stateTip(it) });
  }
  return m;
}
var pad2 = (n) => String(n).padStart(2, "0");
var DAY = 864e5;
function fmtDate(sec) {
  const d = new Date(num(sec) * 1e3);
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}
function fmtTime(sec) {
  const d = new Date(num(sec) * 1e3);
  return `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}
function isoParts(y, m, d) {
  const t = new Date(Date.UTC(y, m, d));
  t.setUTCDate(t.getUTCDate() + 4 - (t.getUTCDay() || 7));
  const year = t.getUTCFullYear();
  return { year, week: Math.ceil(((t - Date.UTC(year, 0, 1)) / DAY + 1) / 7) };
}
var weekLabel = ({ year, week }) => `${year}-W${pad2(week)}`;
var weekOfDate = (d) => weekLabel(isoParts(d.getFullYear(), d.getMonth(), d.getDate()));
var weekOfEpoch = (sec) => weekOfDate(new Date(num(sec) * 1e3));
var currentWeek = (now = /* @__PURE__ */ new Date()) => weekOfDate(now);
function mondayUtc(year, week) {
  const jan4 = new Date(Date.UTC(year, 0, 4));
  return jan4.getTime() - ((jan4.getUTCDay() || 7) - 1) * DAY + (week - 1) * 7 * DAY;
}
function parseWeek(label) {
  const m = /^(\d{4})-W(\d{2})$/.exec(label || "");
  if (!m) return null;
  const year = Number(m[1]);
  const week = Number(m[2]);
  const t = new Date(mondayUtc(year, week));
  const back = isoParts(t.getUTCFullYear(), t.getUTCMonth(), t.getUTCDate());
  return back.year === year && back.week === week ? { year, week } : null;
}
function shiftWeek(label, delta) {
  const p = parseWeek(label);
  if (!p) return label;
  const t = new Date(mondayUtc(p.year, p.week) + delta * 7 * DAY);
  return weekLabel(isoParts(t.getUTCFullYear(), t.getUTCMonth(), t.getUTCDate()));
}
var digestCount = (items, week) => (items || []).filter((it) => (valueOf(it) ?? 0) >= 2 && weekOfEpoch(it.started_at) === week).length;
var clipSummary = (s) => String(s || "").trim().slice(0, SUMMARY_MAX);
function draftFor(it, value) {
  return {
    topic: it.label && it.label.topic || "",
    value: value ?? valueOf(it),
    summary: it.label ? it.label.summary || "" : clipSummary(it.title),
    loose_end_done: !!it.loose_end_done
  };
}
function canSave(it, d) {
  if (!d.topic || d.value === null || d.value === void 0) return false;
  return !!it.label ? !!d.summary.trim() : true;
}
function putBody(it, d) {
  const body = {};
  const summary = clipSummary(d.summary);
  if (!it.label) {
    body.topic = d.topic;
    body.value = d.value;
    body.summary = summary || clipSummary(it.title);
  } else {
    if (d.topic !== it.label.topic) body.topic = d.topic;
    if (d.value !== it.label.value) body.value = d.value;
    if (summary !== (it.label.summary || "")) body.summary = summary;
  }
  if (d.loose_end_done !== !!it.loose_end_done) body.loose_end_done = d.loose_end_done;
  return Object.keys(body).length ? body : null;
}

// desktop/src/state.js
var api = null;
var $filters = null;
var $sort = null;
var $collapsed = null;
var $week = null;
var $editing = null;
function bind(ctx) {
  api = ctx;
  $filters = atom2(normalizeFilters(ctx.storage.get(STORE.filters, null)));
  $sort = atom2(normalizeSort(ctx.storage.get(STORE.sort, null)));
  $collapsed = atom2(normalizeCollapsed(ctx.storage.get(STORE.collapsed, null)));
  $week = atom2(currentWeek());
  $editing = atom2(null);
}
function unbind() {
  api = null;
  $filters = $sort = $collapsed = $week = $editing = null;
}
var persist = (a, key, next) => {
  const v = typeof next === "function" ? next(a.get()) : next;
  a.set(v);
  api.storage.set(key, v);
};
var setFilters = (next) => persist($filters, STORE.filters, next);
var setSort = (next) => persist($sort, STORE.sort, next);
var setCollapsed = (next) => persist($collapsed, STORE.collapsed, next);

// desktop/src/data.js
var scopeKey = (conn, profile) => [ID, conn, profile];
var sessionsKey = (conn, profile) => [...scopeKey(conn, profile), "sessions"];
var fetchSessions = () => api ? api.rest("/sessions") : Promise.reject(new Error("logbuch not loaded"));
function useSessions() {
  const { conn, profile } = useBackend();
  const q = useLiveQuery({
    queryKey: sessionsKey(conn, profile),
    queryFn: fetchSessions,
    placeholderData: (prev, prevQuery) => prevQuery && prevQuery.queryKey[1] === conn && prevQuery.queryKey[2] === profile ? prev : void 0,
    pollMs: POLL_MS,
    staleTime: STALE_MS
  });
  return { ...q, conn, profile };
}
function useCachedSessions() {
  const { conn, profile } = useBackend();
  return useQuery2({ queryKey: sessionsKey(conn, profile), queryFn: fetchSessions, enabled: false, staleTime: Infinity }).data;
}
async function putLabel(id, body) {
  const key = sessionsKey(host2.state.connectionId.get() ?? "", host2.state.profile.get() ?? "");
  const item = await api.rest(`/labels/${encodeURIComponent(id)}`, { method: "PUT", body });
  queryClient2.setQueryData(key, (old) => old ? { ...old, items: old.items.map((i) => i.id === item.id ? item : i) } : old);
  await queryClient2.invalidateQueries({ queryKey: key.slice(0, 3) });
  return item;
}
async function exportDigest(week) {
  const save2 = captureGatewayFileDownload();
  const out = await api.rest("/digest/file", { method: "POST", body: { week } });
  if (!out || typeof out.path !== "string" || typeof out.name !== "string") throw new Error("digest answer has no path and name");
  await save2(out.path, out.name);
  return out;
}
function openSession(id) {
  void host2.openSession(id);
}
function reveal(paneId, path) {
  if (typeof host2.revealPane === "function") host2.revealPane(paneId);
  else host2.navigate(path);
}

// desktop/src/view.js
import {
  Button,
  Checkbox,
  Codicon,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  EmptyState,
  ErrorState,
  host as host3,
  Input,
  Loader,
  SearchField,
  SegmentedControl,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Tip as Tip2,
  useValue as useValue2
} from "@hermes/plugin-sdk";
import { createElement as h2, Fragment, useMemo, useState } from "react";

// desktop/src/state-icon.js
import { Tip } from "@hermes/plugin-sdk";
import { createElement as h, useSyncExternalStore } from "react";

// desktop/src/icons/line-md.json
var line_md_default = { prefix: "line-md", lastModified: 1767255360, aliases: {}, width: 24, height: 24, icons: { "alert-loop": { body: '<g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path stroke-dasharray="60" d="M12 3l9 17h-18l9 -17Z"><animate fill="freeze" attributeName="stroke-dashoffset" dur="0.6s" values="60;0"/></path><path stroke-dasharray="6" stroke-dashoffset="6" d="M12 10v4"><animate attributeName="stroke-width" begin="0.7s" dur="3s" keyTimes="0;0.1;0.2;0.3;1" repeatCount="indefinite" values="2;3;3;2;2"/><animate fill="freeze" attributeName="stroke-dashoffset" begin="0.7s" dur="0.2s" to="0"/></path><path stroke-dasharray="4" stroke-dashoffset="4" d="M12 17v0.01"><animate fill="freeze" attributeName="stroke-dashoffset" begin="0.7s" dur="0.2s" to="0"/><animate attributeName="stroke-width" begin="1s" dur="3s" keyTimes="0;0.1;0.2;0.3;1" repeatCount="indefinite" values="2;3;3;2;2"/></path></g>' }, "bell-alert-loop": { body: '<g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path stroke-dasharray="4" d="M12 3v2"><animate fill="freeze" attributeName="stroke-dashoffset" dur="0.2s" values="4;0"/><animateTransform attributeName="transform" dur="6s" keyTimes="0;0.05;0.15;0.2;1" repeatCount="indefinite" type="rotate" values="0 12 3;3 12 3;-3 12 3;0 12 3;0 12 3"/></path><path stroke-dasharray="30" stroke-dashoffset="30" d="M12 5c-3.31 0 -6 2.69 -6 6l0 6c-1 0 -2 1 -2 2h8M12 5c3.31 0 6 2.69 6 6l0 6c1 0 2 1 2 2h-8"><animateTransform attributeName="transform" dur="6s" keyTimes="0;0.05;0.15;0.2;1" repeatCount="indefinite" type="rotate" values="0 12 3;3 12 3;-3 12 3;0 12 3;0 12 3"/><animate fill="freeze" attributeName="stroke-dashoffset" begin="0.2s" dur="0.4s" to="0"/></path><path stroke-dasharray="10" stroke-dashoffset="10" d="M10 20c0 1.1 0.9 2 2 2c1.1 0 2 -0.9 2 -2"><animateTransform attributeName="transform" begin="0.2s" dur="6s" keyTimes="0;0.05;0.15;0.2;1" repeatCount="indefinite" type="rotate" values="0 12 8;6 12 8;-6 12 8;0 12 8;0 12 8"/><animate fill="freeze" attributeName="stroke-dashoffset" begin="0.7s" dur="0.2s" to="0"/></path><path stroke-dasharray="6" stroke-dashoffset="6" d="M22 6v4"><animate attributeName="stroke-width" begin="0.9s" dur="3s" keyTimes="0;0.1;0.2;0.3;1" repeatCount="indefinite" values="2;3;3;2;2"/><animate fill="freeze" attributeName="stroke-dashoffset" begin="0.9s" dur="0.2s" to="0"/></path><path stroke-dasharray="4" stroke-dashoffset="4" d="M22 14v0.01"><animate attributeName="stroke-width" begin="1.1s" dur="3s" keyTimes="0;0.1;0.2;0.3;1" repeatCount="indefinite" values="2;3;3;2;2"/><animate fill="freeze" attributeName="stroke-dashoffset" begin="1.1s" dur="0.2s" to="0"/></path></g>' }, "alert-circle-twotone": { body: '<g stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path fill="currentColor" fill-opacity="0" stroke-dasharray="60" d="M12 3c4.97 0 9 4.03 9 9c0 4.97 -4.03 9 -9 9c-4.97 0 -9 -4.03 -9 -9c0 -4.97 4.03 -9 9 -9Z"><animate fill="freeze" attributeName="stroke-dashoffset" dur="0.6s" values="60;0"/><animate fill="freeze" attributeName="fill-opacity" begin="1s" dur="0.15s" to=".3"/></path><g fill="none"><path stroke-dasharray="8" stroke-dashoffset="8" d="M12 7v6"><animate fill="freeze" attributeName="stroke-dashoffset" begin="0.7s" dur="0.2s" to="0"/></path><path stroke-dasharray="4" stroke-dashoffset="4" d="M12 17v0.01"><animate fill="freeze" attributeName="stroke-dashoffset" begin="0.7s" dur="0.2s" to="0"/></path></g></g>' }, "upload-twotone": { body: '<g stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path fill="currentColor" fill-opacity="0" stroke-dasharray="20" d="M12 15h2v-6h2.5l-4.5 -4.5M12 15h-2v-6h-2.5l4.5 -4.5"><animate fill="freeze" attributeName="stroke-dashoffset" dur="0.5s" values="20;0"/><animate fill="freeze" attributeName="fill-opacity" begin="0.7s" dur="0.15s" to=".3"/></path><path fill="none" stroke-dasharray="14" stroke-dashoffset="14" d="M6 19h12"><animate fill="freeze" attributeName="stroke-dashoffset" begin="0.5s" dur="0.2s" to="0"/></path></g>' }, "clipboard-list-twotone": { body: '<path fill="currentColor" fill-opacity="0" d="M6 4h4v2h4v-2h4v16h-12v-16Z"><animate fill="freeze" attributeName="fill-opacity" begin="1.5s" dur="0.15s" to=".3"/></path><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path stroke-dasharray="66" stroke-width="2" d="M12 3h7v18h-14v-18h7Z"><animate fill="freeze" attributeName="stroke-dashoffset" dur="0.6s" values="66;0"/></path><path stroke-dasharray="14" stroke-dashoffset="14" d="M14.5 3.5v3h-5v-3"><animate fill="freeze" attributeName="stroke-dashoffset" begin="0.7s" dur="0.2s" to="0"/></path><g stroke-width="2"><path stroke-dasharray="6" stroke-dashoffset="6" d="M9 10h3"><animate fill="freeze" attributeName="stroke-dashoffset" begin="0.9s" dur="0.2s" to="0"/></path><g stroke-dasharray="8" stroke-dashoffset="8"><path d="M9 13h5"><animate fill="freeze" attributeName="stroke-dashoffset" begin="1.1s" dur="0.2s" to="0"/></path><path d="M9 16h6"><animate fill="freeze" attributeName="stroke-dashoffset" begin="1.3s" dur="0.2s" to="0"/></path></g></g></g>' }, "confirm-circle-twotone": { body: '<g stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path fill="currentColor" fill-opacity="0" stroke-dasharray="60" d="M3 12c0 -4.97 4.03 -9 9 -9c4.97 0 9 4.03 9 9c0 4.97 -4.03 9 -9 9c-4.97 0 -9 -4.03 -9 -9Z"><animate fill="freeze" attributeName="stroke-dashoffset" dur="0.6s" values="60;0"/><animate fill="freeze" attributeName="fill-opacity" begin="0.6s" dur="0.15s" to=".3"/></path><path fill="none" stroke-dasharray="14" stroke-dashoffset="14" d="M8 12l3 3l5 -5"><animate fill="freeze" attributeName="stroke-dashoffset" begin="0.85s" dur="0.2s" to="0"/></path></g>' }, circle: { body: '<path fill="none" stroke="currentColor" stroke-dasharray="60" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12c0 -4.97 4.03 -9 9 -9c4.97 0 9 4.03 9 9c0 4.97 -4.03 9 -9 9c-4.97 0 -9 -4.03 -9 -9Z"><animate fill="freeze" attributeName="stroke-dashoffset" dur="0.6s" values="60;0"/></path>' } } };

// desktop/src/icons.js
var ANIM = /<(animate|animateTransform|set)\b[^>]*?\/>/g;
var ELEMENT = /<([a-zA-Z]+)\b([^>]*?)(\/?)>((?:\s*<(?:animate|animateTransform|set)\b[^>]*?\/>)+)\s*<\/\1>/g;
var ATTR = /([a-zA-Z:-]+)="([^"]*)"/g;
var attrsOf = (text) => {
  const out = /* @__PURE__ */ new Map();
  for (const m of text.matchAll(ATTR)) out.set(m[1], m[2]);
  return out;
};
var endValue = (a) => {
  if (a.get("fill") !== "freeze" || !a.get("attributeName")) return null;
  if (a.has("to")) return a.get("to");
  return a.has("values") ? a.get("values").split(";").pop().trim() : null;
};
function staticBody(body) {
  const frozen = body.replace(ELEMENT, (_all, tag, own, _close, kids) => {
    const attrs = attrsOf(own);
    for (const k of kids.matchAll(ANIM)) {
      const a = attrsOf(k[0]);
      const end = endValue(a);
      if (end !== null) attrs.set(a.get("attributeName"), end);
    }
    return `<${tag} ${[...attrs].map(([n, v]) => `${n}="${v}"`).join(" ")}/>`;
  });
  return frozen.replace(ANIM, "").replace(/ stroke-dashoffset="(?!0")[^"]*"/g, "");
}
var cache = /* @__PURE__ */ new Map();
function iconBody(name, animated) {
  const icon = line_md_default.icons[name];
  if (!icon) return "";
  if (animated) return icon.body;
  if (!cache.has(name)) cache.set(name, staticBody(icon.body));
  return cache.get(name);
}
var iconBox = (name) => {
  const icon = line_md_default.icons[name] || {};
  return `0 0 ${icon.width || line_md_default.width || 24} ${icon.height || line_md_default.height || 24}`;
};

// desktop/src/state-icon.js
var QUERY = "(prefers-reduced-motion: reduce)";
var query = () => typeof window !== "undefined" && window.matchMedia ? window.matchMedia(QUERY) : null;
function subscribe(onChange) {
  const mq = query();
  if (!mq) return () => {
  };
  mq.addEventListener("change", onChange);
  return () => mq.removeEventListener("change", onChange);
}
var useReducedMotion = () => useSyncExternalStore(subscribe, () => !!(query() && query().matches), () => false);
function StateIcon({ state, tip, still }) {
  const reduced = useReducedMotion();
  const row = STATES.find((s) => s[0] === state) || STATES[STATES.length - 1];
  const moving = row[3] && !still && !reduced;
  const span = h("span", {
    className: `lb-st lb-c-${row[0]}`,
    "data-state": row[0],
    "data-moving": String(moving),
    role: "img",
    "aria-label": tip || row[1]
  }, h("svg", {
    viewBox: iconBox(row[2]),
    focusable: "false",
    "aria-hidden": "true",
    dangerouslySetInnerHTML: { __html: iconBody(row[2], moving) }
  }));
  return tip ? h(Tip, { label: tip }, span) : span;
}

// desktop/src/view.js
var stop = (e) => e.stopPropagation();
var plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
var say = (kind, message) => host3.notify({ kind, message });
var fail = (what, e) => say("error", `Logbuch: ${what} failed: ${e && e.message || e}`);
async function save(it, body) {
  try {
    await putLabel(it.id, body);
  } catch (e) {
    fail("saving the label", e);
  }
}
function RowMenu({ it }) {
  const labelled = !!it.label;
  const pickValue = (v) => labelled ? save(it, { value: v }) : $editing.set({ id: it.id, value: v });
  return h2(
    DropdownMenu,
    null,
    h2(
      DropdownMenuTrigger,
      { asChild: true },
      h2(
        Button,
        { size: "icon-xs", variant: "ghost", className: "lb-menu", "aria-label": "Row actions", "data-menu": it.id, onClick: stop },
        h2(Codicon, { name: "ellipsis" })
      )
    ),
    h2(
      DropdownMenuContent,
      { align: "end", onClick: stop },
      VALUES.map(([v, label, name]) => h2(
        DropdownMenuItem,
        { key: v, "data-set-value": v, onSelect: () => pickValue(v) },
        valueOf(it) === v ? h2(Codicon, { name: "check" }) : h2("span", { style: { display: "inline-block", width: "1em" } }),
        `${label} (${name.toLowerCase()})`
      )),
      h2(DropdownMenuSeparator, null),
      h2(
        DropdownMenuItem,
        { "data-edit": "1", onSelect: () => $editing.set({ id: it.id }) },
        h2(Codicon, { name: "edit" }),
        "Edit topic and summary"
      ),
      it.loose_end ? h2(
        DropdownMenuItem,
        { "data-loose-toggle": "1", onSelect: () => save(it, { loose_end_done: !it.loose_end_done }) },
        h2(Codicon, { name: it.loose_end_done ? "circle-large-outline" : "pass" }),
        it.loose_end_done ? "Reopen loose end" : "Mark loose end done"
      ) : null
    )
  );
}
function Row({ it, wide }) {
  const v = bucket(it);
  const text = summaryOf(it);
  const open = () => openSession(it.id);
  return h2(
    "div",
    {
      className: `lb-row v${v}`,
      "data-id": it.id,
      role: "button",
      tabIndex: 0,
      onClick: open,
      onKeyDown: (e) => {
        if (e.target === e.currentTarget && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          open();
        }
      }
    },
    h2(
      "div",
      { className: "lb-l1" },
      h2(
        "span",
        { className: `lb-pri v${v}`, "data-pri": it.label ? VALUE_LABEL[v] : "?", title: it.label ? void 0 : "Not labelled yet" },
        it.label ? VALUE_LABEL[v] : "?"
      ),
      h2(StateIcon, { state: stateOf(it), tip: stateTip(it) }),
      h2("span", { className: "lb-sum", title: text }, text),
      h2(RowMenu, { it })
    ),
    wide ? h2("div", { className: "lb-l2" }, h2("span", { className: "lb-ttl", title: it.title }, it.title || "(untitled)")) : null,
    h2(
      "div",
      { className: "lb-l2" },
      h2("span", null, fmtDate(it.started_at)),
      h2("span", null, h2("b", null, it.commit_calls ?? 0), " commit calls"),
      h2("span", null, h2("b", null, it.mr_calls ?? 0), " MR calls"),
      wide ? h2("span", null, h2("b", null, it.turns ?? 0), " turns") : null,
      wide ? h2("span", null, h2("b", null, it.tool_calls ?? 0), " tool calls") : null,
      isLoose(it) ? h2("span", { className: "lb-loose" }, "loose end") : null,
      wide ? h2("code", { className: "lb-id" }, it.id) : null
    )
  );
}
function Group({ g, wide, collapsed }) {
  const closed = !!collapsed[g.key];
  const flip = () => setCollapsed((cur) => {
    const next = { ...cur };
    if (next[g.key]) delete next[g.key];
    else next[g.key] = true;
    return next;
  });
  return h2(
    "div",
    { className: "lb-grp", "data-k": g.key },
    h2(
      "button",
      { type: "button", className: "lb-gh", "aria-expanded": !closed, onClick: flip },
      h2(Codicon, { name: closed ? "chevron-right" : "chevron-down", className: "lb-caret", size: "0.8rem" }),
      h2("span", { className: "lb-gname" }, g.name),
      h2(
        "span",
        { className: "lb-gmeta" },
        `${plural(g.items.length, "session", "sessions")}, ${g.p1} P1, ${g.commit_calls} commit calls, ${g.mr_calls} MR calls`
      )
    ),
    closed ? null : g.items.map((it) => h2(Row, { key: it.id, it, wide }))
  );
}
function EditForm({ it, topics, start }) {
  const [d, setD] = useState(() => draftFor(it, start));
  const [busy, setBusy] = useState(false);
  const close = () => $editing.set(null);
  const submit = async () => {
    const body = putBody(it, d);
    if (!body) return close();
    setBusy(true);
    try {
      await putLabel(it.id, body);
      close();
    } catch (e) {
      fail("saving the label", e);
      setBusy(false);
    }
  };
  return h2(
    Dialog,
    { open: true, onOpenChange: (o) => {
      if (!o) close();
    } },
    h2(
      DialogContent,
      null,
      h2(
        DialogHeader,
        null,
        h2(DialogTitle, null, "Edit label"),
        h2(DialogDescription, null, "A label you save here is manual: automatic labelling never overwrites it.")
      ),
      h2(
        "div",
        { className: "lb-form" },
        h2(
          "label",
          null,
          "Topic",
          h2(
            Select,
            { value: d.topic || void 0, onValueChange: (topic) => setD({ ...d, topic }) },
            h2(SelectTrigger, { "aria-label": "Topic", "data-field": "topic" }, h2(SelectValue, { placeholder: "Choose a topic" })),
            h2(SelectContent, null, Object.entries(topics).map(([k, name]) => h2(SelectItem, { key: k, value: k }, name)))
          )
        ),
        h2(
          "label",
          null,
          "Value",
          h2(SegmentedControl, {
            options: VALUES.map(([v, label]) => ({ id: String(v), label })),
            value: d.value === null || d.value === void 0 ? "" : String(d.value),
            onChange: (id) => setD({ ...d, value: Number(id) })
          })
        ),
        h2(
          "label",
          null,
          `Summary (${d.summary.length}/${SUMMARY_MAX})`,
          h2(Input, { value: d.summary, maxLength: SUMMARY_MAX, "aria-label": "Summary", "data-field": "summary", onChange: (e) => setD({ ...d, summary: e.target.value }) })
        ),
        it.loose_end ? h2(
          "label",
          { className: "lb-inline" },
          h2(Checkbox, { checked: d.loose_end_done, "data-field": "loose", onCheckedChange: (c) => setD({ ...d, loose_end_done: c === true }) }),
          "Loose end done"
        ) : null
      ),
      h2(
        DialogFooter,
        null,
        h2(Button, { variant: "ghost", size: "sm", onClick: close, "data-cancel": "1" }, "Cancel"),
        h2(Button, { size: "sm", disabled: busy || !canSave(it, d), onClick: submit, "data-save": "1" }, "Save")
      )
    )
  );
}
function EditDialog({ items, topics }) {
  const editing = useValue2($editing);
  const it = editing && items.find((i) => i.id === editing.id);
  if (!it) return null;
  return h2(EditForm, { key: `${it.id}:${editing.value ?? ""}`, it, topics, start: editing.value });
}
function DigestControl({ items }) {
  const week = useValue2($week);
  const [busy, setBusy] = useState(false);
  const count = digestCount(items, week);
  const run = async () => {
    setBusy(true);
    try {
      await exportDigest(week);
    } catch (e) {
      fail("writing the digest", e);
    } finally {
      setBusy(false);
    }
  };
  return h2(
    "span",
    { className: "lb-wk", "data-digest": week },
    h2(
      Button,
      { size: "icon-xs", variant: "ghost", "aria-label": "Previous week", "data-week": "prev", onClick: () => $week.set(shiftWeek($week.get(), -1)) },
      h2(Codicon, { name: "chevron-left" })
    ),
    h2("code", { "data-week-label": "1" }, week),
    h2(
      Button,
      { size: "icon-xs", variant: "ghost", "aria-label": "Next week", "data-week": "next", disabled: week >= currentWeek(), onClick: () => $week.set(shiftWeek($week.get(), 1)) },
      h2(Codicon, { name: "chevron-right" })
    ),
    h2(
      Tip2,
      { label: `Save the ${plural(count, "P1 or P2 session", "P1 and P2 sessions")} of ${week} as a Markdown digest` },
      h2(
        Button,
        { size: "xs", variant: "outline", disabled: busy, onClick: run, "data-digest-button": "1" },
        h2(Codicon, { name: "cloud-download" }),
        "Digest"
      )
    )
  );
}
function FilterBars({ groups, counts }) {
  const f = useValue2($filters);
  const sort = useValue2($sort);
  const collapsed = useValue2($collapsed);
  const anyOpen = groups.some((g) => !collapsed[g.key]);
  const setAll = () => setCollapsed((cur) => {
    const next = { ...cur };
    for (const g of groups) if (anyOpen) next[g.key] = true;
    else delete next[g.key];
    return next;
  });
  return [
    h2(
      "div",
      { key: "chips", className: "lb-bar", "data-bar": "chips" },
      VALUES.map(([v, label, name]) => h2("button", {
        key: v,
        type: "button",
        className: `lb-chip v${v}`,
        "data-v": v,
        title: name,
        "aria-pressed": !!f.vals[v],
        onClick: () => setFilters((cur) => ({ ...cur, vals: { ...cur.vals, [v]: !cur.vals[v] } }))
      }, label)),
      h2("button", {
        type: "button",
        className: "lb-chip lo",
        "data-loose": "1",
        "aria-pressed": f.loose,
        onClick: () => setFilters((cur) => ({ ...cur, loose: !cur.loose }))
      }, "Loose ends")
    ),
    h2(
      "div",
      { key: "states", className: "lb-bar lb-states", "data-bar": "states" },
      STATES.map(([id, name, , , blurb]) => h2("button", {
        key: id,
        type: "button",
        className: `lb-chip sc lb-c-${id}`,
        "data-st": id,
        title: blurb,
        "aria-pressed": !!f.states[id],
        onClick: () => setFilters((cur) => ({ ...cur, states: { ...cur.states, [id]: !(cur.states || {})[id] } }))
      }, h2(StateIcon, { state: id, still: true }), name, h2("span", { className: "lb-n", "data-n": id }, counts[id])))
    ),
    h2(
      "div",
      { key: "search", className: "lb-bar", "data-bar": "search" },
      h2(
        "div",
        { className: "lb-search" },
        h2(SearchField, { placeholder: "Search summary, title, id", value: f.q, onChange: (q) => setFilters((cur) => ({ ...cur, q })) })
      ),
      h2(
        Tip2,
        { label: "Sort order, click to change" },
        h2(
          Button,
          { size: "xs", variant: "ghost", "data-sort": sort, onClick: () => setSort(nextSort) },
          h2(Codicon, { name: "sort-precedence" }),
          SORTS.find((s) => s.id === sort).label
        )
      ),
      h2(
        Tip2,
        { label: anyOpen ? "Collapse all topics" : "Expand all topics" },
        h2(
          Button,
          { size: "icon-xs", variant: "ghost", "aria-label": "Collapse or expand all", "data-collapse-all": "1", onClick: setAll },
          h2(Codicon, { name: anyOpen ? "collapse-all" : "expand-all" })
        )
      )
    )
  ];
}
function Unreachable({ error, conn, profile }) {
  const where = `backend ${conn || "this device"}, profile ${profile || "default"}`;
  const hint = /404|not found/i.test(String(error && error.message || error)) ? " A 404 means that backend does not have the logbuch plugin." : " The Python half loads only when logbuch is in plugins.enabled of that profile and the backend was restarted.";
  return h2(ErrorState, { title: `Logbuch backend unreachable (${where})`, description: `${error && error.message || error}.${hint}` });
}
function Body({ q, wide }) {
  const { data, error, isLoading, conn, profile } = q;
  const f = useValue2($filters);
  const sort = useValue2($sort);
  const collapsed = useValue2($collapsed);
  const topics = data && data.topics || {};
  const shown = useMemo(() => data ? filterItems(data.items, topics, f) : [], [data, f]);
  const groups = useMemo(() => groupItems(shown, topics, sort), [shown, sort, data]);
  const counts = useMemo(() => stateCounts(data ? filterBase(data.items, topics, f) : []), [data, f]);
  const s = summarize(shown);
  if (error && !data) return h2("div", { className: "lb-scroll" }, h2(Unreachable, { error, conn, profile }));
  if (isLoading || !data) return h2("div", { className: "lb-empty" }, h2(Loader, null));
  const empty = !data.items.length;
  return h2(
    Fragment,
    null,
    wide ? null : h2("div", { className: "lb-sub", "data-sub": "1" }, `profile ${data.profile || profile}, updated ${fmtTime(data.generated_at)}`),
    data.schema_ok === false ? h2(
      "div",
      { className: "lb-banner", "data-banner": "schema" },
      "The sessions database does not have every column Logbuch reads (schema_ok is false). Counts fall back to session level; labels still work."
    ) : null,
    error ? h2("div", { className: "lb-banner bad", "data-banner": "stale" }, `Backend unreachable (${conn || "this device"}, profile ${profile || "default"}), showing the last answer.`) : null,
    empty ? null : h2(FilterBars, { groups, counts }),
    empty ? null : h2(
      "div",
      { className: "lb-stats", "data-stats": "1" },
      `${plural(s.count, "session", "sessions")} in ${plural(s.topics, "topic", "topics")}: ${s.byValue[3]} P1, ${s.byValue[2]} P2, ${s.byValue[1]} P3, ${s.byValue[0]} none. ${s.commit_calls} commit calls, ${s.mr_calls} MR calls. ${plural(s.loose, "loose end", "loose ends")}.`
    ),
    h2(
      "div",
      { className: "lb-scroll", "data-list": "1" },
      empty ? h2(
        "div",
        { className: "lb-empty", "data-empty": "none" },
        h2(
          "div",
          null,
          h2(EmptyState, { title: "No sessions with real work yet", description: "Logbuch lists desktop and CLI sessions of this profile with at least 20 tool calls and an edit, commit call, MR call or card." }),
          h2("div", { className: "lb-note" }, HIDE_NOTE)
        )
      ) : !groups.length ? h2(
        "div",
        { className: "lb-empty", "data-empty": "filtered" },
        h2(
          "div",
          null,
          h2(EmptyState, { title: "No session matches these filters" }),
          h2(Button, { size: "xs", variant: "outline", "data-reset": "1", onClick: () => setFilters({ vals: { 3: true, 2: true, 1: true, 0: true }, loose: false, q: "", states: {} }) }, "Show every session")
        )
      ) : groups.map((g) => h2(Group, { key: g.key, g, wide, collapsed })),
      wide && !empty ? h2(
        "div",
        { className: "lb-legend" },
        "P1: production fix or colleague request delivered. P2: team enablement, or a decision on company systems. P3: indirect. none: personal. Loose end: the last reply left a decision, a merge or a retry open. Priority is business value, then shipped output (commit calls plus MR calls)."
      ) : null,
      wide && !empty ? h2(
        "div",
        { className: "lb-legend lb-states-legend", "data-legend": "states" },
        STATES.map(([id, name, , , blurb]) => h2("div", { key: id, className: "lb-lg", "data-lg": id }, h2(StateIcon, { state: id, still: true }), h2("b", null, name), ` ${blurb}.`))
      ) : null
    ),
    h2(EditDialog, { items: data.items, topics })
  );
}
function Refresh({ q }) {
  return h2(
    Tip2,
    { label: "Refresh now" },
    h2(
      Button,
      { size: "icon-xs", variant: "ghost", "aria-label": "Refresh", "data-refresh": "1", disabled: q.isFetching, onClick: () => void q.refetch() },
      h2(Codicon, { name: "refresh", spinning: q.isFetching })
    )
  );
}
function LogbuchPane() {
  const q = useSessions();
  return h2(
    "div",
    { className: "lb pane", "data-lb": "pane" },
    h2(
      "div",
      { className: "lb-head" },
      h2("span", { className: "lb-title lb-grow" }, "Logbuch"),
      h2(
        Tip2,
        { label: "Open the full page" },
        h2(Button, { size: "xs", variant: "ghost", "data-open-page": "1", onClick: () => host3.navigate(PATH) }, h2(Codicon, { name: "link-external" }), "Page")
      ),
      h2(Refresh, { q })
    ),
    h2(Body, { q, wide: false }),
    h2("div", { className: "lb-bar lb-foot", "data-bar": "digest" }, h2(DigestControl, { items: q.data && q.data.items || [] }))
  );
}
function LogbuchPage() {
  const q = useSessions();
  const data = q.data;
  return h2(
    "div",
    { className: "lb wide", "data-lb": "page" },
    h2(
      "div",
      { className: "lb-head" },
      h2("span", { className: "lb-title lb-grow" }, "Sessions by business value"),
      h2(DigestControl, { items: data && data.items || [] }),
      h2(
        Tip2,
        { label: "Show the Logbuch tab in the Files zone" },
        h2(Button, { size: "xs", variant: "ghost", "data-show-pane": "1", onClick: () => reveal(PANE_ID, PATH) }, h2(Codicon, { name: "layout-sidebar-right" }), "Pane")
      ),
      h2(Refresh, { q })
    ),
    data ? h2(
      "div",
      { className: "lb-sub", "data-sub": "1" },
      `${plural(data.items.length, "session", "sessions")} with real work, profile ${data.profile || q.profile}, grouped by topic, updated ${fmtTime(data.generated_at)}.`
    ) : null,
    h2(Body, { q, wide: true })
  );
}
function RowBadge({ sessionId }) {
  const data = useCachedSessions();
  const index = useMemo(() => badgeIndex(data && data.items), [data]);
  const states = useMemo(() => badgeStates(data && data.items), [data]);
  const label = badgeFor(index, sessionId);
  if (!label) return null;
  const st = states.get(sessionId) || { state: "none", tip: stateTip({}) };
  const critical = st.state === "critical";
  return h2(
    Tip2,
    { label: `Logbuch ${label}, ${st.tip}` },
    h2(
      "span",
      { className: `lb-badge ${label.toLowerCase()}${critical ? " critical" : ""}`, "data-badge": label, "data-state": st.state },
      st.state === "none" ? null : h2(StateIcon, { state: st.state }),
      label
    )
  );
}

// desktop/src/index.js
var index_default = {
  id: ID,
  name: "Logbuch",
  description: "Real-work sessions ranked by business value: a tab stacked with Files, a full page, value badges in the sidebar and a weekly Markdown digest.",
  register(ctx) {
    bind(ctx);
    const unmountStyle = mountStyle(ID, CSS);
    ctx.onDispose(() => {
      unmountStyle();
      unbind();
    });
    const show = () => reveal(PANE_ID, PATH);
    ctx.registerMany([
      {
        id: "pane",
        area: PANES_AREA,
        title: "Logbuch",
        data: PANE_DATA,
        render: () => h3(LogbuchPane)
      },
      { id: "page", area: ROUTES_AREA, data: { path: PATH }, render: () => h3(LogbuchPage) },
      { id: "nav", area: SIDEBAR_NAV_AREA, order: NAV_ORDER, data: NAV_DATA },
      { id: "keybind", area: KEYBINDS_AREA, data: { id: ACTION_ID, label: "Show Logbuch", defaults: [KEYBIND], run: show } },
      {
        id: "palette",
        area: PALETTE_AREA,
        data: { id: ACTION_ID, action: ACTION_ID, label: "Show Logbuch", keywords: ["logbuch", "sessions", "value", "digest", "log"], run: show }
      },
      { id: "badge", area: SESSION_ROW_AREAS.trailing, data: { render: ({ sessionId }) => h3(RowBadge, { sessionId }) } }
    ]);
  }
};
export {
  index_default as default
};
