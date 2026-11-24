// One line-md icon per state, coloured by severity (css.js); under prefers-reduced-motion the SMIL tags are not emitted.
import { Tip } from '@hermes/plugin-sdk'
import { createElement as h, useSyncExternalStore } from 'react'

import { iconBody, iconBox } from './icons.js'
import { STATES } from './model.js'

const QUERY = '(prefers-reduced-motion: reduce)'
const query = () => (typeof window !== 'undefined' && window.matchMedia ? window.matchMedia(QUERY) : null)

function subscribe(onChange) {
  const mq = query()
  if (!mq) return () => {}
  mq.addEventListener('change', onChange)
  return () => mq.removeEventListener('change', onChange)
}

const useReducedMotion = () => useSyncExternalStore(subscribe, () => !!(query() && query().matches), () => false)

// `still` forces the static frame (chips, legend); without `tip` the icon is a plain span for a parent with its own Tip.
export function StateIcon({ state, tip, still }) {
  const reduced = useReducedMotion()
  const row = STATES.find(s => s[0] === state) || STATES[STATES.length - 1]
  const moving = row[3] && !still && !reduced
  const span = h('span', {
    className: `lb-st lb-c-${row[0]}`, 'data-state': row[0], 'data-moving': String(moving), role: 'img', 'aria-label': tip || row[1]
  }, h('svg', {
    viewBox: iconBox(row[2]), focusable: 'false', 'aria-hidden': 'true', dangerouslySetInnerHTML: { __html: iconBody(row[2], moving) }
  }))
  return tip ? h(Tip, { label: tip }, span) : span
}
