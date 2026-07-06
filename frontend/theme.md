# Sampark AI — Frontend Theme & Design System

> **Design Philosophy:** Premium dark UI with glassmorphism aesthetics — blending transparency, blur, and vibrant gradients to create a futuristic governance platform.

---

## 1. Color System

### 1.1 Core Palette

| Token | CSS Variable | Hex | Usage |
|-------|-------------|-----|-------|
| **Background** | `--bg-color` | `#0b0f19` | Page background (deep navy-black) |
| **Panel** | `--panel-bg` | `#111827` | Card/surface background |
| **Border** | `--border-color` | `rgba(255,255,255,0.08)` | Subtle transparent borders |
| **Text Primary** | `--text-primary` | `#f3f4f6` | Headings, body text |
| **Text Secondary** | `--text-secondary` | `#9ca3af` | Labels, hints, muted text |

### 1.2 Accent Colors

| Token | CSS Variable | Hex | Usage |
|-------|-------------|-----|-------|
| **Primary** | `--primary-color` | `#6366f1` | Buttons, links, active states (indigo) |
| **Primary Hover** | `--primary-hover` | `#4f46e5` | Button hover state |
| **Primary Gradient** | `--primary-gradient` | `linear-gradient(135deg, #6366f1 → #06b6d4)` | Brand headers, primary buttons (indigo → cyan) |
| **Accent Gradient** | `--accent-gradient` | `linear-gradient(135deg, #f59e0b → #ef4444)` | Warning/highlight gradients (amber → red) |

### 1.3 Semantic Colors

| Token | CSS Variable | Hex | Usage |
|-------|-------------|-----|-------|
| **Success** | `--success-color` | `#10b981` | Completed steps, positive metrics, health UP |
| **Error** | `--error-color` | `#ef4444` | Errors, deletions, critical alerts |
| **Warning** | `--warning-color` | `#f59e0b` | Warnings, medium-priority badges |
| **Info/Insight** | — | `#a5b4fc` | AI trace headers, insight panel text (light indigo) |

### 1.4 Badge Colors

| Variant | Background | Text Color |
|---------|-----------|------------|
| `badge-critical` | `rgba(239, 68, 68, 0.2)` | `#f87171` |
| `badge-high` | `rgba(245, 158, 11, 0.2)` | `#fbbf24` |
| `badge-medium` | `rgba(99, 102, 241, 0.2)` | `#818cf8` |
| `badge-low` | `rgba(156, 163, 175, 0.2)` | `#e5e7eb` |

---

## 2. Typography

### 2.1 Font Stack

```css
font-family: 'Outfit', 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont,
             'Segoe UI', Roboto, sans-serif;
```

- **Outfit** — Primary font (geometric, modern, premium feel)
- **Plus Jakarta Sans** — Fallback with similar weight spectrum
- Loaded via Google Fonts CDN

### 2.2 Font Weights

| Weight | Usage |
|--------|-------|
| `300` | Thin meta text (rare) |
| `400` | Body text |
| `500` | Labels, medium emphasis |
| `600` | Buttons, subheadings |
| `700` | Card titles, section headers |
| `800` | Page titles, brand name (extra bold) |

### 2.3 Type Scale

| Element | Size | Weight | Letter-spacing |
|---------|------|--------|----------------|
| Page Title (`h1`) | `32px` | `800` | `-0.8px` |
| Brand Name | `24px` | `800` | `-0.5px` |
| Section Title (`h3`) | `20px` | `700` | normal |
| AI Trace Title | `18px` | `700` | normal |
| Body Text | `15px` | `500` | normal |
| Metric Value (`h3` in metric) | `28px` | `800` | normal |
| Small/Labels | `13px-14px` | `500` | normal |
| Caption/Badge | `12px` | `600` | normal (uppercase) |
| Agent Name | `14px` | `700` | `0.8px` uppercase |

---

## 3. Glassmorphism Components

### 3.1 Glass Panel (`.glass-panel`)

The foundational container component used throughout the UI.

```css
.glass-panel {
  background: var(--panel-bg);       /* #111827 */
  backdrop-filter: blur(8px);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.glass-panel:hover {
  border-color: rgba(99, 102, 241, 0.25);
  box-shadow: 0 12px 40px 0 rgba(99, 102, 241, 0.08);
}
```

**Characteristics:**
- Dark semi-transparent background (`#111827`)
- Subtle `8px` backdrop blur (frosted glass effect)
- `1px` transparent white border
- `16px` border radius for soft corners
- Hover: indigo glow on border + shadow

