// Pure logic (no SDK, React or DOM) so tests/desktop.test.mjs runs it in plain node.

import { DEFAULT_FILTERS, SORTS, STATE_IDS, STATES, SUMMARY_MAX, UNLABELLED, UNLABELLED_NAME, VALUES } from './model.js'

const num = n => (Number.isFinite(n) ? n : 0)

// Business value 0-3, or null while the backend has not labelled the item.
export const valueOf = it => (it.label && Number.isInteger(it.label.value) ? it.label.value : null)
// Filter and score bucket: an unlabelled item counts as "none".
export const bucket = it => valueOf(it) ?? 0
const topicKey = it => (it.label && it.label.topic) || UNLABELLED
const topicName = (topics, key) => (key === UNLABELLED ? UNLABELLED_NAME : (topics && topics[key]) || key)
export const summaryOf = it => (it.label && it.label.summary) || it.title || '(untitled)'
export const shipped = it => num(it.commit_calls) + num(it.mr_calls)
export const isLoose = it => !!it.loose_end && !it.loose_end_done

// D47 state of an item. An unknown or missing state (an older backend) reads as "none".
export const stateOf = it => (STATE_IDS.includes(it.state) ? it.state : 'none')
export const evidenceOf = it => (typeof it.state_evidence === 'string' && it.state_evidence ? it.state_evidence : null)
export const stateTip = it => {
  const row = STATES.find(s => s[0] === stateOf(it)) || STATES[STATES.length - 1]
  return `${row[1]}: ${evidenceOf(it) || row[4]}`
}

// build-value-page.py: value * 100 + min(commit and MR calls, 60) + min(edits, 40) / 10.
export const scoreOf = it => bucket(it) * 100 + Math.min(shipped(it), 60) + Math.min(num(it.edits), 40) / 10

export function normalizeFilters(raw) {
  const vals = { ...DEFAULT_FILTERS.vals }
  if (raw && typeof raw === 'object' && raw.vals && typeof raw.vals === 'object') {
    for (const [v] of VALUES) if (v in raw.vals) vals[v] = !!raw.vals[v]
  }
  const states = {}
  if (raw && typeof raw === 'object' && raw.states && typeof raw.states === 'object') {
    for (const id of STATE_IDS) if (raw.states[id] === true) states[id] = true
  }
  return { vals, loose: !!(raw && raw.loose), q: raw && typeof raw.q === 'string' ? raw.q : '', states }
}
export const normalizeSort = raw => (SORTS.some(s => s.id === raw) ? raw : 'score')
export function normalizeCollapsed(raw) {
  const out = {}
  if (raw && typeof raw === 'object') for (const k of Object.keys(raw)) if (raw[k] === true) out[k] = true
  return out
}
export const nextSort = cur => SORTS[(SORTS.findIndex(s => s.id === cur) + 1) % SORTS.length].id

// Items that pass value, loose-end and search; the state chips count over this set.
export function filterBase(items, topics, f) {
  const q = f.q.trim().toLowerCase()
  return items.filter(it => {
    if (!f.vals[bucket(it)]) return false
    if (f.loose && !isLoose(it)) return false
    if (!q) return true
    return `${summaryOf(it)} ${it.title || ''} ${it.id} ${topicName(topics, topicKey(it))}`.toLowerCase().includes(q)
  })
}

// No state chip pressed means every state; pressed chips are an OR.
export const anyState = f => STATE_IDS.some(id => f.states && f.states[id])
export function filterItems(items, topics, f) {
  const base = filterBase(items, topics, f)
  return anyState(f) ? base.filter(it => f.states[stateOf(it)]) : base
}
export function stateCounts(items) {
  const out = Object.fromEntries(STATE_IDS.map(id => [id, 0]))
  for (const it of items) out[stateOf(it)]++
  return out
}

const newer = (a, b) => num(b.started_at) - num(a.started_at)
const byId = (a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0)
export function sortItems(items, sort) {
  const cmp =
    sort === 'date'
      ? (a, b) => newer(a, b) || byId(a, b)
      : sort === 'ship'
        ? (a, b) => shipped(b) - shipped(a) || scoreOf(b) - scoreOf(a) || newer(a, b) || byId(a, b)
        : (a, b) => scoreOf(b) - scoreOf(a) || newer(a, b) || byId(a, b)
  return [...items].sort(cmp)
}

// Topic groups, strongest first (sum of scores), items sorted inside each group.
export function groupItems(items, topics, sort) {
  const by = new Map()
  for (const it of items) {
    const k = topicKey(it)
    if (!by.has(k)) by.set(k, [])
    by.get(k).push(it)
  }
  const groups = [...by].map(([key, list]) => {
    const rows = sortItems(list, sort)
    return {
      key,
      name: topicName(topics, key),
      items: rows,
      p1: rows.filter(i => valueOf(i) === 3).length,
      commit_calls: rows.reduce((t, i) => t + num(i.commit_calls), 0),
      mr_calls: rows.reduce((t, i) => t + num(i.mr_calls), 0),
      score: rows.reduce((t, i) => t + scoreOf(i), 0)
    }
  })
  return groups.sort((a, b) => b.score - a.score || (a.name < b.name ? -1 : a.name > b.name ? 1 : 0))
}

