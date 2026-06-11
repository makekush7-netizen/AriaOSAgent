# ARIA — Layout Design Specification
### FAR AWAY 2026 | Version 1.0 | Team Endeavour
**For use by:** AI coding agents (Claude, Gemini, Cursor, etc.)  
**Stack:** React 18 + Vite + TypeScript + Tailwind CSS + Three.js / @react-three/fiber + @pixiv/three-vrm + Zustand  
**Window target:** 1280×800px minimum, frameless Tauri window

---

## 0. How to Read This Document

Every section that describes a layout state includes:
1. An ASCII wireframe with exact proportions
2. Component breakdown with pixel/percentage dimensions
3. Animation spec for the transition into that state
4. Implementation notes for the AI building it

**Non-negotiable rules (applies to every state):**
- Never use white backgrounds. Every surface is dark.
- Gold (`#e8c97a`) is the only accent colour. No blue primary.
- The 3D VRM character is always visible — never fully hidden.
- All widget cards are draggable, resizable, and individually deletable.
- Glass morphism panels: `background: rgba(22,22,31,0.85)`, `backdrop-filter: blur(20px)`, `border: 1px solid rgba(232,201,122,0.12)`, `border-radius: 16px`.
- The character is always rendered by `@pixiv/three-vrm` on a Three.js canvas via `@react-three/fiber`. Never use a 2D illustration or SVG avatar.

---

## 1. Design Tokens (Canonical Reference)

All components must use these CSS custom properties. Do not hardcode colours.

```css
/* Backgrounds */
--bg-world:    #0a0a0f;
--bg-base:     #0f0f16;
--bg-surface:  #16161f;
--bg-elevated: #1e1e2a;
--bg-overlay:  rgba(22, 22, 31, 0.85);

/* Gold system */
--gold-primary:    #e8c97a;
--gold-dim:        #c4a55a;
--gold-glow:       rgba(232, 201, 122, 0.15);
--gold-glow-soft:  rgba(232, 201, 122, 0.06);

/* Semantic */
--accent-teal:   #4fd1c7;   /* BrowserBot */
--accent-purple: #9b7ff4;   /* ScriptRunner */
--accent-coral:  #f4956a;   /* HITL / warnings */
--accent-green:  #6bcf7f;   /* Success */
--accent-red:    #f46a6a;   /* Errors */

/* Text */
--text-primary:   #f0ede8;
--text-secondary: #a09a90;
--text-muted:     #5a5550;
--text-gold:      #e8c97a;

/* Glass borders */
--glass-border:        rgba(232, 201, 122, 0.12);
--glass-border-active: rgba(232, 201, 122, 0.30);

/* Typography */
--font-display: 'Space Grotesk', sans-serif;
--font-body:    'Inter', sans-serif;
--font-mono:    'JetBrains Mono', monospace;

/* Easing */
--ease-out-smooth: cubic-bezier(0.16, 1, 0.3, 1);
--ease-spring:     cubic-bezier(0.34, 1.56, 0.64, 1);
--ease-gentle:     cubic-bezier(0.4, 0, 0.2, 1);

/* Durations */
--dur-fast:   150ms;
--dur-normal: 250ms;
--dur-slow:   400ms;
--dur-enter:  500ms;
```

---

## 2. Application Shell (Persistent Across All States)

The shell is the fixed chrome that never changes. Everything else renders inside it.

```
┌────────────────────────────────────────────────────────────────────────┐
│  TOP BAR — 40px — transparent, always on top (z-10)                   │
│  [● ARIA]                          [⌂] [🧠] [🏪] [⚙]                │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  MAIN AREA — fills remaining height (window height − 40px − 52px)     │
│  Contents vary by app state (see sections 3–7)                        │
│                                                                        │
├────────────────────────────────────────────────────────────────────────┤
│  BOTTOM BAR — 52px — voice interface, always visible (z-10)           │
│  [🎤] [~~~waveform~~~] [  Press to speak or type...  ] [➤]           │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Top Bar

| Property | Value |
|---|---|
| Height | 40px |
| Background | `transparent` (world shows through) |
| Backdrop filter | `blur(8px)` |
| Border-bottom | `1px solid rgba(232,201,122,0.08)` |
| z-index | 10 |

**Left side:** ARIA wordmark
- Font: `Space Grotesk`, 16px, weight 700, colour `--gold-primary`
- Letter-spacing: `0.12em`
- Preceded by a 6×6px pulsing gold dot (CSS keyframe `opacity` + `scale`, 2.5s loop)

**Right side:** Navigation icons (icon-only, tooltip on hover)
- Icons: Home, Brain (Memory), Store, Settings
- Default colour: `--text-secondary`
- Hover: `--gold-primary`, background `rgba(232,201,122,0.08)`, border-radius 6px
- Active nav item: `--gold-primary`, 1.5px gold underline, no background fill
- No text labels in default mode

### 2.2 Bottom Bar

| Property | Value |
|---|---|
| Height | 52px |
| Background | `rgba(10,10,15,0.5)` |
| Backdrop filter | `blur(8px)` |
| Border-top | `1px solid rgba(232,201,122,0.07)` |
| z-index | 10 |

**Elements (left to right):**

1. **Voice button** — 30×30px circle, `rgba(232,201,122,0.1)` background, gold border, microphone icon
   - Active/listening state: teal background `rgba(79,209,199,0.2)`, teal border, pulsing animation
2. **Waveform canvas** — 80×30px `<canvas>` element
   - 20 bars, animated via Web Audio API `AnalyserNode`
   - Idle: muted grey bars, slow drift
   - TTS playing: gold bars `#e8c97a`, high amplitude
   - Mic active: teal bars `#4fd1c7`, real-time frequency
