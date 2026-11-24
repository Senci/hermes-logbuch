// Host --ui-* colours only, so themes follow without a rebuild; tone text is mixed 20% toward the text colour for contrast.
export const CSS = `
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
`
