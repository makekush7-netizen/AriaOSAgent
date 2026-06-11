# ARIA — Design System & UI Specification
### FAR AWAY 2026 | Version 2.0

---

## 1. Design Philosophy

ARIA's UI is not a SaaS dashboard. It is not a chat application. It is a **digital environment** — a personal space the user inhabits, not a tool they open and close.

The design must pass three tests:
1. **The first 5 seconds test** — someone watching the demo screen from across the room should say "what is that?" not "oh, another AI chatbot."
2. **The personality test** — the interface has a mood. It feels warm, alive, and slightly magical. Not corporate. Not cold.
3. **The focus test** — at any given moment, there is one clear thing the user is looking at. The UI never competes with itself for attention.

---

## 2. Design Tokens

### Color Palette

```css
/* Core backgrounds — layered depth */
--bg-world:       #0a0a0f;    /* Deepest layer — the "sky" behind everything */
--bg-base:        #0f0f16;    /* App base layer */
--bg-surface:     #16161f;    /* Cards, panels */
--bg-elevated:    #1e1e2a;    /* Active panels, focused state */
--bg-overlay:     rgba(22, 22, 31, 0.85); /* Glassmorphic panels */

/* Gold accent system — ARIA's signature */
--gold-primary:   #e8c97a;    /* Primary gold — headings, active states */
--gold-dim:       #c4a55a;    /* Secondary gold — supporting elements */
--gold-glow:      rgba(232, 201, 122, 0.15); /* Ambient gold glow */
--gold-glow-soft: rgba(232, 201, 122, 0.06); /* Very subtle gold wash */

/* Semantic colors */
--accent-teal:    #4fd1c7;    /* Sub-agent BrowserBot */
--accent-purple:  #9b7ff4;    /* Sub-agent ScriptRunner */
--accent-coral:   #f4956a;    /* Warnings, HITL interrupts */
--accent-green:   #6bcf7f;    /* Success states, completed steps */
--accent-red:     #f46a6a;    /* Errors, cancel actions */

/* Text */
--text-primary:   #f0ede8;    /* Main readable text */
--text-secondary: #a09a90;    /* Supporting text, labels */
--text-muted:     #5a5550;    /* Placeholder text, disabled */
--text-gold:      #e8c97a;    /* ARIA's spoken words, highlights */

/* Glass */
--glass-border:   rgba(232, 201, 122, 0.12);  /* Panel borders */
--glass-border-active: rgba(232, 201, 122, 0.3); /* Active/focused panel borders */
```

### Typography

```css
/* Font stack — loaded via app bundle, no Google Fonts dependency */
--font-display:  'Space Grotesk', sans-serif;   /* Headers, ARIA's name */
--font-body:     'Inter', sans-serif;           /* UI text, labels */
--font-mono:     'JetBrains Mono', monospace;   /* Code canvas, logs */

/* Scale */
--text-2xs:  10px;
--text-xs:   12px;
--text-sm:   13px;
--text-base: 14px;
--text-md:   16px;
--text-lg:   20px;
--text-xl:   24px;
--text-2xl:  32px;
--text-3xl:  48px;

/* Weight */
--weight-regular: 400;
--weight-medium:  500;
--weight-semibold: 600;
--weight-bold:    700;
```

### Spacing

```css
/* 4px base unit */
--space-1:   4px;
--space-2:   8px;
--space-3:   12px;
--space-4:   16px;
--space-5:   20px;
--space-6:   24px;
--space-8:   32px;
--space-10:  40px;
--space-12:  48px;
--space-16:  64px;
```

### Elevation & Glass

```css
.glass-panel {
  background: var(--bg-overlay);
  backdrop-filter: blur(20px) saturate(1.4);
  -webkit-backdrop-filter: blur(20px) saturate(1.4);
  border: 1px solid var(--glass-border);
  border-radius: 16px;
}

.glass-panel:hover,
.glass-panel.active {
  border-color: var(--glass-border-active);
  box-shadow: 0 0 24px var(--gold-glow);
}

/* Depth layers via box-shadow only — no backdrop stacking */
.elevation-1 { box-shadow: 0 2px 8px rgba(0,0,0,0.4); }
.elevation-2 { box-shadow: 0 4px 20px rgba(0,0,0,0.5), 0 0 12px var(--gold-glow-soft); }
.elevation-3 { box-shadow: 0 8px 40px rgba(0,0,0,0.6), 0 0 24px var(--gold-glow); }
```

### Animation Tokens

```css
--ease-out-smooth: cubic-bezier(0.16, 1, 0.3, 1);     /* Panels sliding in */
--ease-spring:     cubic-bezier(0.34, 1.56, 0.64, 1);  /* Character reactions */
--ease-gentle:     cubic-bezier(0.4, 0, 0.2, 1);       /* Standard transitions */

--duration-instant: 80ms;
--duration-fast:   150ms;
--duration-normal: 250ms;
--duration-slow:   400ms;
--duration-enter:  500ms;   /* Panel entrance animations */
```

