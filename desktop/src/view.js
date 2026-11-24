// Rows are buttons that open the session through openSession, never a hermes:// URL; nothing writes chat text (S4).
import {
  Button, Checkbox, Codicon, Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger, EmptyState,
  ErrorState, host, Input, Loader, SearchField, SegmentedControl, Select, SelectContent, SelectItem, SelectTrigger,
  SelectValue, Tip, useValue
} from '@hermes/plugin-sdk'
import { createElement as h, Fragment, useMemo, useState } from 'react'

import { exportDigest, openSession, putLabel, reveal, useCachedSessions, useSessions } from './data.js'
import {
  badgeFor, badgeIndex, badgeStates, bucket, canSave, currentWeek, digestCount, draftFor, filterBase, filterItems,
  fmtDate, fmtTime, groupItems, isLoose, nextSort, putBody, shiftWeek, stateCounts, stateOf, stateTip, summarize,
  summaryOf, valueOf
} from './logic.js'
import { HIDE_NOTE, PANE_ID, PATH, SORTS, STATES, SUMMARY_MAX, VALUES, VALUE_LABEL } from './model.js'
import { StateIcon } from './state-icon.js'
import { $collapsed, $editing, $filters, $sort, $week, setCollapsed, setFilters, setSort } from './state.js'

