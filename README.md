# ppt-agent workspace

Monorepo for the `ppt-agent` Python backend and the `ppt-agent-desktop` Electron frontend.

## Structure

- `ppt-agent/`: Python backend managed by `uv`, targeting Python `3.13.12`
- `ppt-agent-desktop/`: Electron desktop app targeting Node `24.13.0`

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

## Repository conventions

- Root `.editorconfig` applies to both subprojects
- Root `.gitignore` manages shared ignore rules for Python, Node, and macOS artifacts
- Backend source code lives under `ppt-agent/src/`
- Desktop source code lives under `ppt-agent-desktop/src/`


## 参考链接：


```bash
https://linux.do/t/topic/1782304
```
