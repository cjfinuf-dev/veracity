# Pocket CPA -- Product Requirements Document

## 1. Project Overview

**Product Name:** Pocket CPA
**Owner:** Spero Financial Group
**Type:** Single-page web application (SPA)
**Status:** Live / iterating

Pocket CPA is a client-side accounting education and solar project management tool. It serves two audiences:

1. **Accounting learners** -- browse ASC Codification topics and work through Accounting 101 modules.
2. **Solar project managers** -- track residential/commercial solar installations through a full lifecycle (exploration through PTO), manage financials, and generate reports.

The app runs entirely in the browser with no backend, no build step, and no authentication. All data persists in `localStorage`.

---

## 2. Tech Stack

| Layer | Technology |
|-------|-----------|
| UI Library | React 18 (CDN -- `react.production.min.js`) |
| JSX Transform | Babel Standalone (CDN -- `@babel/standalone`) |
| Spreadsheet Export | SheetJS / xlsx 0.20.3 (CDN) |
| Fonts | Google Fonts -- Inter (400/500/600/700) |
| Styling | Vanilla CSS with CSS custom properties (no framework) |
| State | React `useState` + `useEffect` + `useCallback` hooks |
| Persistence | `localStorage` (`pocketcpa_projects` key) |
| Build Tool | None -- zero build, single HTML file |
| Backend | None -- fully client-side |
| Deployment Target | Cloudflare Pages (static hosting) |

---

## 3. Current Feature Set

### 3.1 ASC Codification Browser

A reference library of 8 ASC topics with drill-down detail views:

| Code | Title |
|------|-------|
| ASC 606 | Revenue from Contracts with Customers |
| ASC 842 | Leases |
| ASC 740 | Income Taxes |
| ASC 350 | Intangibles -- Goodwill and Other |
| ASC 820 | Fair Value Measurement |
| ASC 718 | Compensation -- Stock Compensation |
| ASC 326 | Credit Losses (CECL) |
| ASC 230 | Statement of Cash Flows |

Each topic includes:
- Color-coded card with tags
- Multiple key points, each with a title, explanatory body, and practical example
- Back navigation to the topic grid

### 3.2 Accounting 101 Modules

10 educational modules at beginner/intermediate levels:

| # | Title | Level |
|---|-------|-------|
| 1 | The Accounting Equation | Beginner |
| 2 | Double-Entry Bookkeeping | Beginner |
| 3 | Chart of Accounts & General Ledger | Beginner |
| 4 | Journal Entries | Beginner |
| 5 | Accrual vs. Cash Basis | Beginner |
| 6 | Financial Statements | Beginner |
| 7 | Depreciation & Amortization | Intermediate |
| 8 | Bank Reconciliations | Beginner |
| 9 | Internal Controls | Intermediate |
| 10 | Revenue Recognition Basics | Intermediate |

Each module contains:
- Intro paragraph
- Key formula (displayed as a prominent styled block)
- List of concepts with term/definition pairs

### 3.3 Solar Project Tracker

Full project lifecycle management:

- **Dashboard** -- table of all projects with status badges, progress bars, contract value, and margin
- **Project Creation** -- modal form with validated fields: customer name, structured address (street/city/state/zip), phone (formatted), email, system size (kW), panel count, contract value
- **Project Detail** with tabbed views:
  - **Lifecycle Tab** -- 4-milestone timeline (Exploration, Milestone 1/2/3) with checkable steps, per-step notes, completion dates, and progress tracking
  - **Finance Tab** -- cost breakdown (equipment, labor, permits, design, overhead, other), payment ledger with name/amount/status tracking, margin calculations
  - **Reports Tab** -- configurable report builder with toggleable sections, multi-format export (CSV via SheetJS, JSON, clipboard)
- **Project Deletion** with confirmation
- **Import/Export** -- JSON import on the Reports view

---

## 4. Architecture

### 4.1 Component Tree