const stop = e => e.stopPropagation()
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`
const say = (kind, message) => host.notify({ kind, message })
const fail = (what, e) => say('error', `Logbuch: ${what} failed: ${(e && e.message) || e}`)

async function save(it, body) {
  try {
    await putLabel(it.id, body)
  } catch (e) {
    fail('saving the label', e)
  }
}

function RowMenu({ it }) {
  const labelled = !!it.label
  const pickValue = v => (labelled ? save(it, { value: v }) : $editing.set({ id: it.id, value: v }))
  return h(DropdownMenu, null,
    h(DropdownMenuTrigger, { asChild: true },
      h(Button, { size: 'icon-xs', variant: 'ghost', className: 'lb-menu', 'aria-label': 'Row actions', 'data-menu': it.id, onClick: stop },
        h(Codicon, { name: 'ellipsis' }))),
    h(DropdownMenuContent, { align: 'end', onClick: stop },
      VALUES.map(([v, label, name]) =>
        h(DropdownMenuItem, { key: v, 'data-set-value': v, onSelect: () => pickValue(v) },
          valueOf(it) === v ? h(Codicon, { name: 'check' }) : h('span', { style: { display: 'inline-block', width: '1em' } }), `${label} (${name.toLowerCase()})`)),
      h(DropdownMenuSeparator, null),
      h(DropdownMenuItem, { 'data-edit': '1', onSelect: () => $editing.set({ id: it.id }) },
        h(Codicon, { name: 'edit' }), 'Edit topic and summary'),
      it.loose_end
        ? h(DropdownMenuItem, { 'data-loose-toggle': '1', onSelect: () => save(it, { loose_end_done: !it.loose_end_done }) },
          h(Codicon, { name: it.loose_end_done ? 'circle-large-outline' : 'pass' }), it.loose_end_done ? 'Reopen loose end' : 'Mark loose end done')
        : null))
}

function Row({ it, wide }) {
  const v = bucket(it)
  const text = summaryOf(it)
  const open = () => openSession(it.id)
  return h('div', {
    className: `lb-row v${v}`, 'data-id': it.id, role: 'button', tabIndex: 0, onClick: open,
    onKeyDown: e => { if (e.target === e.currentTarget && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); open() } }
  },
  h('div', { className: 'lb-l1' },
    h('span', { className: `lb-pri v${v}`, 'data-pri': it.label ? VALUE_LABEL[v] : '?', title: it.label ? undefined : 'Not labelled yet' },
      it.label ? VALUE_LABEL[v] : '?'),
    h(StateIcon, { state: stateOf(it), tip: stateTip(it) }),
    h('span', { className: 'lb-sum', title: text }, text),
    h(RowMenu, { it })),
  wide ? h('div', { className: 'lb-l2' }, h('span', { className: 'lb-ttl', title: it.title }, it.title || '(untitled)')) : null,
  h('div', { className: 'lb-l2' },
    h('span', null, fmtDate(it.started_at)),
    h('span', null, h('b', null, it.commit_calls ?? 0), ' commit calls'),
    h('span', null, h('b', null, it.mr_calls ?? 0), ' MR calls'),
    wide ? h('span', null, h('b', null, it.turns ?? 0), ' turns') : null,
    wide ? h('span', null, h('b', null, it.tool_calls ?? 0), ' tool calls') : null,
    isLoose(it) ? h('span', { className: 'lb-loose' }, 'loose end') : null,
    wide ? h('code', { className: 'lb-id' }, it.id) : null))
}

function Group({ g, wide, collapsed }) {
  const closed = !!collapsed[g.key]
  const flip = () => setCollapsed(cur => {
    const next = { ...cur }
    if (next[g.key]) delete next[g.key]
    else next[g.key] = true
    return next
  })
  return h('div', { className: 'lb-grp', 'data-k': g.key },
    h('button', { type: 'button', className: 'lb-gh', 'aria-expanded': !closed, onClick: flip },
      h(Codicon, { name: closed ? 'chevron-right' : 'chevron-down', className: 'lb-caret', size: '0.8rem' }),
      h('span', { className: 'lb-gname' }, g.name),
      h('span', { className: 'lb-gmeta' },
        `${plural(g.items.length, 'session', 'sessions')}, ${g.p1} P1, ${g.commit_calls} commit calls, ${g.mr_calls} MR calls`)),
    closed ? null : g.items.map(it => h(Row, { key: it.id, it, wide })))
}

function EditForm({ it, topics, start }) {
  const [d, setD] = useState(() => draftFor(it, start))
  const [busy, setBusy] = useState(false)
  const close = () => $editing.set(null)
  const submit = async () => {
    const body = putBody(it, d)
    if (!body) return close()
    setBusy(true)
    try {
      await putLabel(it.id, body)
      close()
    } catch (e) {
      fail('saving the label', e)
      setBusy(false)
    }
  }
  return h(Dialog, { open: true, onOpenChange: o => { if (!o) close() } },
    h(DialogContent, null,
      h(DialogHeader, null,
        h(DialogTitle, null, 'Edit label'),
        h(DialogDescription, null, 'A label you save here is manual: automatic labelling never overwrites it.')),
      h('div', { className: 'lb-form' },
        h('label', null, 'Topic',
          h(Select, { value: d.topic || undefined, onValueChange: topic => setD({ ...d, topic }) },
            h(SelectTrigger, { 'aria-label': 'Topic', 'data-field': 'topic' }, h(SelectValue, { placeholder: 'Choose a topic' })),
            h(SelectContent, null, Object.entries(topics).map(([k, name]) => h(SelectItem, { key: k, value: k }, name))))),
        h('label', null, 'Value',
          h(SegmentedControl, {
            options: VALUES.map(([v, label]) => ({ id: String(v), label })),
            value: d.value === null || d.value === undefined ? '' : String(d.value),
            onChange: id => setD({ ...d, value: Number(id) })
          })),
        h('label', null, `Summary (${d.summary.length}/${SUMMARY_MAX})`,
          h(Input, { value: d.summary, maxLength: SUMMARY_MAX, 'aria-label': 'Summary', 'data-field': 'summary', onChange: e => setD({ ...d, summary: e.target.value }) })),
        it.loose_end
          ? h('label', { className: 'lb-inline' },
            h(Checkbox, { checked: d.loose_end_done, 'data-field': 'loose', onCheckedChange: c => setD({ ...d, loose_end_done: c === true }) }),
            'Loose end done')
          : null),
      h(DialogFooter, null,
        h(Button, { variant: 'ghost', size: 'sm', onClick: close, 'data-cancel': '1' }, 'Cancel'),
        h(Button, { size: 'sm', disabled: busy || !canSave(it, d), onClick: submit, 'data-save': '1' }, 'Save'))))
}

function EditDialog({ items, topics }) {
  const editing = useValue($editing)
  const it = editing && items.find(i => i.id === editing.id)
  if (!it) return null
  return h(EditForm, { key: `${it.id}:${editing.value ?? ''}`, it, topics, start: editing.value })
}

function DigestControl({ items }) {
  const week = useValue($week)
  const [busy, setBusy] = useState(false)
  const count = digestCount(items, week)
  const run = async () => {
    setBusy(true)
    try {
      await exportDigest(week)
    } catch (e) {
      fail('writing the digest', e)
    } finally {
      setBusy(false)
    }
  }
  return h('span', { className: 'lb-wk', 'data-digest': week },
    h(Button, { size: 'icon-xs', variant: 'ghost', 'aria-label': 'Previous week', 'data-week': 'prev', onClick: () => $week.set(shiftWeek($week.get(), -1)) },
      h(Codicon, { name: 'chevron-left' })),
    h('code', { 'data-week-label': '1' }, week),
    h(Button, { size: 'icon-xs', variant: 'ghost', 'aria-label': 'Next week', 'data-week': 'next', disabled: week >= currentWeek(), onClick: () => $week.set(shiftWeek($week.get(), 1)) },
      h(Codicon, { name: 'chevron-right' })),
    h(Tip, { label: `Save the ${plural(count, 'P1 or P2 session', 'P1 and P2 sessions')} of ${week} as a Markdown digest` },
      h(Button, { size: 'xs', variant: 'outline', disabled: busy, onClick: run, 'data-digest-button': '1' },
        h(Codicon, { name: 'cloud-download' }), 'Digest')))
}

function FilterBars({ groups, counts }) {
  const f = useValue($filters)
  const sort = useValue($sort)
  const collapsed = useValue($collapsed)
  const anyOpen = groups.some(g => !collapsed[g.key])
  const setAll = () => setCollapsed(cur => {
    const next = { ...cur }
    for (const g of groups) if (anyOpen) next[g.key] = true
    else delete next[g.key]
    return next
  })
  return [
    h('div', { key: 'chips', className: 'lb-bar', 'data-bar': 'chips' },
      VALUES.map(([v, label, name]) =>
        h('button', {
          key: v, type: 'button', className: `lb-chip v${v}`, 'data-v': v, title: name, 'aria-pressed': !!f.vals[v],
          onClick: () => setFilters(cur => ({ ...cur, vals: { ...cur.vals, [v]: !cur.vals[v] } }))
        }, label)),
      h('button', {
        type: 'button', className: 'lb-chip lo', 'data-loose': '1', 'aria-pressed': f.loose, onClick: () => setFilters(cur => ({ ...cur, loose: !cur.loose }))
      }, 'Loose ends')),
    h('div', { key: 'states', className: 'lb-bar lb-states', 'data-bar': 'states' },
      STATES.map(([id, name, , , blurb]) =>
        h('button', {
          key: id, type: 'button', className: `lb-chip sc lb-c-${id}`, 'data-st': id, title: blurb, 'aria-pressed': !!f.states[id],
          onClick: () => setFilters(cur => ({ ...cur, states: { ...cur.states, [id]: !(cur.states || {})[id] } }))
        }, h(StateIcon, { state: id, still: true }), name, h('span', { className: 'lb-n', 'data-n': id }, counts[id])))),
    h('div', { key: 'search', className: 'lb-bar', 'data-bar': 'search' },
      h('div', { className: 'lb-search' },
        h(SearchField, { placeholder: 'Search summary, title, id', value: f.q, onChange: q => setFilters(cur => ({ ...cur, q })) })),
      h(Tip, { label: 'Sort order, click to change' },
        h(Button, { size: 'xs', variant: 'ghost', 'data-sort': sort, onClick: () => setSort(nextSort) },
          h(Codicon, { name: 'sort-precedence' }), SORTS.find(s => s.id === sort).label)),
      h(Tip, { label: anyOpen ? 'Collapse all topics' : 'Expand all topics' },
        h(Button, { size: 'icon-xs', variant: 'ghost', 'aria-label': 'Collapse or expand all', 'data-collapse-all': '1', onClick: setAll },
          h(Codicon, { name: anyOpen ? 'collapse-all' : 'expand-all' }))))
  ]
}


function Unreachable({ error, conn, profile }) {
  const where = `backend ${conn || 'this device'}, profile ${profile || 'default'}`
  const hint = /404|not found/i.test(String((error && error.message) || error))
    ? ' A 404 means that backend does not have the logbuch plugin.'
    : ' The Python half loads only when logbuch is in plugins.enabled of that profile and the backend was restarted.'
  return h(ErrorState, { title: `Logbuch backend unreachable (${where})`, description: `${(error && error.message) || error}.${hint}` })
}

function Body({ q, wide }) {
  const { data, error, isLoading, conn, profile } = q
  const f = useValue($filters)
  const sort = useValue($sort)
  const collapsed = useValue($collapsed)
  const topics = (data && data.topics) || {}
  const shown = useMemo(() => (data ? filterItems(data.items, topics, f) : []), [data, f])
  const groups = useMemo(() => groupItems(shown, topics, sort), [shown, sort, data])
  const counts = useMemo(() => stateCounts(data ? filterBase(data.items, topics, f) : []), [data, f])
  const s = summarize(shown)

  if (error && !data) return h('div', { className: 'lb-scroll' }, h(Unreachable, { error, conn, profile }))
  if (isLoading || !data) return h('div', { className: 'lb-empty' }, h(Loader, null))

  const empty = !data.items.length
  return h(
    Fragment, null,
    wide ? null : h('div', { className: 'lb-sub', 'data-sub': '1' }, `profile ${data.profile || profile}, updated ${fmtTime(data.generated_at)}`),
    data.schema_ok === false
      ? h('div', { className: 'lb-banner', 'data-banner': 'schema' },
        'The sessions database does not have every column Logbuch reads (schema_ok is false). Counts fall back to session level; labels still work.')
      : null,
    error ? h('div', { className: 'lb-banner bad', 'data-banner': 'stale' }, `Backend unreachable (${conn || 'this device'}, profile ${profile || 'default'}), showing the last answer.`) : null,
    empty ? null : h(FilterBars, { groups, counts }),
    empty ? null : h('div', { className: 'lb-stats', 'data-stats': '1' },
      `${plural(s.count, 'session', 'sessions')} in ${plural(s.topics, 'topic', 'topics')}: ${s.byValue[3]} P1, ${s.byValue[2]} P2, ${s.byValue[1]} P3, ${s.byValue[0]} none. ` +
      `${s.commit_calls} commit calls, ${s.mr_calls} MR calls. ${plural(s.loose, 'loose end', 'loose ends')}.`),
    h('div', { className: 'lb-scroll', 'data-list': '1' },
      empty
        ? h('div', { className: 'lb-empty', 'data-empty': 'none' },
          h('div', null,
            h(EmptyState, { title: 'No sessions with real work yet', description: 'Logbuch lists desktop and CLI sessions of this profile with at least 20 tool calls and an edit, commit call, MR call or card.' }),
            h('div', { className: 'lb-note' }, HIDE_NOTE)))
        : !groups.length
          ? h('div', { className: 'lb-empty', 'data-empty': 'filtered' },
            h('div', null,
              h(EmptyState, { title: 'No session matches these filters' }),
              h(Button, { size: 'xs', variant: 'outline', 'data-reset': '1', onClick: () => setFilters({ vals: { 3: true, 2: true, 1: true, 0: true }, loose: false, q: '', states: {} }) }, 'Show every session')))
          : groups.map(g => h(Group, { key: g.key, g, wide, collapsed })),
      wide && !empty
        ? h('div', { className: 'lb-legend' },
          'P1: production fix or colleague request delivered. P2: team enablement, or a decision on company systems. P3: indirect. none: personal. ' +
          'Loose end: the last reply left a decision, a merge or a retry open. Priority is business value, then shipped output (commit calls plus MR calls).')
        : null,
      wide && !empty
        ? h('div', { className: 'lb-legend lb-states-legend', 'data-legend': 'states' },
          STATES.map(([id, name, , , blurb]) =>
            h('div', { key: id, className: 'lb-lg', 'data-lg': id }, h(StateIcon, { state: id, still: true }), h('b', null, name), ` ${blurb}.`)))
        : null),
    h(EditDialog, { items: data.items, topics }))
}

function Refresh({ q }) {
  return h(Tip, { label: 'Refresh now' },
    h(Button, { size: 'icon-xs', variant: 'ghost', 'aria-label': 'Refresh', 'data-refresh': '1', disabled: q.isFetching, onClick: () => void q.refetch() },
      h(Codicon, { name: 'refresh', spinning: q.isFetching })))
}

export function LogbuchPane() {
  const q = useSessions()
  return h('div', { className: 'lb pane', 'data-lb': 'pane' },
    h('div', { className: 'lb-head' },
      h('span', { className: 'lb-title lb-grow' }, 'Logbuch'),
      h(Tip, { label: 'Open the full page' },
        h(Button, { size: 'xs', variant: 'ghost', 'data-open-page': '1', onClick: () => host.navigate(PATH) }, h(Codicon, { name: 'link-external' }), 'Page')),
      h(Refresh, { q })),
    h(Body, { q, wide: false }),
    h('div', { className: 'lb-bar lb-foot', 'data-bar': 'digest' }, h(DigestControl, { items: (q.data && q.data.items) || [] })))
}

export function LogbuchPage() {
  const q = useSessions()
  const data = q.data
  return h('div', { className: 'lb wide', 'data-lb': 'page' },
    h('div', { className: 'lb-head' },
      h('span', { className: 'lb-title lb-grow' }, 'Sessions by business value'),
      h(DigestControl, { items: (data && data.items) || [] }),
      h(Tip, { label: 'Show the Logbuch tab in the Files zone' },
        h(Button, { size: 'xs', variant: 'ghost', 'data-show-pane': '1', onClick: () => reveal(PANE_ID, PATH) }, h(Codicon, { name: 'layout-sidebar-right' }), 'Pane')),
      h(Refresh, { q })),
    data
      ? h('div', { className: 'lb-sub', 'data-sub': '1' },
        `${plural(data.items.length, 'session', 'sessions')} with real work, profile ${data.profile || q.profile}, grouped by topic, updated ${fmtTime(data.generated_at)}.`)
      : null,
    h(Body, { q, wide: true }))
}

// Reads the pane's cache entry: P1 and P2 get a pill, every other row and every unknown id gets null.
export function RowBadge({ sessionId }) {
  const data = useCachedSessions()
  const index = useMemo(() => badgeIndex(data && data.items), [data])
  const states = useMemo(() => badgeStates(data && data.items), [data])
  const label = badgeFor(index, sessionId)
  if (!label) return null
  const st = states.get(sessionId) || { state: 'none', tip: stateTip({}) }
  const critical = st.state === 'critical'
  // The state icon rides in the pill (a P1 or P2 with nothing open and nothing shipped shows the plain pill).
  return h(Tip, { label: `Logbuch ${label}, ${st.tip}` },
    h('span', { className: `lb-badge ${label.toLowerCase()}${critical ? ' critical' : ''}`, 'data-badge': label, 'data-state': st.state },
      st.state === 'none' ? null : h(StateIcon, { state: st.state }), label))
}