---

## 3. The Background World

The background is an animated scene — not a static wallpaper. It gives the interface life and sets the tone. It is subtle enough to never distract from the content in the foreground.

### Default Theme: Night Garden
A very dark, desaturated scene with:
- A suggestion of distant rooftops or a garden at the edges
- Soft particle drift (cherry blossoms or light motes) using CSS canvas animation
- A warm ambient light source from behind the character suggesting a lamp or window

**Implementation — pure CSS + Canvas (no heavy 3D library):**
```typescript
// BackgroundCanvas.tsx
// Lightweight particle system — 40 particles max, requestAnimationFrame
// Each particle: x, y, size, opacity, drift speed, rotation
// Blossoms drift downward-left, fade in/out gently
// Total CPU impact: < 1% on modern hardware
```

### Alternate Themes (selectable in settings):
- **Cherry Blossom Day** — soft pink light, daytime warmth, petals falling
- **Rainy Window** — dark blue tones, rain streaks on a virtual window
- **Deep Space** — near-black, slow nebula drift, cold blue-purple tones
- **Lo-fi Room** — a suggestion of a cozy desk setup, warm yellow lamp, bookshelf edges

Theme data is a JSON object with: background color, particle type, particle color, ambient light color, character lighting color. Users can create and share custom themes via the marketplace.

---

## 4. Application Layout — Full Window Mode

