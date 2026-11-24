// SDK-free desktop modules on synthetic data, plus three source rules: no composer.submit, no "commits" wording, ASCII punctuation.
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { existsSync, readdirSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { CSS } from '../desktop/src/css.js'
import { ICON_SET, iconBody, staticBody } from '../desktop/src/icons.js'
import {
  anyState, badgeFor, badgeIndex, badgeStates, bucket, canSave, clipSummary, currentWeek, digestCount, draftFor, evidenceOf,
  filterBase, filterItems, fmtDate, groupItems, isLoose, nextSort, normalizeCollapsed, normalizeFilters, normalizeSort, parseWeek,
  putBody, scoreOf, shiftWeek, sortItems, stateCounts, stateOf, stateTip, summarize, summaryOf, weekOfEpoch
} from '../desktop/src/logic.js'
import {
  ACTION_ID, DEFAULT_FILTERS, HIDE_NOTE, KEYBIND, NAV_DATA, NAV_ORDER, PANE_DATA, PANE_ID, PATH, POLL_MS, STATES, STATE_IDS, UNLABELLED
} from '../desktop/src/model.js'

const here = dirname(fileURLToPath(import.meta.url))
const srcDir = join(here, '..', 'desktop', 'src')

const TOPICS = { INFRA: 'Infrastructure and deployments', SHOP: 'Storefront and checkout', PERSONAL: 'Personal and miscellaneous' }
const mk = (id, over = {}) => ({
  id, title: `title ${id}`, started_at: 1_000_000, last_active_at: 1_000_100, turns: 3, tool_calls: 25, edits: 0,
  commit_calls: 0, mr_calls: 0, loose_end: false, loose_end_done: false,
  label: { topic: 'INFRA', value: 2, summary: `summary ${id}`, source: 'manual' }, ...over
})
const lab = (topic, value, summary = 'x') => ({ topic, value, summary, source: 'rule' })

let n = 0
let failed = 0
function t(name, fn) {
  n++
  try {
    fn()
    console.log(`PASS ${String(n).padStart(2, '0')} ${name}`)
  } catch (e) {
    failed++
    console.log(`FAIL ${String(n).padStart(2, '0')} ${name} :: ${e.message.split('\n')[0]}`)
  }
}

t('constants: one action id, keybind, pane id, poll period', () => {
  assert.equal(ACTION_ID, 'logbuch.reveal')
  assert.equal(KEYBIND, 'mod+alt+l')
  assert.equal(PANE_ID, 'logbuch:pane')
  assert.equal(POLL_MS, 60_000)
})

t('score is value*100 + min(commit+MR calls, 60) + min(edits, 40)/10', () => {
  assert.equal(scoreOf(mk('a', { label: lab('INFRA', 3), commit_calls: 4, mr_calls: 1, edits: 10 })), 300 + 5 + 1)
  assert.equal(scoreOf(mk('b', { label: lab('INFRA', 2), commit_calls: 100, mr_calls: 100, edits: 400 })), 200 + 60 + 4)
  assert.equal(scoreOf(mk('c', { label: null, commit_calls: 2 })), 2)
  assert.equal(bucket(mk('d', { label: null })), 0)
  assert.equal(bucket(mk('e', { label: lab('INFRA', 0) })), 0)
})

t('loose end counts only while not done; summary falls back to the title', () => {
  assert.equal(isLoose(mk('a', { loose_end: true })), true)
  assert.equal(isLoose(mk('b', { loose_end: true, loose_end_done: true })), false)
  assert.equal(isLoose(mk('c')), false)
  assert.equal(summaryOf(mk('d', { label: null })), 'title d')
  assert.equal(summaryOf(mk('e', { label: null, title: '' })), '(untitled)')
})

const SET = [
  mk('p1', { label: lab('INFRA', 3, 'Rebuilt the crew sandbox'), loose_end: true }),
  mk('p2', { label: lab('SHOP', 2, 'Field audit'), loose_end: true, loose_end_done: true }),
  mk('p3', { label: lab('SHOP', 1, 'Token review') }),
  mk('none', { label: lab('PERSONAL', 0, 'Prompt tweaks') }),
  mk('raw', { label: null, title: 'scratch about flags' })
]

t('default filter shows P1 and P2 only', () => {
  const f = normalizeFilters(null)
  assert.deepEqual(f, { vals: { 3: true, 2: true, 1: false, 0: false }, loose: false, q: '', states: {} })
  assert.deepEqual(filterItems(SET, TOPICS, f).map(i => i.id), ['p1', 'p2'])
  assert.deepEqual(DEFAULT_FILTERS.vals, { 3: true, 2: true, 1: false, 0: false })
})

t('chips: P3 and none; an unlabelled item is "none"', () => {
  const on = vals => filterItems(SET, TOPICS, { vals, loose: false, q: '' }).map(i => i.id)
  assert.deepEqual(on({ 3: false, 2: false, 1: true, 0: false }), ['p3'])
  assert.deepEqual(on({ 3: false, 2: false, 1: false, 0: true }), ['none', 'raw'])
  assert.deepEqual(on({ 3: true, 2: true, 1: true, 0: true }).length, 5)
})

t('loose-end filter ignores a loose end marked done', () => {
  const f = { ...normalizeFilters(null), loose: true }
  assert.deepEqual(filterItems(SET, TOPICS, f).map(i => i.id), ['p1'])
})

t('search matches summary, title, id and topic name, case-insensitive, trimmed', () => {
  const all = { vals: { 3: true, 2: true, 1: true, 0: true }, loose: false }
  const q = s => filterItems(SET, TOPICS, { ...all, q: s }).map(i => i.id)
  assert.deepEqual(q('SANDBOX'), ['p1'])
  assert.deepEqual(q('title none'), ['none'])
  assert.deepEqual(q('  STOREFRONT and '), ['p2', 'p3'])
  assert.deepEqual(q('flags'), ['raw'])
  assert.deepEqual(q('Not labelled'), ['raw'])
  assert.deepEqual(q('nothing like this'), [])
})

t('normalizers repair whatever storage hands back', () => {
  assert.deepEqual(normalizeFilters('junk'), normalizeFilters(null))
  assert.deepEqual(normalizeFilters({ vals: { 1: true, 3: false, 9: true }, loose: 1, q: 5 }), { vals: { 3: false, 2: true, 1: true, 0: false }, loose: true, q: '', states: {} })
  assert.deepEqual(normalizeFilters({ states: { critical: true, todo: false, bogus: true, none: 'yes' } }).states, { critical: true })
  assert.deepEqual(normalizeFilters({ states: 'junk' }).states, {})
  assert.equal(normalizeSort('date'), 'date')
  assert.equal(normalizeSort('bogus'), 'score')
  assert.deepEqual(normalizeCollapsed({ INFRA: true, SHOP: false, PERSONAL: 'yes' }), { INFRA: true })
  assert.deepEqual(normalizeCollapsed([1, 2]), {})
  assert.deepEqual(['score', 'date', 'ship'].map(nextSort), ['date', 'ship', 'score'])
})

t('sort: priority, newest, shipped (ties: newer, then id)', () => {
  const a = mk('a', { label: lab('INFRA', 2), commit_calls: 30, started_at: 300 })
  const b = mk('b', { label: lab('INFRA', 3), started_at: 100 })
  const c = mk('c', { label: lab('INFRA', 2), commit_calls: 2, started_at: 200 })
  const d = mk('d', { label: lab('INFRA', 2), commit_calls: 2, started_at: 200 })
  const ids = s => sortItems([c, d, a, b], s).map(i => i.id)
  assert.deepEqual(ids('score'), ['b', 'a', 'c', 'd'])
  assert.deepEqual(ids('date'), ['a', 'c', 'd', 'b'])
  assert.deepEqual(ids('ship'), ['a', 'c', 'd', 'b'])
})

t('groups: strongest topic first, own sort inside, counts per group', () => {
  const items = [
    mk('w1', { label: lab('PERSONAL', 3), commit_calls: 1 }),
    mk('c1', { label: lab('SHOP', 2), commit_calls: 5, mr_calls: 2 }),
    mk('c2', { label: lab('SHOP', 3), mr_calls: 1 }),
    mk('r', { label: null })
  ]
  const g = groupItems(items, TOPICS, 'score')
  assert.deepEqual(g.map(x => x.key), ['SHOP', 'PERSONAL', UNLABELLED])
  assert.deepEqual(g[0].items.map(i => i.id), ['c2', 'c1'])
  assert.deepEqual([g[0].p1, g[0].commit_calls, g[0].mr_calls], [1, 5, 3])
  assert.equal(g[0].name, 'Storefront and checkout')
  assert.equal(g[2].name, 'Not labelled yet')
})

t('summary numbers', () => {
  const s = summarize(SET)
  assert.deepEqual(s.byValue, { 3: 1, 2: 1, 1: 1, 0: 2 })
  assert.equal(s.count, 5)
  assert.equal(s.loose, 1)
  assert.equal(s.topics, 4)
  assert.equal(summarize([]).count, 0)
})

t('badge: P1 and P2 only, null for P3, none, unlabelled and unknown ids', () => {
  const idx = badgeIndex(SET)
  assert.equal(badgeFor(idx, 'p1'), 'P1')
  assert.equal(badgeFor(idx, 'p2'), 'P2')
  for (const id of ['p3', 'none', 'raw', 'unknown-id']) assert.equal(badgeFor(idx, id), null)
  assert.equal(badgeFor(badgeIndex(undefined), 'p1'), null)
  assert.equal(badgeFor(undefined, 'p1'), null)
})

t('ISO weeks: year edges, 53-week years, shifting, parsing', () => {
  const w = (y, m, d) => weekOfEpoch(new Date(y, m - 1, d, 12).getTime() / 1000)
  assert.equal(w(2021, 1, 3), '2020-W53')
  assert.equal(w(2020, 12, 31), '2020-W53')
  assert.equal(w(2021, 1, 4), '2021-W01')
  assert.equal(w(2024, 12, 30), '2025-W01')
  assert.equal(w(2026, 1, 1), '2026-W01')
  assert.equal(w(2026, 10, 21), '2026-W43')
  assert.equal(w(2026, 12, 31), '2026-W53')
  assert.equal(currentWeek(new Date(2026, 9, 21, 9, 0)), '2026-W43')
  assert.equal(shiftWeek('2026-W01', -1), '2025-W52')
  assert.equal(shiftWeek('2025-W52', 1), '2026-W01')
  assert.equal(shiftWeek('2026-W53', 1), '2027-W01')
  assert.equal(shiftWeek('2026-W43', -43), '2025-W52')
  assert.deepEqual(parseWeek('2026-W53'), { year: 2026, week: 53 })
  assert.equal(parseWeek('2025-W53'), null)
  assert.equal(parseWeek('2026-W00'), null)
  assert.equal(parseWeek('2026-43'), null)
  assert.equal(shiftWeek('garbage', 1), 'garbage')
})

t('digest count: P1 and P2 sessions that started in the week', () => {
  const at = (y, m, d) => new Date(y, m - 1, d, 10).getTime() / 1000
  const items = [
    mk('a', { label: lab('INFRA', 3), started_at: at(2026, 10, 19) }),
    mk('b', { label: lab('INFRA', 2), started_at: at(2026, 10, 25) }),
    mk('c', { label: lab('INFRA', 1), started_at: at(2026, 10, 21) }),
    mk('d', { label: null, started_at: at(2026, 10, 21) }),
    mk('e', { label: lab('INFRA', 3), started_at: at(2026, 10, 26) })
  ]
  assert.equal(digestCount(items, '2026-W43'), 2)
  assert.equal(digestCount(items, '2026-W44'), 1)
  assert.equal(digestCount(undefined, '2026-W44'), 0)
})

t('fmtDate is the local calendar day', () => {
  assert.equal(fmtDate(new Date(2026, 9, 21, 23, 30).getTime() / 1000), '2026-10-21')
  assert.equal(fmtDate(new Date(2026, 0, 2, 0, 5).getTime() / 1000), '2026-01-02')
})

t('PUT body: changed fields only on a labelled item, full label on an unlabelled one', () => {
  const it = mk('a', { label: lab('INFRA', 2, 'Alert routing'), loose_end: true })
  const d = draftFor(it)
  assert.equal(putBody(it, d), null)
  assert.deepEqual(putBody(it, { ...d, value: 3 }), { value: 3 })
  assert.deepEqual(putBody(it, { ...d, topic: 'SHOP', summary: '  New text  ' }), { topic: 'SHOP', summary: 'New text' })
  assert.deepEqual(putBody(it, { ...d, loose_end_done: true }), { loose_end_done: true })
  const raw = mk('r', { label: null, title: 'scratch' })
  assert.deepEqual(putBody(raw, { ...draftFor(raw, 3), topic: 'PERSONAL' }), { topic: 'PERSONAL', value: 3, summary: 'scratch' })
  assert.equal(clipSummary(`  ${'x'.repeat(200)}  `).length, 120)
})

t('save is offered only when the backend would accept the merged label', () => {
  const raw = mk('r', { label: null })
  assert.equal(canSave(raw, draftFor(raw, 2)), false)
  assert.equal(canSave(raw, { ...draftFor(raw, 2), topic: 'INFRA' }), true)
  assert.equal(canSave(raw, { ...draftFor(raw), topic: 'INFRA' }), false)
  const it = mk('a')
  assert.equal(canSave(it, draftFor(it)), true)
  assert.equal(canSave(it, { ...draftFor(it), summary: '  ' }), false)
  assert.equal(draftFor(raw).summary, 'title r')
})

const ST = [
  mk('crit', { label: lab('INFRA', 3), state: 'critical', state_evidence: 'Your request was not processed.' }),
  mk('wait', { label: lab('INFRA', 2), state: 'waiting_go', state_evidence: 'needs your go before it lands' }),
  mk('intr', { label: lab('SHOP', 1), state: 'interrupted', state_evidence: 'Operation interrupted: waiting for model response' }),
  mk('merge', { label: lab('SHOP', 3), state: 'not_merged', state_evidence: 'none is merged yet' }),
  mk('todo', { label: lab('INFRA', 2), state: 'todo', state_evidence: 'is still to do' }),
  mk('ship', { label: lab('INFRA', 3), state: 'shipped', state_evidence: null, commit_calls: 2 }),
  mk('none', { label: lab('PERSONAL', 0), state: 'none', state_evidence: null }),
  mk('old', { label: lab('INFRA', 2) })
]
const ALL = { vals: { 3: true, 2: true, 1: true, 0: true }, loose: false, q: '', states: {} }

t('states: seven in severity order, icons vendored, only critical and waiting_go animate', () => {
  assert.deepEqual(STATE_IDS, ['critical', 'waiting_go', 'interrupted', 'not_merged', 'todo', 'shipped', 'none'])
  assert.deepEqual(STATES.filter(s => s[3]).map(s => s[0]), ['critical', 'waiting_go'])
  for (const [, , icon] of STATES) assert.ok(ICON_SET.icons[icon], icon)
  assert.equal(new Set(STATES.map(s => s[2])).size, 7)
})

t('icons: vendored JSON, not_found null, sha256 file matches, MIT licence beside it', () => {
  const dir = join(srcDir, 'icons')
  const json = readFileSync(join(dir, 'line-md.json'))
  assert.equal(ICON_SET.prefix, 'line-md')
  // The API leaves the key out when every requested name exists; a present key must be null.
  assert.ok(ICON_SET.not_found === undefined || ICON_SET.not_found === null)
  const sum = readFileSync(join(dir, 'line-md.json.sha256'), 'utf8').trim().split(/\s+/)[0]
  assert.equal(createHash('sha256').update(json).digest('hex'), sum)
  assert.deepEqual(Object.keys(ICON_SET.icons).sort(), STATES.map(s => s[2]).sort())
  assert.ok(existsSync(join(dir, 'LICENSE')))
  const lic = readFileSync(join(dir, 'LICENSE'), 'utf8')
  assert.ok(/Vjacheslav Trushkin/.test(lic) && /Permission is hereby granted/.test(lic))
})

t('icons: the static frame has no SMIL and every stroke is drawn', () => {
  for (const [id, , icon, animated] of STATES) {
    const still = iconBody(icon, false)
    assert.equal(/<(animate|animateTransform|set)\b/.test(still), false, `${id} static still animates`)
    for (const m of still.matchAll(/stroke-dashoffset="([^"]*)"/g)) assert.equal(m[1], '0', `${id} dashoffset ${m[1]}`)
    assert.equal(/fill-opacity="0"/.test(still), false, `${id} twotone fill hidden`)
    const moving = iconBody(icon, true)
    assert.equal(/repeatCount="indefinite"/.test(moving), animated, `${id} loop only when animated`)
  }
  assert.equal(iconBody('alert-loop', true), ICON_SET.icons['alert-loop'].body)
  assert.equal(iconBody('missing', true), '')
})

t('icons: staticBody writes the frozen end value onto the element', () => {
  const body = '<path fill-opacity="0" stroke-dashoffset="9"><animate fill="freeze" attributeName="stroke-dashoffset" to="0"/>' +
    '<animate fill="freeze" attributeName="fill-opacity" begin="1s" to=".3"/><animate attributeName="stroke-width" repeatCount="indefinite" values="2;3"/></path>'
  const out = staticBody(body)
  assert.ok(/stroke-dashoffset="0"/.test(out) && /fill-opacity="\.3"/.test(out))
  assert.equal(/stroke-width/.test(out), false)
  assert.equal(/<animate/.test(out), false)
  assert.ok(/values="60;0"/.test(ICON_SET.icons['alert-loop'].body))
  assert.ok(/stroke-dashoffset="0"/.test(staticBody(ICON_SET.icons['alert-loop'].body)))
})

t('state accessors: unknown or missing state reads none, evidence only when a string', () => {
  assert.equal(stateOf(mk('a')), 'none')
  assert.equal(stateOf(mk('a', { state: 'bogus' })), 'none')
  assert.equal(stateOf(ST[0]), 'critical')
  assert.equal(evidenceOf(ST[0]), 'Your request was not processed.')
  assert.equal(evidenceOf(ST[5]), null)
  assert.equal(evidenceOf(mk('a', { state_evidence: '' })), null)
  assert.equal(evidenceOf(mk('a', { state_evidence: 7 })), null)
})

t('state tip: the state name, then the evidence, else what the state means', () => {
  assert.equal(stateTip(ST[0]), 'Critical: Your request was not processed.')
  assert.equal(stateTip(ST[1]), 'Waiting on go: needs your go before it lands')
  assert.ok(/^Shipped: /.test(stateTip(ST[5])) && /Commit or MR calls/.test(stateTip(ST[5])))
  assert.ok(/^None: /.test(stateTip(mk('a'))))
})

t('state filter: no chip shows all, chips are an OR, composes with value and loose', () => {
  const ids = f => filterItems(ST, TOPICS, f).map(i => i.id)
  assert.equal(anyState(ALL), false)
  assert.equal(ids(ALL).length, 8)
  assert.deepEqual(ids({ ...ALL, states: { critical: true } }), ['crit'])
  assert.deepEqual(ids({ ...ALL, states: { critical: true, todo: true } }), ['crit', 'todo'])
  assert.deepEqual(ids({ ...ALL, states: { none: true } }), ['none', 'old'])
  assert.deepEqual(ids({ ...ALL, vals: { 3: true, 2: false, 1: false, 0: false }, states: { shipped: true, todo: true } }), ['ship'])
  assert.deepEqual(ids({ ...ALL, loose: true, states: { critical: true } }), [])
  assert.deepEqual(ids({ vals: ALL.vals, loose: false, q: '' }).length, 8)
  assert.deepEqual(ids({ ...ALL, states: { critical: false } }).length, 8)
})

t('state counts run over the value, loose and search filters but not the state chips', () => {
  const all = stateCounts(filterBase(ST, TOPICS, ALL))
  assert.deepEqual(all, { critical: 1, waiting_go: 1, interrupted: 1, not_merged: 1, todo: 1, shipped: 1, none: 2 })
  const p1 = stateCounts(filterBase(ST, TOPICS, { ...ALL, vals: { 3: true, 2: false, 1: false, 0: false }, states: { todo: true } }))
  assert.deepEqual(p1, { critical: 1, waiting_go: 0, interrupted: 0, not_merged: 1, todo: 0, shipped: 1, none: 0 })
  assert.deepEqual(stateCounts([]), { critical: 0, waiting_go: 0, interrupted: 0, not_merged: 0, todo: 0, shipped: 0, none: 0 })
})

t('badge states: P1 and P2 only; a critical session is the red variant, the rest keep their state', () => {
  const idx = badgeStates(ST)
  assert.equal(idx.get('crit').state, 'critical')
  assert.equal(idx.get('merge').state, 'not_merged')
  assert.equal(idx.get('old').state, 'none')
  assert.ok(/^Critical: /.test(idx.get('crit').tip))
  for (const id of ['intr', 'none', 'unknown']) assert.equal(idx.get(id), undefined)
  assert.equal(badgeFor(badgeIndex(ST), 'crit'), 'P1')
  assert.equal(badgeStates(undefined).size, 0)
  const view = readFileSync(join(srcDir, 'view.js'), 'utf8')
  assert.ok(/critical \? ' critical' : ''/.test(view) && /state === 'none' \? null : h\(StateIcon/.test(view))
})

t('interrupted and waiting_go use the app --ui-orange token with a fallback, no red/yellow mix', () => {
  const rule = CSS.split('\n').find(l => l.startsWith('.lb-c-waiting_go,.lb-c-interrupted{'))
  assert.ok(rule, 'rule exists')
  assert.ok(/var\(--ui-orange,#db704b\)/.test(rule), rule)
  assert.equal(/--ui-(red|yellow)/.test(rule), false, rule)
  assert.equal(/\.lb-c-critical\{[^}]*--ui-red/.test(CSS), true)
})

t('orange state tone has contrast >= 3:1 on the dark and the light pane', () => {
  const lin = c => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4 }
  const lum = ([r, g, b]) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
  const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05) }
  const mix = (a, b, p) => a.map((v, i) => v * p + b[i] * (1 - p))
  const orange = [0xdb, 0x70, 0x4b] // styles.css:244, same in :root and :root.dark
  const dark = ratio(mix(orange, [0xec, 0xec, 0xf0], 0.8), [0x16, 0x16, 0x18])
  const light = ratio(mix(orange, [0x18, 0x18, 0x1b], 0.8), [0xff, 0xff, 0xff])
  assert.ok(dark >= 3, `dark ${dark.toFixed(2)}`)
  assert.ok(light >= 3, `light ${light.toFixed(2)}`)
})

const files = readdirSync(srcDir).filter(f => f.endsWith('.js'))
const read = f => readFileSync(join(srcDir, f), 'utf8')

t('pane data stacks into Files: center dock, no enforce, hide-only, collapsible, 340px, tab text', () => {
  assert.deepEqual(PANE_DATA.dock, { pane: 'files', pos: 'center' })
  assert.equal('enforce' in PANE_DATA.dock, false)
  assert.equal(PANE_DATA.placement, 'right')
  assert.equal(PANE_DATA.collapsible, true)
  assert.equal(PANE_DATA.hideOnly, true)
  assert.equal(PANE_DATA.width, '340px')
  // Capped, or the Files zone turns into the row's absorber and fills the window.
  assert.equal(PANE_DATA.minWidth, '15rem')
  assert.equal(PANE_DATA.maxWidth, '36rem')
  assert.equal(PANE_DATA.tabTitleText(), 'Logbuch')
})

t('index.js registers the pane with PANE_DATA and no workspace dock', () => {
  const idx = read('index.js')
  assert.ok(/id: 'pane',\s+area: PANES_AREA,[^}]*data: PANE_DATA/.test(idx))
  assert.equal(/pane: 'workspace'/.test(idx), false)
})