3. **Text input** — flexible width (fills remaining space)
   - Background: `rgba(22,22,31,0.8)`, border `rgba(232,201,122,0.12)`, border-radius 8px
   - Placeholder: `--text-muted`
   - Focus ring: border `rgba(232,201,122,0.35)`
   - Font: Inter 12px
   - Sends on `Enter` key
4. **Send button** — 30×30px, gold fill `#e8c97a`, black icon, border-radius 7px
   - Hover: scale(1.05), gold box-shadow

**When agent is executing:** A `"Agent running..."` label (10px, `--text-muted`, with a pulsing coral dot) appears above the waveform as an overlay line.

---

## 3. State 1 — Home (Companion Mode)

**Trigger:** App launch, task completion dismiss, user clicks "Done"  
**Character size:** Large (dominant visual)  
**Purpose:** The "wow" screen. ARIA is present, the environment feels alive.

### 3.1 Layout

```
┌───────────────────────────────────────────────────────────────────────┐
│ TOP BAR                                                               │
├──────────────────────────────┬────────────────────────────────────────┤
│                              │                                        │
│   CHARACTER ZONE — 45%       │   WIDGET ZONE — 55%                   │
│                              │                                        │
│   Three.js canvas            │   ┌──────────────┐ ┌──────────────┐  │
│   VRM model, full height     │   │  Clock        │ │  Active Task │  │
│   Ambient glow beneath       │   │  Widget       │ │  Widget      │  │
│   character                  │   └──────────────┘ └──────────────┘  │
│                              │   ┌──────────────┐ ┌──────────────┐  │
│                              │   │  Memory       │ │  Quick       │  │
│   "Ready"                    │   │  Widget       │ │  Actions     │  │
│   status line                │   └──────────────┘ └──────────────┘  │
│                              │                                        │
├──────────────────────────────┴────────────────────────────────────────┤
│ BOTTOM BAR                                                            │
└───────────────────────────────────────────────────────────────────────┘
```

### 3.2 Character Zone (45% width)

| Property | Value |
|---|---|
| Width | 45% of main area |
| Background | transparent (world canvas shows through) |
| Three.js canvas | fills 100% of zone width, 100% of zone height |
| VRM model height | ~70% of zone height (breathing room above and below) |
| Ambient glow | Radial gradient beneath model feet, `rgba(232,201,122,0.10)`, 160px radius |
| Status text | 11px Inter, `--text-secondary`, centred below character, with 5×5px status dot |

**VRM Character specs:**
- Load from: `%APPDATA%/ARIA/characters/default_girl.vrm` (or bundled fallback)
- Camera: `PerspectiveCamera`, fov 35, positioned to frame character from waist up
- Idle animation: breathing cycle (chest bone Y offset, 0.6s ease in-out loop), occasional blink (0.1s), slow head sway (±3° Y-axis, 4s loop)
- Emotion on Home state: `idle`
- Lighting: one warm point light `#ffd4a0` from upper-left (character lamp direction), ambient `#1a1428` at 0.4 intensity

### 3.3 Widget Zone (55% width)

The widget zone uses a **free-form drag canvas** — not a rigid CSS grid. Widgets have a default 2×2 arrangement on first launch, but the user can rearrange them freely.

**Widget canvas behaviour:**
- Each widget is a draggable, resizable, deletable panel
- Drag handle: the entire widget header area (cursor `grab` / `grabbing`)
- Resize handle: 8×8px transparent hit-area at bottom-right corner (shows a subtle resize cursor on hover)
- Delete: a `×` button appears in the top-right of the widget on hover (12px, `--text-muted`, fades in on `opacity` transition)
- Deleting a widget removes it from view and from `settings.json`. It can be re-added from Settings.
- Widget positions and sizes are persisted to `settings.json` under `widget_layout`
- Minimum widget size: 140×100px
- Widgets cannot overlap each other (snap-to-avoid or slight push behaviour optional for v1)
- Widgets should not overlap the character zone

**Default widget layout (positions are suggestions, not hard constraints):**

```
[Clock]         [Active Task]
[Memory]        [Quick Actions]
```

Each widget is approximately 48% of the zone width × 44% of the zone height in the default layout, with 10px gaps.

### 3.4 Widget Specifications

All widgets share the same glass panel base:
```css
background: rgba(22, 22, 31, 0.82);
backdrop-filter: blur(16px) saturate(1.4);
border: 1px solid rgba(232, 201, 122, 0.10);
border-radius: 12px;
padding: 14px 16px;
transition: border-color 200ms, box-shadow 200ms;

:hover {
  border-color: rgba(232, 201, 122, 0.28);
  box-shadow: 0 0 18px rgba(232, 201, 122, 0.10);
}
```

**Widget: Clock**
```
┌──────────────────────┐
│ 🕐 TIME              │ ← label: 10px, --text-muted, uppercase
│                      │
│  14:32               │ ← 28px, Space Grotesk, --text-primary
│  Thursday, Jun 12    │ ← 11px, --text-secondary
└──────────────────────┘
```
- Time updates every second via `setInterval`
- Format: 24-hour `HH:MM`, locale: user's system locale

**Widget: Active Task**
```
┌──────────────────────┐
│ ⚡ ACTIVE TASK       │
│                      │
│  Idle                │ ← 13px, --text-secondary (when no task)
│  [active task name]  │ ← 13px, --gold-primary (when task running)
│  Click to begin →    │ ← 10px, --text-muted
└──────────────────────┘
```
- Clicking this widget when idle triggers conversation state
- When a task is active, shows task name + a pulsing gold status dot

**Widget: Memory**
```
┌──────────────────────┐
│ 🧠 MEMORY            │
│                      │
│  7  items stored     │ ← value: 20px Space Grotesk; label: 11px
│                      │
│  [email] student@... │ ← memory-tag chips: teal border, teal text
│  [roll]  2024CS042   │
│                      │
│  [View All]          │ ← ghost button, 11px
└──────────────────────┘
```
- Memory tags: `background: rgba(79,209,199,0.08)`, `border: 1px solid rgba(79,209,199,0.20)`, `color: #4fd1c7`, border-radius 4px, font-size 9px, padding 2px 6px
- Show top 2–3 most recent memory keys
- "View All" opens the Memory panel (nav)

