# Cost Viewer v2 Frontend Design

## Goal

Rewrite the Amplifier Cost Viewer frontend using Lit 3 web components and a Canvas 2D Gantt renderer, replacing the broken vanilla JS + SVG implementation while leaving the FastAPI backend completely unchanged.

## Background

The current viewer at `viewer/amplifier_app_cost_viewer/static/` has a working FastAPI backend (`reader.py`, `server.py`, `pricing.py`) with full test coverage. The frontend — `app.js`, `style.css`, and `index.html` — is broken. It uses vanilla JS with SVG rendering that has accumulated enough state and layout bugs to make incremental repair impractical.

The backend API is stable and correct. The rewrite is purely a frontend concern: three existing files get replaced, one new vendor file is added.

## Approach

Replace the SVG-based renderer with a Canvas 2D Gantt and four Lit 3 web components. Lit is vendored locally (no CDN dependency at runtime, no build step). State is managed with a single global object and explicit `requestUpdate()` calls — no framework reactivity layer. This mirrors the Chrome DevTools pattern: `HTMLElement` subclasses that call `Lit.render()` manually inside a shadow root.

Canvas is chosen for the Gantt because it handles hundreds of overlapping spans efficiently via color-batched drawing, produces no DOM node overhead per span, and makes text-label culling trivial.

## Architecture

```
┌─ toolbar ────────────────────────────────────────────────────────┐
│ [Amplifier Cost Viewer] [Session ▾] [$total] [↺] [− scale +]    │
├─ left tree ─────────┬─ right timeline ─────────────────────────┤
│ ▾ Cost Strategy $19 │ ░░▓▓████▓▓░░▓▓▓███▓░░  ← cost heatmap   │
│   explorer    $1.32 │ 0s    5m    10m    15m  ← ruler           │
│   git-ops     $0.07 │ ████████████████████   ← canvas gantt    │
│   implementer $8.10 │ ████████                                  │
│ ▸ Langfuse    $3.24 │      ██ ████ ██                           │
│                     ├──────────────────────────────────────────┤
│                     │ detail panel (slides up on span click)    │
└─────────────────────┴──────────────────────────────────────────┘
```

**Navigation model (Option C — tree controls visibility):** Expand/collapse in `<acv-tree>` controls which session rows appear in the Gantt. The Gantt mirrors the tree exactly; it is not independently navigable. Clicking a delegate span in the Gantt opens the detail panel but does not trigger navigation or expansion.

## Components

### `<acv-toolbar>`

Session dropdown with paginated load (25 sessions per page, "Load more" appended at bottom). Displays total cost for the active session. Zoom controls: `−` button, scale label, `+` button. Refresh button (`↺`) re-fetches the session list from the API.

### `<acv-tree>`

Left-panel session hierarchy. Each row contains:
- Indent level + expand/collapse toggle (`▾` / `▸`)
- Session name or ID
- 3px tall inline cost bar whose width scales as `(session.total_cost_usd / max_sibling_cost) * 100%`
- Cost label (right-aligned)

Expand/collapse state is maintained in `state.expandedSessions` (a `Set` of session IDs). Toggling a row updates the set and calls `requestUpdate()` on `<acv-timeline>`.

### `<acv-timeline>`

Right panel. Contains three vertically stacked elements:

1. **Cost heatmap strip** (20px tall) — bucketed cost visualization
2. **Time ruler** — tick marks and timestamps; wheel events on this element zoom centered on cursor
3. **Canvas Gantt** — single `<canvas>` spanning the full timeline width

The canvas redraws on every `state` change that affects visible spans. The detail panel (`<acv-detail>`) is a child of this component and slides up when `state.selectedSpan` is non-null.

### `<acv-detail>`

Slides up from the bottom of the timeline area when a span is clicked. Displays:
- Provider and model
- Start time, end time, duration
- Token breakdown: input / output / cache_read / cache_write / total
- Cost in USD
- Input and output content (when available from the span data)

Dismissed by pressing `Escape` or clicking elsewhere.

## Data Flow

```
Browser                           FastAPI
  │                                  │
  ├─ GET /api/sessions?limit=25 ────►│
  │◄─ [{id, name, cost, ...}] ───────┤
  │                                  │
  ├─ GET /api/sessions/{id} ────────►│
  │◄─ full session tree ─────────────┤
  │                                  │
  ├─ GET /api/sessions/{id}/spans ──►│
  │◄─ flat span list ────────────────┤
  │                                  │
  state.sessions / state.spans updated
  requestUpdate() called on all components
  Canvas redraws via RAF
```

On initial load: fetch sessions list, populate dropdown. On session selection: fetch session tree and flat spans in parallel, update state, trigger full redraw.

## State Model

Single global object. All components read from it; updates call `requestUpdate()` on affected components explicitly.

```javascript
const state = {
  sessions: [],           // paginated list from /api/sessions
  sessionsOffset: 0,
  sessionsHasMore: false,
  activeSessionId: null,
  sessionData: null,      // full tree from /api/sessions/{id}
  spans: [],              // flat span list from /api/sessions/{id}/spans
  expandedSessions: new Set(),
  selectedSpan: null,
  timeScale: 1,           // ms per CSS pixel
  scrollLeft: 0,          // canvas horizontal scroll in pixels
};
```

No observable proxy, no Proxy traps. Mutations are explicit; callers own the `requestUpdate()` call after mutation.