```
┌─────────────────────────────────────────────────────────────────────┐
│ BACKGROUND WORLD (full window, z-index: 0)                          │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ TOP BAR (z-index: 10) — thin, 40px                           │  │
│  │  [ARIA logo + name]          [Home][Memory][Store][Settings] │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌────────────────────┐    ┌──────────────────────────────────────┐ │
│  │ CHARACTER ZONE     │    │ CANVAS / CONTENT ZONE                │ │
│  │ (left 40%)         │    │ (right 60%)                          │ │
│  │                    │    │                                      │ │
│  │  VRM Character     │    │ State-dependent content:             │ │
│  │  (3D canvas)       │    │  - Home: quick action widgets        │ │
│  │                    │    │  - Conversation: chat panel          │ │
│  │  Status line:      │    │  - Planning: approval card           │ │
│  │  "Active Task..."  │    │  - Execution: Task Canvas            │ │
│  │                    │    │  - Completion: summary card          │ │
│  └────────────────────┘    └──────────────────────────────────────┘ │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ BOTTOM BAR (z-index: 10) — 60px                              │  │
│  │  [Voice Mode: Active/Inactive]  [🎙️ WAVEFORM]  [type here] │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Top Bar
Height: 40px. Background: transparent — the world shows through. Left: ARIA wordmark in Space Grotesk, gold. Right: navigation icons (no text labels in icon-only mode, tooltips on hover). The nav has NO active "page" styling — it uses subtle gold underline only.

### Character Zone
The 3D canvas fills this zone completely. The character stands or sits at roughly 70% height of the zone. Subtle circular glow beneath the character (the platform reimagined as a floor light). The character is never cropped at the edges — breathing room is important.

### Canvas Zone
In Home State, this area contains draggable glassmorphic widgets (clock, active task status, recent tasks, quick action chips). In Execution State, the Task Canvas takes over this entire area. Widgets can be moved by dragging. Layout is saved to settings.json.

### Bottom Bar
The voice interface lives here permanently. The waveform visualizer pulses when TTS is playing or microphone is active. The text input is a clean single-line field with placeholder "Press to speak or type a message..." When an agent is executing, a subtle "Agent running..." indicator appears above the waveform.

---

## 5. State-by-State Visual Specification

### Home State

Character is the visual anchor. The canvas zone shows up to 4 widget cards arranged in a 2×2 grid (or user-customized layout):

```
┌─────────────────────┐  ┌─────────────────────┐
│ 🕐 14:32            │  │ ⚡ Active Task        │
│    Thursday         │  │    Idle              │
│    June 11          │  │                      │
└─────────────────────┘  └─────────────────────┘
┌─────────────────────┐  ┌─────────────────────┐
│ 🧠 Memory           │  │ 🏪 Quick Actions     │
│    7 items stored   │  │  [Fill Form]         │
│    [View All]       │  │  [Research]          │
│                     │  │  [Send Emails]       │
└─────────────────────┘  └─────────────────────┘
```

Each widget: glass panel, 1px gold border, subtle gold glow on hover. Font: --text-sm for labels, --text-md for values.

### Conversation State

The canvas zone transitions to the chat panel. Animation: slide in from right, 400ms ease-out-smooth. Character slightly turns toward the chat zone and shifts to listening expression.

Chat panel design:
- ARIA messages: left-aligned, gold text on transparent background, ARIA avatar initials icon
- User messages: right-aligned, --bg-elevated background pill, --text-primary color
- Timestamps: --text-muted, --text-xs, appear on hover only
- No avatar images in chat — the 3D character IS the avatar

The chat input in the bottom bar gains a gold focus ring when Conversation State is active.

### Planning State

A Planning Card slides in over the canvas zone. The character adopts the "thinking" expression and animation.

```
┌──────────────────────────────────────────────────────────────────┐
│  🎯  Task: Fill Hackathon Registration on Unstop               │
│──────────────────────────────────────────────────────────────────│
│  ARIA's Understanding:                                           │
│  Navigate to unstop.com, find the active registration form,     │
│  fill all fields using your memory profile, pause for any       │
│  unknown fields.                                                 │
│                                                                  │
│  Execution Plan:                    Permissions Needed:          │
│  ○ Open browser to unstop.com       ✅ Browser access           │
│  ○ Locate registration form         ✅ Memory read              │
│  ○ Inject DOM overlay               ⚠️ Form submission          │
│  ○ Autofill known fields (7)                                     │
│  ○ Pause for unknown fields                                      │
│  ○ Submit on confirmation                                        │
│                                                                  │
│  Information Gaps:       [None — all fields covered by memory]  │
│                                                                  │
│  [  Cancel  ]                              [  ✓ Approve & Run  ]│
└──────────────────────────────────────────────────────────────────┘
```

The "Approve & Run" button: gold fill, black text, 16px border-radius, 200ms scale animation on click. The "Cancel" button: transparent, gold border, gold text.

Execution plan steps use circle indicators: empty circle = pending, pulsing circle = active, filled gold circle = complete, red circle = error.

### Execution State

The Task Canvas takes over the canvas zone. The character shrinks to a small floating widget in the bottom-left of the canvas zone (about 15% of its original display size) with just the head visible. Sub-agent chips appear as floating cards in the top-right area.

**Sub-agent chip:**
```
┌────────────────────────────────┐
│  🤖 BrowserBot                 │
│  Filling field 4 of 9...      │
│  ▂▄▆█▆▄▂▄▆  ●  online         │
│                      [Pause]  │
└────────────────────────────────┘
```

Chip border color matches the agent's accent color (teal for BrowserBot, purple for ScriptRunner). The heartbeat line is an animated SVG path, not a static icon. Width: 220px. Position: top-right of canvas zone, stacked vertically if multiple agents.

### Completion State

Canvas closes with a scale-down animation (500ms). Character returns to center with a scale-up and "success" expression. A completion card appears briefly:

```
┌──────────────────────────────────────────────────────────────────┐
│  ✅  Task Complete                                               │
│──────────────────────────────────────────────────────────────────│
│  Form submitted successfully to Unstop.                          │
│  7 fields autofilled from memory.                                │
│  1 field filled from your input (Team Code: Y2K26-016)           │
│                                                                  │
│  Memory updated with 1 new item.                                 │
│                                                                  │
│  [  View Notepad  ]                          [  Done  ]          │
└──────────────────────────────────────────────────────────────────┘
```

This card auto-dismisses after 8 seconds or on "Done" click. After dismiss, returns to Home State.

---

## 6. Task Canvas Specifications

### Form Canvas
```
Left panel (40%): Live Chromium browser view embedded as webview
Right panel (60%):
  - Field list with status badges (autofilled / needs input / approved)
  - HITL interrupt zone: appears when agent pauses for unknown field
  - Action log: last 5 actions in --font-mono, --text-xs
  - Control buttons: [Pause] [Override Field] [Skip] [Abort]
```

### Certificate Canvas
```
Top row: two upload zones side by side
  Left: "Drop template image" (PNG/JPG) — shows preview on upload
  Right: "Drop CSV file" — shows column headers on parse

Center: Live preview of certificate with overlaid text
  - Draggable text position handles
  - Font selector dropdown (5 curated options: serif, sans, handwritten)
  - Font size slider
  - Color picker (foreground text color)

Bottom row:
  - "Preview All" — shows 3 sample previews using first 3 rows of CSV
  - Progress bar (appears during generation)
  - "Generate [N] Certificates" — runs ScriptRunner
  - Output folder path display after completion
```

### Research Canvas
```
Header: Query + sub-questions as tag pills

Body (scrollable):
  - Per sub-question sections
  - Each section: synthesized finding paragraph + [N sources] expandable
  - Source cards (expandable): site name, URL, extracted quote, credibility signal

Footer:
  - Export as Markdown button
  - Export as PDF button
  - "Ask follow-up" quick input
```

### Email Blast Canvas
```
Left panel (45%):
  Template editor:
    - Rich text (bold, italic, links only — no full formatting)
    - Variable chips: {{name}}, {{email}}, {{college}} — click to insert
    - Subject line input at top

