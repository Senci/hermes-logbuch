// Iconify line-md (MIT, Vjacheslav Trushkin), vendored in icons/line-md.json and never fetched at runtime.
// The SMIL draw-in starts hidden, so `staticBody` writes each frozen animation's end value on its element, then drops the tags.
import data from './icons/line-md.json' with { type: 'json' }

export const ICON_SET = data

const ANIM = /<(animate|animateTransform|set)\b[^>]*?\/>/g
const ELEMENT = /<([a-zA-Z]+)\b([^>]*?)(\/?)>((?:\s*<(?:animate|animateTransform|set)\b[^>]*?\/>)+)\s*<\/\1>/g
const ATTR = /([a-zA-Z:-]+)="([^"]*)"/g

const attrsOf = text => {
  const out = new Map()
  for (const m of text.matchAll(ATTR)) out.set(m[1], m[2])
  return out
}

// End value of a frozen animation: `to`, else the last of `values`.
const endValue = a => {
  if (a.get('fill') !== 'freeze' || !a.get('attributeName')) return null
  if (a.has('to')) return a.get('to')
  return a.has('values') ? a.get('values').split(';').pop().trim() : null
}

export function staticBody(body) {
  const frozen = body.replace(ELEMENT, (_all, tag, own, _close, kids) => {
    const attrs = attrsOf(own)
    for (const k of kids.matchAll(ANIM)) {
      const a = attrsOf(k[0])
      const end = endValue(a)
      if (end !== null) attrs.set(a.get('attributeName'), end)
    }
    return `<${tag} ${[...attrs].map(([n, v]) => `${n}="${v}"`).join(' ')}/>`
  })
  // A group can carry the hidden start offset its children override; the frame is fully drawn, so drop any.
  return frozen.replace(ANIM, '').replace(/ stroke-dashoffset="(?!0")[^"]*"/g, '')
}

const cache = new Map()
export function iconBody(name, animated) {
  const icon = data.icons[name]
  if (!icon) return ''
  if (animated) return icon.body
  if (!cache.has(name)) cache.set(name, staticBody(icon.body))
  return cache.get(name)
}

export const iconBox = name => {
  const icon = data.icons[name] || {}
  return `0 0 ${icon.width || data.width || 24} ${icon.height || data.height || 24}`
}
