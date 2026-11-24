// Host context and view preferences, bound in register(), cleared on dispose; atoms keep pane and page in sync, writes go to ctx.storage.
import { atom } from '@hermes/plugin-sdk'

import { STORE } from './model.js'
import { currentWeek, normalizeCollapsed, normalizeFilters, normalizeSort } from './logic.js'

export let api = null
export let $filters = null
export let $sort = null
export let $collapsed = null
// Week the digest button exports. A session-long choice, not stored: it starts at the current week.
export let $week = null
// The item the label dialog edits: { id, value } or null.
export let $editing = null

export function bind(ctx) {
  api = ctx
  $filters = atom(normalizeFilters(ctx.storage.get(STORE.filters, null)))
  $sort = atom(normalizeSort(ctx.storage.get(STORE.sort, null)))
  $collapsed = atom(normalizeCollapsed(ctx.storage.get(STORE.collapsed, null)))
  $week = atom(currentWeek())
  $editing = atom(null)
}

export function unbind() {
  api = null
  $filters = $sort = $collapsed = $week = $editing = null
}

// The function form reads the atom, not a render's closure, so two changes in one tick both land.
const persist = (a, key, next) => {
  const v = typeof next === 'function' ? next(a.get()) : next
  a.set(v)
  api.storage.set(key, v)
}
export const setFilters = next => persist($filters, STORE.filters, next)
export const setSort = next => persist($sort, STORE.sort, next)
export const setCollapsed = next => persist($collapsed, STORE.collapsed, next)