**Widget: Quick Actions**
```
┌──────────────────────┐
│ ✦ QUICK ACTIONS      │
│                      │
│  [⬛ Fill Form     ] │ ← action chip
│  [🔍 Research     ] │
│  [✉ Email Blast   ] │
└──────────────────────┘
```
Action chips:
```css
background: rgba(232, 201, 122, 0.07);
border: 1px solid rgba(232, 201, 122, 0.14);
color: --gold-primary;
border-radius: 7px;
padding: 6px 10px;
font-size: 11px;
width: 100%;
text-align: left;
cursor: pointer;

:hover { background: rgba(232, 201, 122, 0.14); }
```
- Clicking "Fill Form" → transitions to Planning state with form fill intent pre-filled
- Clicking "Research" → transitions to Conversation state
- Clicking "Email Blast" → transitions to Planning state with email blast intent

---

## 4. State 2 — Conversation (Chat Mode)

**Trigger:** Wake word detected, user clicks voice button, user clicks any Quick Action that needs clarification, user clicks chat input  
**Character size:** Large (same as Home, slight expression change)  
**Purpose:** Natural back-and-forth. ARIA is listening.

### 4.1 Layout

The widget zone morphs into a chat panel. Character stays at 45%.

```
┌───────────────────────────────────────────────────────────────────────┐
│ TOP BAR                                                               │
├──────────────────────────────┬────────────────────────────────────────┤
│                              │                                        │
│   CHARACTER ZONE — 45%       │   CHAT PANEL — 55%                    │
│   (unchanged from Home)      │                                        │
│                              │   [A] Hey! What would you like...     │
│                              │                                        │
│   Expression: listening      │         Fill the hackathon form [user] │
│   Slight head tilt           │                                        │
│                              │   [A] Got it — let me build a plan.   │
│   Status: "Listening..."     │                                        │
│                              │   [A] ▋  (typing indicator)           │
│                              │                                        │
├──────────────────────────────┴────────────────────────────────────────┤
│ BOTTOM BAR — chat input gains gold focus ring                         │
└───────────────────────────────────────────────────────────────────────┘
```

### 4.2 Chat Panel Specs

**Transition in:** Widgets fade out (`opacity: 0`, 200ms), chat panel slides in from right (`translateX(24px) → translateX(0)`, 400ms `--ease-out-smooth`). Character does a slight "nod" (Y-bone rotation ±5°, 150ms).

**Panel container:**
```css
display: flex;
flex-direction: column;
gap: 8px;
padding: 16px 12px 8px 4px;
overflow-y: auto;
height: 100%;
/* Custom scrollbar */
scrollbar-width: thin;
scrollbar-color: rgba(232,201,122,0.15) transparent;
```

**Message: ARIA (left-aligned)**
```
[A]  Hey! What would you like me to do today?
```
- Avatar badge: 22×22px circle, `rgba(232,201,122,0.15)` bg, `rgba(232,201,122,0.25)` border, "A" in Space Grotesk 9px gold
- Bubble: no background, `color: --gold-primary`, font Inter 12px, line-height 1.6
- Timestamp: `--text-muted`, 10px, visible on hover only (`opacity` transition)
- Animate in: `opacity: 0 → 1`, `translateY(4px) → 0`, 200ms

**Message: User (right-aligned)**
```
                    Fill the hackathon form on Unstop [user]
```
- Bubble: `background: #1e1e2a`, `border: 1px solid rgba(232,201,122,0.10)`, `color: --text-primary`, padding 8px 12px, border-radius 10px 10px 2px 10px
- No avatar badge
- Animate in: `opacity: 0 → 1`, `translateX(4px) → 0`, 150ms

**Typing indicator:**
- Three dots with a staggered bounce animation (dot 1: delay 0ms, dot 2: 150ms, dot 3: 300ms)
- Colour: `--gold-dim`
- Only shown while awaiting LLM response

**Auto-scroll:** Chat panel scrolls to the latest message on every new message added.

---

## 5. State 3 — Planning (Pre-Execution Review)

**Trigger:** ARIA identifies a multi-step task from the conversation  
**Character size:** Medium (30% — steps back slightly to give room to the plan)  
**Purpose:** User reviews and approves before anything runs.

### 5.1 Layout

```
┌───────────────────────────────────────────────────────────────────────┐
│ TOP BAR                                                               │
├──────────────────────┬────────────────────────────────────────────────┤
│                      │                                                │
│  CHARACTER — 30%     │  PLANNING CARD — 70%                          │
│                      │                                                │
│  VRM, upper-body     │  ┌──────────────────────────────────────────┐ │
│  cropped in view     │  │ 🎯 Fill Hackathon Registration — Unstop  │ │
│                      │  │──────────────────────────────────────────│ │
│  Expression:         │  │ ARIA's understanding (2–3 lines)         │ │
│  thinking            │  │                                          │ │
│                      │  │ Execution Plan        Permissions        │ │
│  Status:             │  │ ○ Open browser        ✅ Browser         │ │
│  "Thinking..."       │  │ ○ Inject overlay      ✅ Memory read     │ │
│                      │  │ ○ Autofill 7 fields   ⚠ Form submit     │ │
│                      │  │ ○ HITL for unknowns                      │ │
│                      │  │ ○ Submit on confirm                      │ │
│                      │  │                                          │ │
│                      │  │ Info Gaps: None — all covered            │ │
│                      │  │                                          │ │
│                      │  │  [  Cancel  ]    [ ✓ Approve & Run  ]   │ │
│                      │  └──────────────────────────────────────────┘ │
├──────────────────────┴────────────────────────────────────────────────┤
│ BOTTOM BAR                                                            │
└───────────────────────────────────────────────────────────────────────┘
```