### 3.2 Input Fields (`.input-field`)

```css
.input-field {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 12px 16px;
  color: var(--text-primary);
  font-size: 15px;
}

.input-field:focus {
  border-color: var(--primary-color);
  background: rgba(255, 255, 255, 0.06);
  box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.15);
}
```

---

## 4. Layout System

### 4.1 App Shell (`.layout-wrapper`)

```
┌─────────────┬──────────────────────────────────────┐
│  SIDEBAR    │          MAIN CONTENT                 │
│  (280px)    │          (flex: 1)                    │
│             │                                        │
│  Brand      │  Header (page title + actions)         │
│  Navigation │                                        │
│             │  Content panels (glass-panel)          │
│  User       │                                        │
│  Profile    │                                        │
│  Logout     │                                        │
└─────────────┴──────────────────────────────────────┘
```

- **Sidebar:** Fixed `280px` width, dark background, contains brand, nav, and user profile
- **Main:** Fluid remaining width, scrollable, `40px` padding
- **Max content width:** `800px` on Report tab

### 4.2 Dashboard Layout (`.dashboard-v2-grid`)

| Breakpoint | Columns |
|-----------|---------|
| `< 1024px` | Single column (1fr) |
| `≥ 1024px` | Two columns (3fr + 1fr) |

- **Main column (left):** Summary metrics, Critical Action Queue
- **Side column (right):** AI Insights, Ward Risk Map

---

## 5. UI Components

### 5.1 Buttons

| Variant | Class | Style |
|---------|-------|-------|
| **Primary** | `.btn-primary` | Indigo→cyan gradient, white text, shadow glow |
| **Secondary** | `.btn-secondary` | Transparent bg, white border, muted text |

Both share: `12px` border-radius, `12px 24px` padding, `600` weight, `15px` font, flex with `8px` gap for icons.

### 5.2 Sidebar Menu Items

- `14px 18px` padding, `12px` border-radius
- Default: text-secondary color
- Hover: background `rgba(255,255,255,0.05)`, text-primary
- Active: indigo tint (`rgba(99,102,241,0.15)` bg, indigo border, `#818cf8` text)

### 5.3 User Profile

- `42px` avatar with primary gradient background
- Name (`14px`, `600` weight) + role label (`12px`, secondary color)
- Wrapped in a subtle glass panel

### 5.4 Metric Cards

- Horizontal flex layout: icon (`52px` square) + data
- Icon container: indigo tint, `12px` border-radius
- Metric value: `28px`, `800` weight
- Label: `14px`, secondary color, `500` weight

### 5.5 Badges

- `4px 10px` padding, rounded `99px` (pill shape)
- `12px` font, `600` weight, UPPERCASE
- Color-coded by severity (see 1.4)

### 5.6 Alerts

- `12px 16px` padding, `12px` border-radius
- Error variant: red tint background with red border
- Animated notification banner: indigo tint with `Sparkles` icon

### 5.7 Critical Action Queue Items

- `16px` padding, `12px` border-radius
- Subtle glass background (`rgba(255,255,255,0.02)`)
- Horizontal layout: description + status badge
- Hover: slightly brighter background

### 5.8 AI Decision Trace Cards

- 5 agent cards stacked vertically
- Each card has: agent icon (`28px` square), name, status badge
- Grid of trace items (`200px` min column width)
- Policy citation cards: indigo tint, `8px` border-radius

---

## 6. Animations & Transitions

### 6.1 Keyframe Animations

```css
@keyframes spin {
  0%   { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%      { opacity: 0.8; transform: scale(1.05); }
}
```

| Animation | Used On |
|-----------|---------|
| `spin` | Loading spinner (`.spinner`) |
| `pulse` | Brand logo, waiting step bullet |

### 6.2 Transitions

- **Glass panels:** `0.3s cubic-bezier(0.4, 0, 0.2, 1)` — smooth hover glow
- **Menu items:** `0.2s ease` — color/bg changes
- **Buttons:** `0.2s ease` — hover lift + shadow
- **Inputs:** `0.2s ease` — focus glow ring
- **Metric cards:** standard hover effects

---

## 7. Step Progress / Pipeline Stream

Visual representation of the LangGraph agent pipeline execution:

```
● Completed    — green bullet with glow (box-shadow)
● Waiting      — gray bullet
● In Progress  — gray bullet with pulse animation
```

- `12px` gap between steps
- Completed steps: `--success-color` text + bullet
- Waiting steps: muted secondary color

---

## 8. Responsive Design

### 8.1 Breakpoint: `max-width: 768px`