```
App (root state owner)
  NavRail (fixed left rail / mobile bottom bar)
  NavSidebar (contextual sidebar -- ASC topics, modules, project info)
  MobileNavPanel (bottom-sheet overlay for mobile nav)
  [view routing via state]
    HomeView (hero + ASC grid + module grid)
    ASCDetailView (single topic deep-dive)
    ModulesView (module card grid)
    ModuleDetailView (single module content)
    Dashboard (project table)
    NewProjectForm (modal overlay)
    ProjectDetail
      LifecycleTab (milestone timeline + step checkboxes)
      FinanceTab (cost cards + payment table)
      ReportsView (toggleable report sections + export)
  BufferedInput (controlled input with deferred commit)
```

### 4.2 State Management

All state lives in `App`:

```
view: string            -- current view ("home"|"asc"|"asc-detail"|"modules"|"module-detail"|"dashboard"|"project")
projects: array         -- full project list (synced to localStorage)
selectedProjectId: str  -- active project ID
selectedTab: str        -- active tab within project detail
ascTopicId: str         -- selected ASC topic for detail view
moduleId: str           -- selected module for detail view
showForm: bool          -- new-project modal visibility
showMobileHelp: bool    -- mobile nav panel visibility
```

State flows down via props. Mutations bubble up through callback props (`onUpdate`, `onDelete`, `onSave`, etc.). No context providers or external state libraries.

### 4.3 Routing

Client-side routing is simulated via the `view` state variable. No URL hash or History API -- navigation is purely in-memory. The `NavRail` and `NavSidebar` drive view changes through `onNavigate` callbacks.

### 4.4 Data Flow

```
User action -> callback prop -> App setState -> localStorage.setItem -> re-render
Page load -> localStorage.getItem -> App setState -> render
```

---

## 5. Data Models

### 5.1 Project

```js
{
  id: string,              // e.g. "m1abc2def"
  customerName: string,
  address: string,         // formatted composite
  street: string,
  city: string,
  state: string,           // 2-letter code
  zip: string,             // "12345" or "12345-6789"
  phone: string,           // "(555) 123-4567"
  email: string,
  systemSize: number,      // kW
  panelCount: number,
  contractValue: number,   // USD
  createdDate: string,     // ISO 8601
  milestones: [            // 4 milestones
    {
      name: string,        // "Exploration Phase" | "Milestone 1" | "Milestone 2" | "Milestone 3"
      phase: string,       // "exploration" | "milestone1" | "milestone2" | "milestone3"
      steps: [
        {
          name: string,
          completed: boolean,
          completedDate: string | null,
          notes: string
        }
      ]
    }
  ],
  costs: {
    equipment: number,
    labor: number,
    permits: number,
    design: number,
    overhead: number,
    other: number
  },
  payments: [
    {
      id: string,
      name: string,
      amount: number,
      status: "pending" | "remitted"
    }
  ]
}
```

### 5.2 ASC_TOPICS

```js
{
  id: string,          // e.g. "asc606"
  code: string,        // e.g. "ASC 606"
  title: string,
  color: string,       // hex for card stripe
  tags: string[],
  desc: string,
  points: [
    { title: string, body: string, example: string }
  ]
}
```

### 5.3 ACCOUNTING_MODULES

```js
{
  id: string,          // e.g. "mod01"
  num: string,         // e.g. "Module 1"
  title: string,
  level: "beginner" | "intermediate" | "advanced",
  desc: string,
  content: {
    intro: string,
    formula: string,
    concepts: [
      { term: string, def: string }
    ]
  }
}
```

---

## 6. Design System

### 6.1 Brand Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--spero-green` | `#152717` | Primary brand, header bg, nav rail, accents |
| `--spero-gold` | `#CCC185` | Secondary brand, highlights, card stripes, active states |
| `--spero-green-light` | `#1e3a22` | Hover states on green surfaces |
| `--charcoal` | `#1F2937` | Body text |
| `--muted-grey` | `#6B7280` | Secondary text |
| `--off-white` | `#F9FAFB` | Surface color |

### 6.2 Semantic Colors

- **Green** (`#16a34a`) -- success, completion, positive margin
- **Red** (`#dc2626`) -- danger, deletion, negative margin
- **Blue** (`#2563eb`) -- info, Milestone 1, intermediate badges
- **Purple** (`#7c3aed`) -- Exploration phase, advanced badges
- **Gold tints** (`--gold-10` through `--gold-30`) -- row alternation, hover states, subtle highlights