### 5.2 Transition Into Planning

1. Character zone narrows from 45% → 30% (`width` transition, 400ms `--ease-out-smooth`)
2. Chat panel or widgets fade out (200ms)
3. Planning card slides in from top (`translateY(-16px) → 0`, `opacity: 0 → 1`, 500ms `--ease-out-smooth`)
4. Character adopts `thinking` emotion (VRM BlendShape)

### 5.3 Planning Card Specs

```css
background: rgba(22, 22, 31, 0.92);
border: 1px solid rgba(232, 201, 122, 0.20);
border-radius: 16px;
padding: 20px;
box-shadow: 0 0 28px rgba(232, 201, 122, 0.08);
display: flex;
flex-direction: column;
gap: 14px;
/* fills full height of the 70% zone with 16px padding around it */
```

**Title row:**
- Icon + task name: Space Grotesk 14px, weight 600, `--gold-primary`
- Separator: 1px `rgba(232,201,122,0.10)` line

**Understanding paragraph:**
- Font: Inter 12px, `--text-secondary`, line-height 1.6
- Container: `background: rgba(255,255,255,0.02)`, `border-left: 2px solid rgba(232,201,122,0.20)`, padding 8px 12px, border-radius 0 6px 6px 0

**Execution Plan (step list):**

Each step row: `display: flex`, `align-items: center`, `gap: 8px`, `font-size: 11px`, `color: --text-secondary`

Step indicator circle (14×14px):
| State | Style |
|---|---|
| `pending` | Border `1.5px solid #5a5550`, no fill |
| `active` | Border + fill `rgba(232,201,122,0.15)`, gold border, pulsing animation |
| `complete` | Gold fill `#e8c97a`, gold border, checkmark (6px white SVG) |
| `error` | Red fill `#f46a6a`, red border, × mark |

**Permissions column:**
- ✅ green text, `--accent-green`
- ⚠ coral text, `--accent-coral`
- Font: 11px Inter

**Info Gaps row:**
- `background: rgba(107,207,127,0.05)`, `border: 1px solid rgba(107,207,127,0.10)`, border-radius 6px, padding 6px 10px
- Font 10px, `--accent-green` icon, `--text-muted` text

**Action buttons:**

Cancel button:
```css
flex: 1;
padding: 9px;
border: 1px solid rgba(232, 201, 122, 0.28);
background: transparent;
color: --gold-primary;
border-radius: 8px;
font-size: 12px;
font-family: --font-body;
cursor: pointer;
transition: background 150ms;
:hover { background: rgba(232, 201, 122, 0.06); }
```

Approve & Run button:
```css
flex: 2;
padding: 9px;
background: #e8c97a;
border: none;
color: #0a0a0f;
border-radius: 8px;
font-size: 12px;
font-weight: 600;
font-family: --font-body;
cursor: pointer;
transition: transform 150ms --ease-spring, box-shadow 150ms;
:hover  { transform: scale(1.02); box-shadow: 0 0 16px rgba(232,201,122,0.30); }
:active { transform: scale(0.98); }
```

---

## 6. State 4 — Execution (Work Mode / Canvas Active)

**Trigger:** User clicks "Approve & Run"  
**Character size:** Small co-pilot (25% — slides left, stays fully visible)  
**Purpose:** The canvas becomes the star. ARIA watches and narrates.

### 6.1 Layout

```
┌───────────────────────────────────────────────────────────────────────┐
│ TOP BAR                                                               │
├───────────────────┬───────────────────────────────────────────────────┤
│                   │                                     [BrowserBot ▸]│
│  CHARACTER — 20%  │  TASK CANVAS — 80%                               │
│                   │                                                   │
│  VRM, upper-body  │  (Canvas type depends on active task —           │
│  framing only     │   see Section 6.3 for each canvas spec)          │
│                   │                                                   │
│  Small but        │                                                   │
│  fully rendered   │                                                   │
│                   │                                                   │
│  Expression:      │                                                   │
│  executing        │                                                   │
│                   │                                                   │
│  Status:          │                                                   │
│  "Working..."     │                                                   │
│                   │                                                   │
├───────────────────┴───────────────────────────────────────────────────┤
│ BOTTOM BAR — "Agent running..." indicator above waveform              │
└───────────────────────────────────────────────────────────────────────┘
```

### 6.2 Transition Into Execution

1. Character zone narrows: 30% → 20% (`width` transition, 500ms `--ease-out-smooth`)
2. Planning card scales down and fades out (`scale(0.96)` + `opacity: 0`, 300ms)
3. Task canvas expands from centre (`scale(0.96) → scale(1)` + `opacity: 0 → 1`, 500ms `--ease-out-smooth`)
4. Sub-agent chip animates in from top-right (`translateX(16px)` + `opacity: 0 → 1`, 250ms `--ease-spring`)
5. Character adopts `executing` emotion
6. Bottom bar shows "Agent running..." indicator

### 6.3 Sub-Agent Chip

Floats in the top-right area of the canvas zone (absolute positioned within it, top: 12px, right: 12px). Multiple chips stack vertically with 8px gap.

```
┌──────────────────────────────────┐
│  🤖 BrowserBot         [Pause]  │
│  Filling field 4 of 9...        │
│  ▂▄▆█▆▄▂▄▆  ●  online           │
└──────────────────────────────────┘
```

```css
background: rgba(22, 22, 31, 0.92);
border: 1px solid rgba(79, 209, 199, 0.30);    /* teal for BrowserBot */
border-radius: 10px;
padding: 10px 12px;
width: 220px;
box-shadow: 0 4px 16px rgba(0,0,0,0.4);
```