| Element | Behavior |
|---------|----------|
| Layout | Single column (sidebar becomes top bar) |
| Sidebar | Horizontal scroll, flex-direction row, `16px` padding |
| Brand | Inline with nav, no bottom margin |
| Menu | Horizontal row with `8px` gap |
| User Profile | Hidden |
| Main Content | Reduced padding to `20px` |
| Dashboard/Summary | Single column grid |

### 8.2 Breakpoint: `min-width: 1024px`

Dashboard switches to 2-column layout (`3fr + 1fr`).

---

## 9. Login Screen

- Full-viewport centered card
- Background: radial gradient circles (indigo top-right, cyan bottom-left)
- Card: `max-width: 440px`, centered
- Brand logo with pulse animation
- Form: username + password inputs
- Demo credentials shown below form

---

## 10. Scrollbar Customization

```css
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: var(--bg-color);
}
::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.25);
}
```

Thin, dark track with subtle white thumb — blends with the dark theme.

---

## 11. Icon Set

All icons sourced from **Lucide React** library (`lucide-react`):

| Icon Component | Usage |
|---------------|-------|
| `Building2` | Brand logo, Workflow agent |
| `MapPin` | Location display |
| `AlertTriangle` | Critical alerts |
| `BookOpen` | Knowledge Base tab |
| `LogOut` | Logout button |
| `Send` | Submit button, Intake agent |
| `CheckCircle2` | Success state, Validation agent |
| `Loader2` | Loading spinner |
| `FileText` | Empty KB state |
| `Trash2` | Delete document |
| `Upload` | File upload area |
| `Activity` | Dashboard tab, Prediction agent |
| `AlertCircle` | Critical queue header |
| `RefreshCw` | Refresh button |
| `Sparkles` | AI Insights, Recommendation agent |
| `Search` | (imported but available for future use) |

---

## 12. Third-Party Dependencies (Theme-Relevant)

### 12.1 Lucide React
- **Purpose:** Icon library — all icons in the application
- **Version:** `^0.395.0`
- **Size:** ~16KB gzipped (tree-shaken by Vite)

### 12.2 Recharts
- **Purpose:** Dashboard charts (7-day trend, etc.)
- **Version:** `^2.12.7`
- **Theme Integration:** Chart colors should use CSS variable palette:
  - Line/stroke: `var(--primary-color)` (#6366f1)
  - Grid lines: `var(--border-color)`
  - Tooltip bg: `var(--panel-bg)` (#111827)
  - Text: `var(--text-primary)` / `var(--text-secondary)`
- **Note:** Current chart implementation uses placeholder data; the `chart-wrapper` container has a `min-height: 320px` placeholder style.

### 12.3 Google Fonts
- **Outfit** (300–800) — Primary geometric sans-serif
- **Plus Jakarta Sans** (300–800) — Fallback
- Loaded via `<link>` in `index.html` from Google Fonts CDN

---

## 13. Responsive Considerations & Known Gaps

### 13.1 Knowledge Base Tab

The KB tab uses a two-column grid (`grid-template-columns: 1fr 2fr`) for upload + document list. **No `@media` override exists for mobile** — below `768px`, the grid will stack awkwardly. If mobile support is needed, add:

```css
@media (max-width: 768px) {
  .kb-grid {
    grid-template-columns: 1fr;
  }
}
```

### 13.2 Kebab / Sidebar Overflow

On very narrow screens (≤480px), the horizontal sidebar menu items may overflow. Consider a hamburger toggle or `overflow-x: auto` (currently applied).

---

## 14. Design Tokens Summary

```
┌─────────────────────────────────────────────────────────┐
│                   DESIGN TOKENS                          │
├───────────────┬─────────────────────────────────────────┤
│ Panel BG      │ #111827                                 │
│ Page BG       │ #0b0f19                                 │
│ Brand Grad.   │ indigo (#6366f1) → cyan (#06b6d4)       │
│ Surface       │ Glassmorphism (blur 8px, border 1px)    │
│ Corner Radius │ 12px (inputs), 16px (panels), 99px (badges)│
│ Shadow        │ 0 8px 32px rgba(0,0,0,0.37)             │
│ Focus Ring    │ 0 0 0 4px rgba(99,102,241,0.15)         │
│ Transitions   │ 0.2s ease (interactive), 0.3s cubic (panels)│
└───────────────┴─────────────────────────────────────────┘
```

---

> **Note:** The `index.css.append` file contains duplicated dashboard styles from the main `index.css`. The append file appears to be a development artifact and the canonical styles live in `index.css`.