Right panel (55%):
  Top: CSV drop zone → shows parsed preview table (name, email columns)
  Middle: Preview toggle — shows rendered email for first recipient
  Bottom:
    - Rate limit selector: [Slow (1/min)] [Normal (5/min)] [Fast (20/min)]
    - "Send to [N] recipients" — triggers ScriptRunner
    - Progress counter during send
```

---

## 7. Floating Widget Mode (Overlay on Desktop)

When the user minimizes to widget mode, the main window hides and the Tauri widget window appears. This is a transparent 300×400px always-on-top window showing only the character's upper body.

The character appears to stand on top of whatever application the user has open. Hit-testing is enabled — clicks pass through transparent areas, only the character mesh captures mouse events.

**Widget state:**
- Idle: character breathes, occasionally looks around
- Click on character: expands to full window
- Right-click: context menu with quick actions (Fill form on this page, Research this topic, Open ARIA)
- Active agent: a small pulsing gold dot appears above the character's head
- HITL interrupt: character taps her chin animation + a small toast notification appears

**Widget size options:** Small (150×200), Medium (300×400), Large (450×600). Resizable by dragging the character's feet area (invisible resize handle).

---

## 8. Component Library

### ARIAButton
```typescript
type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
type ButtonSize = 'sm' | 'md' | 'lg'

// primary: gold fill, black text, gold hover glow
// secondary: transparent, gold border, gold text
// ghost: transparent, --text-secondary, subtle hover bg
// danger: transparent, --accent-red border, --accent-red text
```

### ARIACard (Glass Panel)
```typescript
interface ARIACardProps {
  variant?: 'default' | 'active' | 'elevated'
  draggable?: boolean
  onDragEnd?: (position: Position) => void
  children: React.ReactNode
}
// All cards use glass-panel CSS class as base
// active variant gets gold border and elevation-2 shadow
// draggable cards get a subtle drag handle indicator on hover
```

### StatusIndicator
```typescript
type Status = 'idle' | 'active' | 'success' | 'error' | 'warning'
// idle: dim grey dot
// active: pulsing gold dot (CSS keyframe animation)
// success: solid green dot
// error: solid red dot
// warning: pulsing coral dot
```

### StepList (Execution Plan)
```typescript
interface Step {
  id: string
  label: string
  status: 'pending' | 'active' | 'complete' | 'error' | 'skipped'
}
// Each step renders a circle indicator + label
// active step: pulsing circle with gold fill
// complete step: solid gold fill with checkmark
// error: red fill with X
```

### WaveformVisualizer
```typescript
// Uses Web Audio API AnalyserNode
// 32 bars, rendered on canvas element
// Bars animate in real-time from audio frequency data
// Color: gold (#e8c97a) during TTS playback
// Color: teal (#4fd1c7) during microphone active (listening)
// Color: muted grey during idle
```

---

## 9. Micro-interactions & Motion

Every meaningful action should have a motion response. Animations should be fast enough to not slow the user down but present enough to feel alive.

**Panel transitions:** Slide from the direction that makes spatial sense. Chat panel comes from the right. Planning card drops from the top. Canvas expands from center.

**Character reactions:**
- Receiving a message → slight "head nod" (Y-axis bone rotation, 150ms)
- Task approved → small "ready" bounce (Y-position keyframe, 200ms spring)  
- Error → subtle head shake (X-axis rotation, 300ms)
- Task complete → shoulder relax animation (global pose ease, 400ms)

**HITL interrupt:** The chat input ring pulses three times in --accent-coral before the HITL modal appears. This draws the user's eye to the interface.

**Sub-agent spawn:** The chip animates in from the top-right corner with a scale+fade, 250ms ease-spring. Despawn: scale down + fade, 200ms.

**Success particles:** On task completion, 12 small gold particles burst from the character's hands and disperse. Duration: 600ms. Pure CSS/Canvas, no library.

---

## 10. Things To Never Do

This section is as important as everything above.

- **Never use white backgrounds.** Even modals stay dark.
- **Never use blue as a primary accent.** Blue feels like any other SaaS tool. Gold is ARIA's identity.
- **Never show an empty state without the character.** If content is loading or missing, the character fills the space.
- **Never use standard HTML alert/confirm dialogs.** All system dialogs are replaced with ARIACard modals.
- **Never stack more than 3 glassmorphic panels in the same view.** Glass on glass on glass loses all depth.
- **Never autoplay TTS at full volume.** Start at 70%, user-adjustable.
- **Never make the character disappear entirely.** Even in heavy Execution State, she's visible as a small widget.
- **Never show raw JSON or stack traces to the user.** All errors get a friendly ARIA narration and a clean error card.
- **Never add a loading spinner without a character state change.** ARIA's "thinking" animation IS the loading state.