Chip border colours per agent:
- BrowserBot: `rgba(79, 209, 199, 0.30)` (teal)
- ScriptRunner: `rgba(155, 127, 244, 0.30)` (purple)
- ResearchBot: `rgba(232, 201, 122, 0.30)` (gold)

Chip name: Space Grotesk 12px, weight 600, agent accent colour  
Status text: Inter 10px, `--text-secondary`  
Heartbeat line: animated SVG `<polyline>`, 80×20px, stroke matches agent colour, `stroke-dashoffset` animation at 2s linear infinite  
Pause button: transparent background, 1px agent-colour border, border-radius 4px, 10px font, agent colour text

**Chip entrance animation:** `translateX(16px)` + `opacity: 0 → 1`, 250ms `--ease-spring`  
**Chip exit animation:** `scale(0.9)` + `opacity: 0`, 200ms `--ease-gentle`

### 6.4 Form Fill Canvas

Shown when `activeCanvas === 'form'`. This is the highest-priority canvas — most likely to be shown in the demo.

```
┌──────────────────────────────────────────────────────────────────────┐
│  FORM FILL CANVAS                                                    │
│  ┌────────────────────────────┐  ┌─────────────────────────────────┐ │
│  │  BROWSER WEBVIEW  (55%)    │  │  FIELD PANEL  (45%)             │ │
│  │                            │  │                                 │ │
│  │  Live Chromium view        │  │  [1] Full Name     ✅ autofilled │ │
│  │  (Tauri WebView2)          │  │  [2] Email         ✅ autofilled │ │
│  │                            │  │  [3] College       ✅ autofilled │ │
│  │  DOM overlay badges        │  │  [4] Department    ✅ autofilled │ │
│  │  [1][2][3] visible         │  │  [7] Team Code     ⚠ needs input│ │
│  │  on page elements          │  │                                 │ │
│  │                            │  │  ─────────────────────────────  │ │
│  │                            │  │  ACTION LOG                     │ │
│  │                            │  │  > Opened unstop.com            │ │
│  │                            │  │  > Injected DOM overlay         │ │
│  │                            │  │  > Filled [1] Full Name         │ │
│  │                            │  │                                 │ │
│  │                            │  │  [Pause] [Override] [Abort]     │ │
│  └────────────────────────────┘  └─────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

**Browser webview (left, 55%):**
- This is a Tauri `<webview>` component (WebView2 on Windows) embedding the live Playwright-controlled Chromium
- The webview renders the actual website ARIA is operating
- DOM badges `[1]`, `[2]` etc. are injected by ARIA's `OVERLAY_JS` and are visible on the page
- Border-radius: 10px, border: `1px solid rgba(232,201,122,0.12)`, overflow hidden
- A thin label bar at the top of the webview shows the current URL in `--font-mono` 10px `--text-muted`

**Field panel (right, 45%):**
- Container: glass panel, `flex-direction: column`, gap 6px, padding 14px
- Title: "Form Fields" in Space Grotesk 12px `--gold-primary`

Field row:
```
[badge] Field Name    [status badge]   [value preview]
```
- Badge: `[N]` number in 9px mono, `rgba(232,201,122,0.15)` background, 16×16px, border-radius 3px
- Field name: Inter 11px `--text-secondary`
- Status badges:
  - `✅ autofilled` — green text, green dot
  - `⚠ needs input` — coral text, pulsing coral dot
  - `⏳ pending` — muted text
  - `✓ approved` — green text
- Value preview: 10px `--font-mono` `--text-muted`, truncated at 20 chars

**Action log:**
```css
background: rgba(10, 10, 15, 0.6);
border: 1px solid rgba(255,255,255,0.05);
border-radius: 8px;
padding: 10px;
flex: 1;
overflow-y: auto;
```
- Each log line: `font-family: --font-mono`, `font-size: 10px`, line-height 1.8
- Colours: pending `--text-muted`, active `--text-secondary`, done `--accent-green`, error `--accent-red`
- Log lines animate in with `opacity: 0 → 1` stagger

**Control buttons row:**
- `[Pause]` — ghost button, gold border
- `[Override Field]` — ghost button, coral border
- `[Skip]` — ghost button, muted border
- `[Abort]` — danger button, red border

### 6.5 Research Canvas

Shown when `activeCanvas === 'research'`.

```
┌──────────────────────────────────────────────────────────────────────┐
│  RESEARCH CANVAS                                                     │
│                                                                      │
│  Query: "Quantum Computing"                                          │
│  Sub-questions: [What is quantum computing?] [Key applications]...  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  (scrollable findings body)                                  │   │
│  │                                                              │   │
│  │  ▶ What is quantum computing?                                │   │
│  │    Synthesised finding paragraph...                          │   │
│  │    [2 sources ▾]                                             │   │
│  │                                                              │   │
│  │  ▶ Key applications                                          │   │
│  │    Synthesised finding paragraph...                          │   │
│  │    [3 sources ▾]                                             │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  [Export MD]  [Export PDF]  [ Ask follow-up... ]                    │
└──────────────────────────────────────────────────────────────────────┘
```

- Header: query in Space Grotesk 14px `--gold-primary`
- Sub-question pills: `background: rgba(232,201,122,0.08)`, `border: 1px solid rgba(232,201,122,0.18)`, `color: --gold-dim`, border-radius 20px, padding 3px 10px, font-size 10px
- Section headers: Inter 12px weight 600 `--text-primary`, with expand/collapse chevron
- Finding paragraphs: Inter 12px `--text-secondary`, line-height 1.7
- Source expandable: `[N sources ▾]` in teal, expands to show source cards
- Source card: site name + URL + credibility dot + short quote excerpt

### 6.6 Email Blast Canvas

Shown when `activeCanvas === 'email'`.

```
┌───────────────────────────────┬──────────────────────────────────────┐
│  TEMPLATE EDITOR (45%)        │  RECIPIENT PANEL (55%)               │
│                               │                                      │
│  Subject: [________________]  │  [Drop CSV here]                     │
│                               │  or click to browse                  │
│  Body:                        │                                      │
│  ┌─────────────────────────┐  │  ─────────────────────────────────   │
│  │ Hi {{name}},            │  │  Preview: Email 1 of 47              │
│  │                         │  │  To: Rohan Verma <r@example.com>    │
│  │ [rich text area]        │  │  Subject: Team Invitation            │
│  │                         │  │  Body preview (rendered)            │
│  └─────────────────────────┘  │                                      │
│                               │  ─────────────────────────────────   │
│  Variables:                   │  Rate: [Slow] [Normal●] [Fast]       │
│  [{{name}}] [{{email}}]       │                                      │
│                               │  [Send to 47 recipients]            │
└───────────────────────────────┴──────────────────────────────────────┘
```

### 6.7 Certificate Canvas

Shown when `activeCanvas === 'certificate'`.

```
┌─────────────────────────────────────────────────────────────────────┐
│  Upload row                                                         │
│  ┌─────────────────────────┐  ┌─────────────────────────────────┐  │
│  │  Drop template image    │  │  Drop CSV / spreadsheet         │  │
│  │  PNG or JPG             │  │  Shows column headers on parse  │  │
│  └─────────────────────────┘  └─────────────────────────────────┘  │
│                                                                     │
│  Live preview of certificate with text overlay                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │            [certificate image]                              │   │
│  │            [draggable text handles]                         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  Font: [Serif▾]  Size: [──●──]  Colour: [⬤]                        │
│                                                                     │
│  [Preview All (3)]    ████████░░░░  [Generate 47 Certificates]     │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.8 Script Canvas

