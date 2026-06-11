# progress.md

## Progress update

### 1) Identified likely cause of stale widget UI
- Widget window could be loading the wrong entry page because `tauri.conf.json` didn’t explicitly pin the widget window URL.

### 2) Implemented config fix
- Updated `src-tauri/tauri.conf.json`:
  - main window `url: "index.html"`
  - widget window `url: "/widget.html"`

### 3) Rebuild/clean
- Cleaned Rust artifacts and ensured rebuild.
- Rebuilt frontend (`npm --prefix frontend run build`).

### 4) Current status
- After the rebuild, Tauri should now load `frontend/widget.html` and `frontend/src/widget.jsx` for the floating widget.
- If widget behavior still doesn’t match (F11 fullscreen, hide cross, right-click close, drag/drop), changes must be made in `frontend/src/widget.jsx`.