## Canvas Drawing Architecture

### Pre-computation (before each draw)

```javascript
const spanStartPx = spans.map(s => s.start_ms / state.timeScale);
const spanWidthPx = spans.map(s => Math.max(2, (s.end_ms - s.start_ms) / state.timeScale));
```

Spans are grouped by color into batches ahead of the draw call. Minimum span width of 2px ensures every span is at least visible at all zoom levels.

### Draw loop (executed inside `requestAnimationFrame`)

1. **Clear** — `ctx.clearRect(0, 0, canvas.width, canvas.height)`
2. **Row backgrounds** — alternating light/dark horizontal bands, one per visible session row
3. **Time grid lines** — vertical lines at ruler tick positions
4. **Color-batched span drawing:**
   ```
   for each color group:
     ctx.beginPath()
     for each span in group:
       if span is outside viewport → skip (visibility culling)
       ctx.rect(x, y, w, h)
     ctx.fillStyle = color
     ctx.fill()
   ```
5. **Text labels** — drawn only when a span's rendered width exceeds 60px; content is `model_name + " $" + cost`
6. **Gap labels** — orchestrator idle-time labels drawn in dark spaces between spans

### Zoom and Pan

`state.timeScale` is ms-per-CSS-pixel. Zoom in → smaller value (fewer ms per pixel → wider spans). Zoom out → larger value.

Pan is `state.scrollLeft` in pixels. All span X positions are computed as `spanStartPx - state.scrollLeft`.

## Cost Heatmap

A 20px strip between the toolbar and the ruler. Computed client-side by bucketing `cost_usd` from all visible spans into N columns, where N equals the canvas width in pixels divided by 4 (one bucket per 4px).

Each column's background opacity:

```
opacity = cost_in_bucket / max_bucket_cost
color   = rgba(123, 47, 190, opacity)   // Anthropic purple
```

A thin amber (`#f59e0b`) vertical marker `|` is drawn on the peak-cost bucket.

The heatmap redraws on every zoom or pan event because the bucket width changes with `state.timeScale`.

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `W` / `=` | Zoom in (scale × 0.7) |
| `S` / `-` | Zoom out (scale × 1.3) |
| `A` / `←` | Pan left 150px |
| `D` / `→` | Pan right 150px |
| `Shift+W` / `Shift+=` | Zoom in 3× faster |
| `Shift+S` / `Shift+-` | Zoom out 3× faster |
| `Escape` | Close detail panel |

Keyboard events are captured on `document`. All zoom changes are RAF-debounced — a single pending `requestAnimationFrame` handle is reused, never stacked.

Wheel events on `#time-ruler` zoom centered on the cursor's X position (no modifier key needed).

## File Structure

```
viewer/amplifier_app_cost_viewer/static/
├── index.html              ← updated: defines 4 custom elements, imports from vendor
├── style.css               ← redesigned: layout, component styles, no SVG rules
├── app.js                  ← rewritten: 4 Lit components + Canvas renderer + state
└── vendor/
    └── lit.all.min.js      ← Lit 3 vendored from CDN, downloaded once, served as static
```

No build step. No TypeScript. No `package.json`. The vendor file is a one-time download; after that, the app runs fully offline from the FastAPI static server.

## What Is Not Changing

| File | Status |
|------|--------|
| `server.py` | Unchanged |
| `reader.py` | Unchanged |
| `pricing.py` | Unchanged |
| `pyproject.toml` | Unchanged |
| All Python tests | Unchanged |
| All API endpoints | Contract unchanged |

The backend is considered complete and correct. No new endpoints are required.

## Error Handling

- **Network errors on session load** — show an error message in the session dropdown; do not crash the component
- **Empty span list** — render an empty canvas with a "No spans" label; do not divide by zero in heatmap computation
- **Span outside viewport** — skip during draw loop (visibility culling), not an error
- **Detail panel with missing fields** — render available fields only; omit sections for absent data (e.g., no input/output content)

## Migration Plan

1. Download `lit.all.min.js` from the Lit CDN to `static/vendor/`
2. Rewrite `index.html` — register 4 custom elements, import Lit from `vendor/lit.all.min.js`
3. Rewrite `app.js` — 4 `HTMLElement` subclasses using `Lit.render()` in shadow roots, Canvas renderer, state model, keyboard handler
4. Rewrite `style.css` — new layout rules, component styles, remove all SVG-specific rules
5. Manual browser verification against real session data
6. Remove old SVG-specific test assertions; add canvas smoke tests

## Testing Strategy

- **Existing Python tests** — run unmodified; all must continue to pass
- **Canvas smoke tests** — verify that selecting a session causes at least one `ctx.fill()` call (mock canvas context)
- **Browser verification** — manual walkthrough: load sessions, select one, zoom in/out with W/S, pan with A/D, click a span, verify detail panel content, collapse tree rows, verify Gantt rows disappear

## Success Criteria

| Criterion | Target |
|-----------|--------|
| Session list load | < 2 seconds |
| Gantt render after session select | < 500ms |
| Zoom/pan frame rate | 60fps, no visible jank |
| Heatmap updates on zoom | Yes |
| Tree expand/collapse ↔ Gantt rows | Instant, in sync |
| W/A/S/D keyboard navigation | Working |
| Detail panel on span click | Full span data shown |
| Existing backend tests | All pass |

## Open Questions

None. All design decisions were validated before this document was written.