Shown when `activeCanvas === 'script'` (ScriptRunner active).

```
┌─────────────────────────────────────────────────────────────────────┐
│  SCRIPT PREVIEW                      [▶ Run]  [✎ Edit]  [✕ Abort] │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  # Generated by ARIA ScriptRunner                          │   │
│  │  import csv, smtplib ...                                   │   │
│  │  (read-only code view, syntax highlighted)                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  OUTPUT STREAM                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  > Sent email to rohan@example.com                         │   │
│  │  > Sent email to priya@example.com                         │   │
│  │  > [47/47] Complete                                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 7. State 5 — Completion (Return to Companion)

**Trigger:** Task complete signal from backend WebSocket (`task_complete` message)  
**Character size:** Returns to large (45% — expands back to Home proportions)  
**Purpose:** Celebrate, summarise, close the loop. Then return to Home.

### 7.1 Layout

```
┌───────────────────────────────────────────────────────────────────────┐
│ TOP BAR                                                               │
├──────────────────────────────┬────────────────────────────────────────┤
│                              │                                        │
│  CHARACTER — 45%             │  COMPLETION CARD — 55%                │
│  (back to Home size)         │                                        │
│                              │  ┌──────────────────────────────────┐ │
│  Expression: success         │  │  ✅  Task Complete               │ │
│  Bounce animation            │  │  ───────────────────────────────│ │
│  Gold particles from hands   │  │  ✓ Form submitted to Unstop     │ │
│                              │  │  🧠 7 fields from memory        │ │
│  Status: "Task done!"        │  │  👤 1 field from your input     │ │
│                              │  │  💾 Memory updated — 1 new item │ │
│                              │  │                                 │ │
│                              │  │  [ View Notepad ]  [ Done ]     │ │
│                              │  └──────────────────────────────────┘ │
│                              │  (auto-dismisses in 8s)               │
├──────────────────────────────┴────────────────────────────────────────┤
│ BOTTOM BAR                                                            │
└───────────────────────────────────────────────────────────────────────┘
```

### 7.2 Transition Into Completion

1. Task canvas scales down and fades out (`scale(0.96)` + `opacity: 0`, 300ms)
2. Sub-agent chips exit with despawn animation
3. Character zone expands: 20% → 45% (500ms `--ease-out-smooth`)
4. Completion card slides in from right (`translateX(24px) → 0`, `opacity: 0 → 1`, 500ms)
5. Character adopts `success` emotion + small Y-position bounce (200ms spring)
6. Gold success particles: 12 small particles (`4×4px` gold divs) burst from the character's hand position, disperse via CSS keyframe with random `translate` and `opacity: 1 → 0`, 600ms

### 7.3 Completion Card Specs

```css
background: rgba(22, 22, 31, 0.92);
border: 1px solid rgba(107, 207, 127, 0.25);
border-radius: 16px;
padding: 20px;
box-shadow: 0 0 28px rgba(107, 207, 127, 0.08);
```

- Title: `✅ Task Complete` — Space Grotesk 15px weight 600 `--accent-green`
- Separator: 1px `rgba(107,207,127,0.15)` line

Result rows:
```css
display: flex;
align-items: flex-start;
gap: 8px;
font-size: 12px;
color: --text-secondary;
padding: 6px 10px;
background: rgba(255,255,255,0.02);
border-radius: 7px;
```

Row icon colours: ✓ green, 🧠 gold, 👤 teal, 💾 purple

**Auto-dismiss:** 8-second countdown. A thin progress bar at the bottom of the card depletes from full to empty over 8s (`width: 100% → 0`, linear). On reaching 0, triggers → Home State. "Done" button triggers immediately.

**View Notepad:** Ghost button (gold border). Opens a slide-over panel showing the full task log and any files generated.

**After dismiss:** → Home State (section 3). The widget zone re-appears with widgets fading back in.

---

## 8. HITL Interrupt Modal

**Trigger:** Backend sends `hitl_request` WebSocket message  
**Displayed over:** Any execution state (does not change layout, overlays it)

```
┌──────────────────────────────────────────────────────────────────────┐
│ (blurred overlay — rgba(10,10,15,0.7), backdrop-filter: blur(4px))  │
│                                                                      │
│            ┌────────────────────────────────────┐                   │
│            │  ⚠  ARIA needs your input          │                   │
│            │  ──────────────────────────────    │                   │
│            │  Unknown field: Team Access Code   │                   │
│            │  Not found in your memory profile. │                   │
│            │                                    │                   │
│            │  [________________________]        │                   │
│            │                                    │                   │
│            │  [  Submit & Resume  ]             │                   │
│            └────────────────────────────────────┘                   │
└──────────────────────────────────────────────────────────────────────┘
```

**Overlay:** `position: absolute`, `inset: 0`, `z-index: 30`, `background: rgba(10,10,15,0.7)`, `backdrop-filter: blur(4px)`, `border-radius: 16px` (matches app)

**Modal inner:**
```css
background: #16161f;
border: 1px solid rgba(244, 149, 106, 0.40);
border-radius: 14px;
padding: 20px;
width: 300px;
box-shadow: 0 0 40px rgba(244, 149, 106, 0.15);
```

**Pre-modal attention signal:** Before the modal appears, the chat input border pulses coral (`--accent-coral`) three times (150ms each pulse), then the modal fades in.

**Character reaction:** Head tilt animation + `thinking` expression while HITL is open.

**On submit:** Modal fades out, character returns to `executing`, automation resumes.

---

## 9. Floating Widget Mode (Overlay on Desktop)

**Trigger:** User minimises to widget via system tray or keyboard shortcut  
**Implementation:** Second Tauri window (`label: "widget"`) — `transparent: true`, `alwaysOnTop: true`, `decorations: false`  
**Size options:** Small 150×200, Medium 300×400 (default), Large 450×600  

This window shows only the VRM character's upper body against a transparent background. The character appears to float over whatever the user has open.

**Behaviour:**
- **Idle:** Character breathes, occasional glance around
- **Click on character:** `invoke('show_main_window')` → main window raises and focuses
- **Right-click:** Context menu
  ```
  ┌───────────────────────────────┐
  │  Fill form on this page       │
  │  Research this topic          │
  │  Open ARIA                    │
  │  ─────────────────────────── │
  │  Widget size: S / M / L       │
  └───────────────────────────────┘
  ```
- **Agent active:** Small pulsing gold dot (8×8px) above character's head
- **HITL interrupt:** Character plays `thinking` animation + small toast notification slides in from bottom of widget window: `"ARIA needs your input →"` in a glass pill, coral left border, 220px wide

**Hit testing:** `tauri_plugin_window_passthrough` — clicks pass through fully transparent pixels. Only the VRM mesh captures mouse events.

**Resize handle:** Transparent 20×20px area at the bottom of the widget. Drag resizes the Tauri window between the three size presets.

---

## 10. Background World

Rendered on a full-window `<canvas>` element at `z-index: 0`. Lightweight particle system — no heavy 3D library, pure `requestAnimationFrame`.

**Default theme: Night Garden**
- Background: linear gradient `#0a0a12 → #0f0f16 → #0c0b14` (top to bottom)
- Stars: 7–10 static small white dots (`rgba(240,237,232,0.4)`) at random positions in the upper quarter
- Ambient warm glow: radial gradient behind character position, `rgba(232,201,122,0.05)`, 180px radius
- Particles: 38 max, each is a small gold ellipse (`fill: #e8c97a`), drifts down-left slowly, fades in/out
  - `size`: 1.5–4.5px, `opacity`: 0.05–0.35, `dx`: −0.3 to 0, `dy`: 0.15–0.55, rotation drift
  - On exit (below canvas): respawn at top with new random X