export function summarize(items) {
  const byValue = { 3: 0, 2: 0, 1: 0, 0: 0 }
  let commit_calls = 0
  let mr_calls = 0
  let loose = 0
  const topics = new Set()
  for (const it of items) {
    byValue[bucket(it)]++
    commit_calls += num(it.commit_calls)
    mr_calls += num(it.mr_calls)
    if (isLoose(it)) loose++
    topics.add(topicKey(it))
  }
  return { count: items.length, topics: topics.size, byValue, commit_calls, mr_calls, loose }
}

// id -> 'P1' | 'P2' for labelled value 3 and 2 only. Everything else has no entry.
export function badgeIndex(items) {
  const m = new Map()
  for (const it of items || []) {
    const v = valueOf(it)
    if (v === 3) m.set(it.id, 'P1')
    else if (v === 2) m.set(it.id, 'P2')
  }
  return m
}
export const badgeFor = (index, id) => (index && index.get(id)) || null
// id -> { state, evidence } for the same P1 and P2 items: the badge's icon, and red when critical.
export function badgeStates(items) {
  const m = new Map()
  for (const it of items || []) {
    const v = valueOf(it)
    if (v === 3 || v === 2) m.set(it.id, { state: stateOf(it), evidence: evidenceOf(it), tip: stateTip(it) })
  }
  return m
}

const pad2 = n => String(n).padStart(2, '0')
const DAY = 86_400_000

export function fmtDate(sec) {
  const d = new Date(num(sec) * 1000)
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`
}
export function fmtTime(sec) {
  const d = new Date(num(sec) * 1000)
  return `${pad2(d.getHours())}:${pad2(d.getMinutes())}`
}

function isoParts(y, m, d) {
  const t = new Date(Date.UTC(y, m, d))
  t.setUTCDate(t.getUTCDate() + 4 - (t.getUTCDay() || 7))
  const year = t.getUTCFullYear()
  return { year, week: Math.ceil(((t - Date.UTC(year, 0, 1)) / DAY + 1) / 7) }
}
const weekLabel = ({ year, week }) => `${year}-W${pad2(week)}`
const weekOfDate = d => weekLabel(isoParts(d.getFullYear(), d.getMonth(), d.getDate()))
export const weekOfEpoch = sec => weekOfDate(new Date(num(sec) * 1000))
export const currentWeek = (now = new Date()) => weekOfDate(now)

function mondayUtc(year, week) {
  const jan4 = new Date(Date.UTC(year, 0, 4))
  return jan4.getTime() - ((jan4.getUTCDay() || 7) - 1) * DAY + (week - 1) * 7 * DAY
}
// A week label that exists (2026-W53 does not), else null.
export function parseWeek(label) {
  const m = /^(\d{4})-W(\d{2})$/.exec(label || '')
  if (!m) return null
  const year = Number(m[1])
  const week = Number(m[2])
  const t = new Date(mondayUtc(year, week))
  const back = isoParts(t.getUTCFullYear(), t.getUTCMonth(), t.getUTCDate())
  return back.year === year && back.week === week ? { year, week } : null
}
export function shiftWeek(label, delta) {
  const p = parseWeek(label)
  if (!p) return label
  const t = new Date(mondayUtc(p.year, p.week) + delta * 7 * DAY)
  return weekLabel(isoParts(t.getUTCFullYear(), t.getUTCMonth(), t.getUTCDate()))
}
// P1 and P2 items that started in `week`: what the digest of that week lists.
export const digestCount = (items, week) =>
  (items || []).filter(it => (valueOf(it) ?? 0) >= 2 && weekOfEpoch(it.started_at) === week).length

export const clipSummary = s => String(s || '').trim().slice(0, SUMMARY_MAX)

// The dialog's starting values. `value` overrides the stored one (a menu entry picked a value).
export function draftFor(it, value) {
  return {
    topic: (it.label && it.label.topic) || '',
    value: value ?? valueOf(it),
    summary: it.label ? it.label.summary || '' : clipSummary(it.title),
    loose_end_done: !!it.loose_end_done
  }
}

// The backend answers 422 without a topic and a value; only an unlabelled item may leave the summary empty (the title stands in).
export function canSave(it, d) {
  if (!d.topic || d.value === null || d.value === undefined) return false
  return !!it.label ? !!d.summary.trim() : true
}

// PUT /labels/{id} body: changed fields only on a labelled item (the backend merges), a full label otherwise; null if unchanged.
export function putBody(it, d) {
  const body = {}
  const summary = clipSummary(d.summary)
  if (!it.label) {
    body.topic = d.topic
    body.value = d.value
    body.summary = summary || clipSummary(it.title)
  } else {
    if (d.topic !== it.label.topic) body.topic = d.topic
    if (d.value !== it.label.value) body.value = d.value
    if (summary !== (it.label.summary || '')) body.summary = summary
  }
  if (d.loose_end_done !== !!it.loose_end_done) body.loose_end_done = d.loose_end_done
  return Object.keys(body).length ? body : null
}
