// ctx.rest follows the active gateway on every call, so connection and profile are in every query key.
import { captureGatewayFileDownload, host, queryClient, useQuery } from '@hermes/plugin-sdk'

import { useBackend, useLiveQuery } from './kit/live.js'

import { ID, POLL_MS, STALE_MS } from './model.js'
import { api } from './state.js'

const scopeKey = (conn, profile) => [ID, conn, profile]
const sessionsKey = (conn, profile) => [...scopeKey(conn, profile), 'sessions']

const fetchSessions = () => (api ? api.rest('/sessions') : Promise.reject(new Error('logbuch not loaded')))

// The one polling query. A previous payload carries over only from the same connection and profile.
export function useSessions() {
  const { conn, profile } = useBackend()
  const q = useLiveQuery({
    queryKey: sessionsKey(conn, profile),
    queryFn: fetchSessions,
    placeholderData: (prev, prevQuery) =>
      prevQuery && prevQuery.queryKey[1] === conn && prevQuery.queryKey[2] === profile ? prev : undefined,
    pollMs: POLL_MS,
    staleTime: STALE_MS
  })
  return { ...q, conn, profile }
}

// Read-only view of the cache entry for sidebar rows (no fetch, no timer); useSessions() keeps it fresh.
export function useCachedSessions() {
  const { conn, profile } = useBackend()
  return useQuery({ queryKey: sessionsKey(conn, profile), queryFn: fetchSessions, enabled: false, staleTime: Infinity }).data
}

// Save a label. The returned item replaces the row at once; the refetch that follows is the truth.
export async function putLabel(id, body) {
  const key = sessionsKey(host.state.connectionId.get() ?? '', host.state.profile.get() ?? '')
  const item = await api.rest(`/labels/${encodeURIComponent(id)}`, { method: 'PUT', body })
  queryClient.setQueryData(key, old => (old ? { ...old, items: old.items.map(i => (i.id === item.id ? item : i)) } : old))
  await queryClient.invalidateQueries({ queryKey: key.slice(0, 3) })
  return item
}

// Capture the save door right before the request: a file belongs to the connection that wrote it (SDK rule).
export async function exportDigest(week) {
  const save = captureGatewayFileDownload()
  const out = await api.rest('/digest/file', { method: 'POST', body: { week } })
  if (!out || typeof out.path !== 'string' || typeof out.name !== 'string') throw new Error('digest answer has no path and name')
  await save(out.path, out.name)
  return out
}

export function openSession(id) {
  void host.openSession(id)
}

// Idempotent, never toggles; older desktops have no revealPane, so the full page is the way in.
export function reveal(paneId, path) {
  if (typeof host.revealPane === 'function') host.revealPane(paneId)
  else host.navigate(path)
}
