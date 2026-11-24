// Constants shared by the desktop half. No imports: the node test loads this file as is.

export const ID = 'logbuch'
export const PATH = '/logbuch'
export const PANE_ID = `${ID}:pane`
export const ACTION_ID = 'logbuch.reveal'
export const KEYBIND = 'mod+alt+l'
export const POLL_MS = 60_000
export const NAV_ORDER = 53
export const HIDE_NOTE = 'The Logbuch tab only hides: use its tab menu or Ctrl+K (Logbuch) to hide or show it, and Ctrl+J to fold the whole Files zone with it. The plugin stays on.'

// Stacks into the Files zone so Ctrl+J folds both; maxWidth is required or the zone absorbs all leftover width.
export const PANE_DATA = {
  placement: 'right',
  dock: { pane: 'files', pos: 'center' },
  collapsible: true,
  hideOnly: true,
  width: '340px',
  minWidth: '15rem',
  maxWidth: '36rem',
  tabTitleText: () => 'Logbuch'
}
export const NAV_DATA = { path: PATH, label: 'Logbuch', codicon: 'notebook' }
export const STALE_MS = 30_000
export const SUMMARY_MAX = 120

// Business value, highest first: [value, chip label, name].
export const VALUES = [
  [3, 'P1', 'High'],
  [2, 'P2', 'Medium'],
  [1, 'P3', 'Low'],
  [0, 'none', 'No business value']
]
export const VALUE_LABEL = { 3: 'P1', 2: 'P2', 1: 'P3', 0: '-' }

export const SORTS = [
  { id: 'score', label: 'Priority' },
  { id: 'date', label: 'Newest' },
  { id: 'ship', label: 'Shipped' }
]

// Group key and name for items the backend has not labelled yet.
export const UNLABELLED = '_unlabelled'
export const UNLABELLED_NAME = 'Not labelled yet'

export const STORE = { filters: 'filters', sort: 'sort', collapsed: 'collapsed' }

// Session states (D47), highest first: [id, name, line-md icon, animated, meaning]; an older backend sends none and items read "none".
export const STATES = [
  ['critical', 'Critical', 'alert-loop', true, 'A P1 session that ended on a provider problem'],
  ['waiting_go', 'Waiting on go', 'bell-alert-loop', true, 'The last reply waits for your go or a decision'],
  ['interrupted', 'Interrupted', 'alert-circle-twotone', false, 'Ended on a provider problem, not a P1 session'],
  ['not_merged', 'Not merged', 'upload-twotone', false, 'The last reply says a merge request is not merged or is a draft'],
  ['todo', 'To do', 'clipboard-list-twotone', false, 'The last reply says something is still open or still to do'],
  ['shipped', 'Shipped', 'confirm-circle-twotone', false, 'Commit or MR calls and nothing open'],
  ['none', 'None', 'circle', false, 'Nothing open and nothing shipped']
]
export const STATE_IDS = STATES.map(s => s[0])

export const DEFAULT_FILTERS = { vals: { 3: true, 2: true, 1: false, 0: false }, loose: false, q: '', states: {} }