t('sidebar nav row: Logbuch, notebook codicon, order 53, path of the page', () => {
  assert.deepEqual(NAV_DATA, { path: PATH, label: 'Logbuch', codicon: 'notebook' })
  assert.equal(NAV_ORDER, 53)
  const idx = read('index.js')
  assert.ok(/id: 'nav', area: SIDEBAR_NAV_AREA, order: NAV_ORDER, data: NAV_DATA/.test(idx))
  assert.ok(/SIDEBAR_NAV_AREA \}/.test(idx))
})

t('empty-state note describes hide-only: tab menu, Ctrl+K, Ctrl+J, plugin stays on; no disable wording', () => {
  assert.ok(/tab menu/.test(HIDE_NOTE) && /Ctrl\+K/.test(HIDE_NOTE) && /Ctrl\+J/.test(HIDE_NOTE) && /plugin stays on/.test(HIDE_NOTE))
  assert.equal(/disables|Closing/.test(HIDE_NOTE), false)
  const view = read('view.js')
  assert.ok(/lb-note' \}, HIDE_NOTE/.test(view))
  assert.equal(/CLOSE_NOTE|disables the whole plugin/.test(view), false)
})

t('no composer.submit anywhere in desktop/src', () => {
  assert.ok(files.length >= 9)
  for (const f of files) assert.equal(/composer\s*\.\s*submit/.test(read(f)), false, f)
})

t('UI strings say "commit calls" and "MR calls", never "commits"', () => {
  for (const f of files) {
    for (const [i, line] of read(f).split('\n').entries()) {
      if (/^\s*\/\//.test(line)) continue
      assert.equal(/['"`][^'"`]*\bcommits\b/i.test(line), false, `${f}:${i + 1}`)
    }
  }
  assert.ok(/commit calls/.test(read('view.js')) && /MR calls/.test(read('view.js')))
})

t('desktop/src and README use ASCII punctuation only', () => {
  const bad = /[\u2013\u2014\u2026\u2018\u2019\u201c\u201d\u2190-\u21ff]/
  for (const f of files) assert.equal(bad.test(read(f)), false, f)
  assert.equal(bad.test(readFileSync(join(here, '..', 'README.md'), 'utf8')), false, 'README.md')
})

console.log(`${n - failed}/${n} passed`)
process.exit(failed ? 1 : 0)
