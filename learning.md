# learning.md

## Why Tauri wasn’t showing updated widget UI

### Symptom
- Changes made to the Tauri floating widget (3D-only girl, fullscreen on F11, hide cross, right-click menu, drag/drop behavior) were not appearing after rebuild / restart.

### Root cause (configuration-level)
- In `src-tauri/tauri.conf.json`, the **widget window URL** was not explicitly pinned to the widget entry file.
- This meant the widget window could end up loading the wrong HTML entry depending on how Tauri served content in dev/build modes (base paths / devUrl behavior).
- As a result, UI changes in `frontend/widget.html` + `frontend/src/widget.jsx` were not the code being rendered in the widget window.

### Fix applied
- Updated `src-tauri/tauri.conf.json` to explicitly define the URLs:
  - Main window: `url: "index.html"`
  - Widget window: `url: "/widget.html"`

This forces the widget window to load the correct entry (`frontend/widget.html` → mounts `frontend/src/widget.jsx`).

### Verification steps performed
- Stopped any running Tauri app process.
- Cleaned Rust build artifacts (`cargo clean`).
- Rebuilt frontend (`npm --prefix frontend run build`) so `frontend/dist/widget.html` and widget JS bundles were regenerated.
- Ran Tauri again (`cargo run --manifest-path src-tauri/Cargo.toml`).

### Note
- After this fix, any remaining mismatches (fullscreen/hide cross/drag-drop logic) should be handled inside `frontend/src/widget.jsx`, because Tauri will now reliably load the widget entry.

