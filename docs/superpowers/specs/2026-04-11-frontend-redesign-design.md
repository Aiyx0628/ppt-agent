# Frontend Redesign: SANDUN-Inspired Layout

**Date:** 2026-04-11  
**Scope:** ppt-agent-desktop renderer (`src/renderer/`)  
**Reference:** https://sandun.cc/

---

## Overview

Comprehensive redesign of the desktop frontend to adopt a SANDUN-inspired three-column layout. The visual style (blue gradient background, glassmorphism cards) is preserved; only layout, information architecture, and interaction patterns change.

Key goals:
- Intake page becomes a full-screen welcome experience with a persistent project history sidebar
- Editor page becomes a three-column layout: slide rail | main stage | AI chat panel
- Chat panel enables post-generation editing without page navigation

---

## 1. Architecture & Component Map

### New component structure

| Component | Replaces / Extends | Notes |
|-----------|-------------------|-------|
| `<Sidebar>` | (new) | Shared shell, switches content based on page view |
| `<IntakeView>` | `.intake-shell` / `.intake-panel` | Full-screen, left-right split |
| `<EditorTopbar>` | `.editor-topbar` | Adds back button; stage tabs move here from rail |
| `<SlideRail>` | `.slide-rail` | Remove rail-stage-switch; thumbnails move up |
| `<MainStage>` | `.editor-main` | Unchanged content, adjusted container |
| `<ChatPanel>` | (new) | Right-side fixed 320px panel |

### Page skeleton

**Intake page:**
```
[Sidebar 220px] | [Main content area — flex]
```

**Editor page:**
```
[EditorTopbar — full width]
[SlideRail 220px] | [MainStage — flex] | [ChatPanel 320px]
```

---

## 2. Intake Page

### Sidebar (project history)

- Width: 220px, fixed
- Background: `rgba(255,255,255,0.56)` + `backdrop-filter: blur(18px)`
- Border-right: `1px solid rgba(216,223,235,0.82)`
- Contents (top to bottom):
  - Brand name "ppt-agent" (`.intake-brand` style)
  - "新建项目" primary button
  - Separator + "最近" label
  - Project list: each item shows title (truncated) + stage badge
    - Hover: `var(--surface-muted)` background
    - Active: `var(--blue-soft)` background + 3px left blue border
  - Empty state: "暂无记录" centered muted text
  - Bottom: settings icon button (fixed)

### Main content area

- Full height, centered vertically (flex column, justify-content: center)
- Greeting heading (48–56px, fontWeight 800, dynamic by time of day):
  - 06:00–11:59 → "早上好，"
  - 12:00–17:59 → "下午好，"
  - 18:00–05:59 → "晚上好，"
  - Second line: "准备生成什么 PPT？"
- Subtitle: "AI 生成定制级、可编辑的 PPT" (14px, `var(--muted)`)
- Input box: existing `.intake-textarea` style, `min-height` reduced from 320px to 160px
- Toolbar row below input: file attach button (left) + submit button (right)
- Quick-suggestion chips: 3–4 preset topic pills (`.file-chip` style), click fills textarea
- "最近项目" grid (only when projects exist):
  - 3-column card grid
  - Each card: project title + created date + current stage badge
  - Click → navigate directly to editor for that project

---

## 3. Editor Page

### Top navigation bar

- Height: 64px
- Background: `rgba(255,255,255,0.78)` + `backdrop-filter: blur(18px)`
- Border-bottom: `1px solid rgba(216,223,235,0.9)`
- Mac: `padding-left: 88px`
- Layout: `grid-template-columns: auto 1fr auto`
  - Left: back button (← icon, `.ghost-button` style) → returns to intake without reload
  - Center: project title (truncated, max-width 400px) + existing `.stage-tabs` switcher
  - Right: export dropdown button (existing `.export-button`)

### Slide rail (left, 220px)

- Existing `.slide-rail` styles, with one change: remove `.rail-stage-switch` (stage switching moves to topbar)
- Slide thumbnails expand to fill vacated space

### Main stage (center, flex)

- Existing three stage views unchanged:
  - Search: `.search-layout` master-detail
  - Draft: `.stage-preview-shell` + artboard
  - Design: `.stage-preview-shell` + SVG preview + review panel
- Container: `min-height: 0`, `overflow: hidden`, `flex: 1`

### Chat panel (right, 320px, new)

- Fixed width 320px, full editor height
- Background: `rgba(255,255,255,0.86)` + `backdrop-filter: blur(18px)`
- Border-left: `1px solid rgba(216,223,235,0.82)`
- Layout (top to bottom):
  - Stage badge header: current stage label (搜索 / 初稿 / 设计稿)
  - Message list (flex-grow: 1, overflow-y: auto, padding 14px):
    - AI progress messages (e.g. "正在搜索…", "已生成 14 页设计稿")
    - Auto-scroll to bottom on new message
    - `isBusy` state: spinner + "处理中…" message
  - Input area (fixed bottom):
    - Textarea: "输入修改需求…" placeholder
    - Attach button + send button (`.submit-button` style, disabled when `isBusy`)
    - Hint text: "Enter 发送，Shift+Enter 换行"
- Empty state (no messages yet): centered icon + "生成完成后，可在这里修改内容"
- Backend: chat submit triggers existing API calls based on current stage; responses update workspace state

---

## 4. What Does NOT Change

- All CSS custom properties (color tokens, shadows)
- Background gradient on `body`
- Glassmorphism card styles (`.workspace-card`, `.intake-panel` base styles)
- All three stage content components (search/draft/design) — logic and markup unchanged
- Export dropdown behavior
- Slide thumbnail rendering logic
- All TypeScript types in `types.ts`
- API service layer (`services/api.ts`)

---

## 5. Files to Modify

| File | Change |
|------|--------|
| `src/renderer/App.tsx` | Full restructure: add Sidebar, IntakeView overhaul, Editor three-column layout, ChatPanel |
| `src/renderer/styles.css` | Add new layout classes; keep all existing classes |

No new files needed — all new components live as functions inside `App.tsx` (consistent with current pattern).

---

## 6. Out of Scope

- Backend / API changes
- Authentication or subscription UI
- Dark mode
- Mobile / responsive breakpoints beyond existing media queries
- Slide drag-and-drop reordering (existing behavior preserved)