### 6.3 Typography

- **Font:** Inter (Google Fonts), fallback to system-ui
- **Base size:** 14px, line-height 1.6
- **Scale:** 11px (labels/tags) -> 12px (secondary) -> 13px (body small) -> 14px (body) -> 16px (section heads) -> 20px (titles) -> 26px (hero)

### 6.4 Spacing & Radius

- **Spacing scale:** 4px base (`--space-1` through `--space-10`)
- **Border radius:** `4px` (sm) / `8px` (md) / `12px` (lg) / `9999px` (pill)
- **Shadows:** 4-tier hierarchy (sm/md/lg/card) with hover variants

### 6.5 Card Patterns

- **Sidebar cards:** white bg, gold left border, green header bar
- **ASC cards:** white bg with colored top stripe (per-topic color), hover lift
- **Module cards:** white bg with gold left border, hover lift
- **Finance cards:** white bg with gold top border, hover lift
- **Summary cards:** accent-colored top borders (purple/blue/gold/green)

### 6.6 Transitions

- **Easing:** `cubic-bezier(0.4, 0, 0.2, 1)`
- **Durations:** 150ms (fast) / 200ms (base) / 300ms (slow)
- **Hover patterns:** `translateY(-1px)` lift + shadow escalation

---

## 7. Navigation Model

### 7.1 Nav Rail (Desktop)

- Fixed left column, 60px wide, full height
- Spero logo badge at top
- Icon buttons with tooltip-on-hover: Home, ASC, Modules, Solar Tracker, Help
- Active state: gold background with green icon

### 7.2 Nav Rail (Mobile, <=700px)

- Converts to fixed bottom bar, full width, 56px tall
- Icons in a horizontal row, no tooltips
- Logo hidden

### 7.3 Sidebar (Desktop, >1100px)

- 260px sticky sidebar to the right of main content
- Context-sensitive: shows ASC topic list, module list, or project details depending on current view
- Collapsible sections with accordion headers
- Hidden below 1100px breakpoint

### 7.4 Mobile Nav Panel

- Bottom-sheet overlay triggered by help/nav button
- Full sidebar content in a scrollable panel
- Backdrop blur overlay

---

## 8. File Structure

```
pocket-cpa/
  index.html          -- entire application (HTML + CSS + JSX)
  assets/
    favicon.ico       -- browser tab icon
  PRD.md              -- this file
```

---

## 9. Key Constraints

1. **No build step** -- must run by opening `index.html` or serving statically. Babel transforms JSX at runtime.
2. **No backend** -- all data in `localStorage`. No API calls, no database.
3. **No authentication** -- single-user, local-only.
4. **Single file** -- all CSS, JS, and markup live in `index.html`. No imports, no modules.
5. **CDN dependencies only** -- React, ReactDOM, Babel, and SheetJS loaded from unpkg/cdn.sheetjs.com.
6. **Client-side export only** -- reports generated as CSV (via SheetJS), JSON, or clipboard copy. No server-side rendering.
7. **localStorage limits** -- practical cap of ~5-10 MB depending on browser. No pagination or cleanup strategy currently.

---

## 10. Stretch Goals / Roadmap

- **Dark mode** -- CSS custom property architecture already supports theme switching
- **URL-based routing** -- hash or History API for bookmarkable views and back-button support
- **Search & filter** -- full-text search across ASC topics and modules; project filtering by status/date
- **Quiz mode** -- interactive self-assessment for Accounting 101 modules
- **Additional ASC topics** -- ASC 360 (PP&E), ASC 815 (Derivatives), ASC 805 (Business Combinations), ASC 860 (Transfers & Servicing)
- **Additional modules** -- Advanced topics (consolidation, foreign currency, partnerships)
- **PWA support** -- service worker for offline access, installable on mobile
- **Multi-project comparison** -- side-by-side financials across solar projects
- **Chart visualizations** -- progress over time, cost breakdown pie charts, margin trends
- **Data backup/restore** -- export/import full localStorage snapshot as JSON file
- **Print-friendly views** -- `@media print` styles for reports and financial summaries