**Alternate themes** (selectable in Settings, stored in `settings.json`):
- `cherry_blossom_day` — pink tones, warmer particles
- `rainy_window` — dark blue, vertical rain streaks (lines instead of ellipses)
- `deep_space` — near-black, slow nebula drift, blue-purple particles
- `lofi_room` — warm amber glow, no particles (static)

Each theme is a JSON config object:
```json
{
  "id": "night_garden",
  "bgGradient": ["#0a0a12", "#0f0f16", "#0c0b14"],
  "particleColor": "#e8c97a",
  "particleType": "blossom",
  "ambientColor": "rgba(232,201,122,0.05)",
  "characterLighting": "#ffd4a0"
}
```

---

## 11. Draggable Widget System — Implementation Spec

This applies to the Home state widget zone (section 3.3). Every widget card must support drag, resize, and delete without breaking anything else.

### 11.1 Recommended Library

Use **`@dnd-kit/core`** + **`@dnd-kit/utilities`** for drag-and-drop. It is accessible, touch-compatible, and does not conflict with Three.js pointer events.

Alternatively use **react-resizable-panels** for resize. Or implement with native pointer events if keeping dependencies minimal.

### 11.2 Data Model

Widget layout is stored in Zustand and persisted to `settings.json`:

```typescript
interface WidgetConfig {
  id: WidgetId;          // 'clock' | 'active_task' | 'memory' | 'quick_actions'
  visible: boolean;       // false = deleted/hidden
  position: { x: number; y: number };  // px offset from widget zone top-left
  size: { width: number; height: number };  // px
}

type WidgetId = 'clock' | 'active_task' | 'memory' | 'quick_actions';

// In ARIAStore:
widgetLayout: WidgetConfig[];
updateWidget: (id: WidgetId, patch: Partial<WidgetConfig>) => void;
resetWidgetLayout: () => void;  // restore defaults
```

### 11.3 Drag Behaviour

- **Drag handle:** Entire widget header area. Apply `cursor: grab` on hover, `cursor: grabbing` during drag.
- **Drag indicator:** While dragging, the widget lifts (`box-shadow: 0 8px 40px rgba(0,0,0,0.6)`) and the ghost placeholder (semi-transparent outline, `border: 1px dashed rgba(232,201,122,0.25)`) remains at the original position.
- **Drop:** Widget snaps to the nearest 8px grid point (optional — makes layouts cleaner).
- **Boundary:** Widgets cannot be dragged outside the widget zone boundaries.
- **Collision:** If dropped overlapping another widget, resolve by pushing the dragged widget to the nearest free position.

