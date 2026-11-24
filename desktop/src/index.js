// Source of desktop/plugin.js (`sh scripts/rebuild.sh`, CI job logbuch:self-contained). Data comes from
// dashboard/plugin_api.py through ctx.rest; labels go back through PUT /labels/{id}, nothing here writes chat text (S4).
// Every named @hermes/plugin-sdk import must exist in the oldest supported host SDK (tools/build/sdk-exports.mjs).

import { KEYBINDS_AREA, PALETTE_AREA, PANES_AREA, ROUTES_AREA, SESSION_ROW_AREAS, SIDEBAR_NAV_AREA } from '@hermes/plugin-sdk'
import { createElement as h } from 'react'

import { mountStyle } from './kit/theme.js'

import { CSS } from './css.js'
import { reveal } from './data.js'
import { ACTION_ID, ID, KEYBIND, NAV_DATA, NAV_ORDER, PANE_DATA, PANE_ID, PATH } from './model.js'
import { bind, unbind } from './state.js'
import { LogbuchPage, LogbuchPane, RowBadge } from './view.js'

export default {
  id: ID,
  name: 'Logbuch',
  description: 'Real-work sessions ranked by business value: a tab stacked with Files, a full page, value badges in the sidebar and a weekly Markdown digest.',
  register(ctx) {
    bind(ctx)
    const unmountStyle = mountStyle(ID, CSS)
    ctx.onDispose(() => {
      unmountStyle()
      unbind()
    })
    // One action, two surfaces: the keybind and the palette row can never drift apart.
    const show = () => reveal(PANE_ID, PATH)
    ctx.registerMany([
      {
        id: 'pane',
        area: PANES_AREA,
        title: 'Logbuch',
        data: PANE_DATA,
        render: () => h(LogbuchPane)
      },
      { id: 'page', area: ROUTES_AREA, data: { path: PATH }, render: () => h(LogbuchPage) },
      { id: 'nav', area: SIDEBAR_NAV_AREA, order: NAV_ORDER, data: NAV_DATA },
      { id: 'keybind', area: KEYBINDS_AREA, data: { id: ACTION_ID, label: 'Show Logbuch', defaults: [KEYBIND], run: show } },
      {
        id: 'palette',
        area: PALETTE_AREA,
        data: { id: ACTION_ID, action: ACTION_ID, label: 'Show Logbuch', keywords: ['logbuch', 'sessions', 'value', 'digest', 'log'], run: show }
      },
      { id: 'badge', area: SESSION_ROW_AREAS.trailing, data: { render: ({ sessionId }) => h(RowBadge, { sessionId }) } }
    ])
  }
}
