# ppt-agent workspace

Monorepo for the `ppt-agent` Python backend and the `ppt-agent-desktop` Electron frontend.

## Structure

- `ppt-agent/`: Python backend managed by `uv`, targeting Python `3.13.12`
- `ppt-agent-desktop/`: Electron desktop app targeting Node `24`

## Quick start

### Backend

```bash
cd ppt-agent
uv sync
uv run ppt-agent
```

### Desktop

```bash
cd ppt-agent-desktop
npm install
npm run dev
```