### 11.4 Resize Behaviour

- **Handle:** 12×12px hit area at the bottom-right corner. Visible only on widget hover as a subtle `⌟` icon in `--text-muted`.
- **Minimum size:** 140px wide × 100px tall.
- **Maximum size:** Widget zone width × widget zone height (can expand to fill entire zone if user wants).
- **Live resize:** Widget redraws during drag (no flicker — avoid re-mounting).
- **After resize:** Update `WidgetConfig.size` and persist.

### 11.5 Delete Behaviour

- **Trigger:** `×` button in the top-right corner of the widget. Appears on hover (`opacity: 0 → 1`, 150ms transition). Size: 18×18px, colour `--text-muted`, hover colour `--accent-red`.
- **Animation on delete:** Widget scales down and fades out (`scale(0.9)` + `opacity: 0`, 200ms). The space it occupied collapses softly (other widgets do not auto-reflow — the zone is free-form, not a grid).
- **Effect:** Sets `visible: false` in `WidgetConfig`. Widget data is preserved; it can be re-enabled from Settings → Widget Manager.
- **Nothing breaks:** Deleting a widget only affects that widget's `visible` flag. The state machine, character, canvases, and other widgets are completely unaffected.
- **Empty state:** If all widgets are deleted, show a subtle ghost hint: `"+ Add widgets in Settings"` centred in the zone, in `--text-muted` 11px.

### 11.6 Widget Manager (Settings Panel)

Accessible via the Settings nav icon. Shows all 4 widgets (and any from installed skills) as toggle rows:

```
Widget Manager
──────────────────────────────────
●  Clock               [●  ON ]
●  Active Task         [●  ON ]
○  Memory              [○ OFF ]   ← deleted/hidden
●  Quick Actions       [●  ON ]
──────────────────────────────────
                    [Reset Layout]
```

Toggling a widget back on re-adds it to its last saved position (or a default position if position data was lost).

---

## 12. State Transition Summary

| From → To | Character width | Animation |
|---|---|---|
| Home → Conversation | 45% → 45% (no change) | Widgets fade out, chat slides in from right (400ms) |
| Conversation → Planning | 45% → 30% | Chat fades, character narrows, planning card drops from top (500ms) |
| Planning → Execution | 30% → 20% | Planning card scales out, canvas expands, chip spawns (500ms) |
| Execution → Completion | 20% → 45% | Canvas scales out, character expands, completion card slides in (500ms) |
| Completion → Home | 45% → 45% (no change) | Completion card fades, widgets fade back in (300ms) |
| Any → Home (cancel) | Any → 45% | Current panel fades, widgets fade in (300ms) |

All width transitions use `transition: width 500ms var(--ease-out-smooth)`.  
The Three.js canvas always fills 100% of the character zone — the VRM camera adjusts to frame the character correctly at each zone width (wider zone = more of the body visible, narrower = tighter upper-body crop). Implement this as a camera position lerp triggered by zone width changes.

---

## 13. Z-Index Stack

```
z-index: 0   — Background world canvas (particle system)
z-index: 1   — Ambient glow divs
z-index: 2   — Three.js character canvas
z-index: 3   — Widget zone / Canvas zone content
z-index: 10  — Top bar, Bottom bar (always on top of content)
z-index: 20  — Sub-agent chips (float above canvas)
z-index: 30  — HITL modal overlay
z-index: 40  — Tooltips, context menus
```

---

## 14. Accessibility Minimum Requirements

- All interactive elements have `aria-label` attributes
- Keyboard navigation: Tab order follows visual left-to-right, top-to-bottom layout
- Focus rings: `box-shadow: 0 0 0 2px rgba(232,201,122,0.5)` (gold, not browser default blue)
- Modal (HITL): focus trapped inside while open; `Escape` key submits/dismisses
- Character animations: wrapped in `@media (prefers-reduced-motion)` — if reduced motion is on, disable the particle system and character idle animations; keep static pose only
- Screen reader summary: a visually-hidden `<h1>` at the root reads "ARIA — AI Desktop Companion" and updates with current state name

---

## 15. File Structure Recommendation

```
src/
  components/
    shell/
      TopBar.tsx
      BottomBar.tsx
      BackgroundCanvas.tsx
    character/
      CharacterZone.tsx        ← Three.js canvas + VRM loader
      useVRMEmotions.ts        ← Hook: exposes setEmotion(EmotionState)
    widgets/
      WidgetCanvas.tsx         ← Drag-and-drop host
      ClockWidget.tsx
      ActiveTaskWidget.tsx
      MemoryWidget.tsx
      QuickActionsWidget.tsx
    states/
      HomeState.tsx
      ConversationState.tsx
      PlanningState.tsx
      ExecutionState.tsx
      CompletionState.tsx
    canvases/
      FormFillCanvas.tsx
      ResearchCanvas.tsx
      EmailBlastCanvas.tsx
      CertificateCanvas.tsx
      ScriptCanvas.tsx
    modals/
      HITLModal.tsx
    chips/
      SubAgentChip.tsx
  store/
    ariaStore.ts               ← Zustand store (AppState + widgetLayout + messages)
  hooks/
    useWebSocket.ts
    useWakeWord.ts
    useWaveform.ts
  styles/
    tokens.css                 ← All design tokens (section 1)
    globals.css
  lib/
    vrm.ts                     ← VRM loader utility
    widgetDefaults.ts          ← Default WidgetConfig[]
```

---

*End of ARIA Layout Design Specification v1.0*  
*Built for FAR AWAY 2026 — Team Endeavour*
