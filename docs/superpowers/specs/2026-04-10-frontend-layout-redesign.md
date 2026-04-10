# Frontend Layout Redesign

**Date:** 2026-04-10  
**Scope:** `ppt-agent-desktop/src/renderer/App.tsx` + `styles.css`

---

## Goals

1. Simplify the topbar to reduce visual noise
2. Restructure the left sidebar: horizontal stage tabs on top, thumbnails below
3. Redesign the main content area per stage: search = citation master-detail; draft/design = full-width preview
4. Fix Electron window drag (currently dragging selects text instead of moving the window)

---

## Layout Overview

```
┌─────────────────────────────────────────────────────┐
│  返回输入          项目标题               导出 ▾    │  ← Topbar (draggable)
├──────────┬──────────────────────────────────────────┤
│搜索│初稿│设计│                                      │
│──────────│        Main content area                 │
│ 缩略图 1 │  (changes by stage, see below)           │
│ 缩略图 2 │                                          │
│   ...    │                                          │
└──────────┴──────────────────────────────────────────┘
```

---

## Part 1: Topbar

**Grid:** `auto 1fr auto` (left | center | right)

| Zone | Content |
|------|---------|
| Left | `返回输入` ghost button |
| Center | Project title (single line, truncated with ellipsis) |
| Right | `导出 ▾` dropdown button |

**Removed:**
- "预览" pill (redundant)
- "放映" button (no functionality yet)

**Electron window drag fix:**
- `.editor-topbar` gets `-webkit-app-region: drag`
- All `<button>` elements inside topbar get `-webkit-app-region: no-drag`
- `body` gets `-webkit-user-select: none` to prevent text selection during drag
- `input`, `textarea` keep `user-select: text` so users can still select text in input fields

---

## Part 2: Left Sidebar

**Width:** 220px (up from 148px)

**Structure (top to bottom):**
1. **Horizontal stage tabs** — three equal columns (`1fr 1fr 1fr`), height 36px each, style matches existing `.stage-tab` / `.stage-tab-active`
2. **Section header** — "幻灯片 / 共 N 页" label row
3. **Thumbnail list** — vertical scroll, thumbnails fill the new width automatically

**CSS changes:**
- `.rail-stage-switch`: change from `grid` (single column) to `grid-template-columns: 1fr 1fr 1fr`
- `.editor-body`: change `grid-template-columns` from `148px 1fr` to `220px 1fr`

---

## Part 3: Main Content Area

### Search stage — Citation master-detail

Two columns inside the main area:

```
┌──────────────────────┬─────────────────────────────┐
│  来源列表 (280px)    │  网页内容 (remaining width)  │
│                      │                             │
│  ● Citation 1 title  │  Title: ...                 │
│  ● Citation 2 title  │  URL: ...                   │
│    (selected, blue)  │  Snippet: ...               │
│  ● Citation 3 title  │                             │
└──────────────────────┴─────────────────────────────┘
```

- Left column (fixed 280px): list of all citations for the current slide; click to select
- Right column (flex 1): displays selected citation's title, URL, and snippet
- Default selection: first citation
- State: local `useState` for `selectedCitationIndex` inside `SearchWorkspace`
- If no citations: show a single empty-state card spanning both columns

### Draft stage — Full-width artboard preview

- Remove the left workspace-panel / right preview-panel split
- Show the artboard (title + blocks) centered, full-width
- Keep edit controls (编辑/保存 button) in the section header above the artboard
- Block reorder arrows remain inside each block card

### Design stage — Full-width SVG preview

- Remove the left workspace-panel / right preview-panel split  
- SVG preview fills the full main area, centered, 16:9 aspect ratio
- Two floating action buttons in the top-right corner of the preview frame:
  - `重新生成` (ghost style)
  - `检查` (ghost style)
- Review results: displayed as a panel **below** the SVG preview (not a drawer), toggled by the 检查 button; shows pass/fail and issue list

---

## CSS Changes Summary

| Selector | Change |
|----------|--------|
| `body` | Add `-webkit-user-select: none` |
| `input, textarea` | Add `user-select: text` (override above) |
| `.editor-topbar` | Add `-webkit-app-region: drag` |
| `.editor-topbar button` | Add `-webkit-app-region: no-drag` |
| `.editor-body` | `grid-template-columns: 220px 1fr` |
| `.rail-stage-switch` | `grid-template-columns: 1fr 1fr 1fr` (was single column) |
| `.slide-rail` | Width follows new 220px grid column |
| `.workspace-layout` | Remove (replaced by stage-specific layouts) |
| `.workspace-panel` | Remove (no longer used as a split panel container) |
| New: `.search-layout` | `display: grid; grid-template-columns: 280px 1fr` for search stage |
| New: `.citation-list` | Left citation list panel styles |
| New: `.citation-detail` | Right citation detail panel styles |
| New: `.design-action-bar` | Floating action buttons overlay on design preview |

---

## Component Changes Summary

| Component | Change |
|-----------|--------|
| `App` (editor JSX) | Remove `workspace-layout` split; render stage-specific full layouts |
| `SearchWorkspace` | Add `selectedCitationIndex` state; render two-column master-detail |
| `DraftWorkspace` | Render artboard directly (no left/right split); keep edit controls |
| `DesignWorkspace` | Render SVG full-width; add floating action bar; review panel below SVG |
| `SvgPreview` | Remove (merged into `DesignWorkspace`) |
| `SearchPreview` | Remove (merged into `SearchWorkspace`) |
| `DraftPreview` | Remove (merged into `DraftWorkspace`) |

---

## Out of Scope

- Slide drag-to-reorder (existing feature, unchanged)
- Intake page (no changes needed)
- Backend API changes (none required)
- "放映" functionality (deferred)
