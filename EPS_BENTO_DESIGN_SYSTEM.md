# EPS Bento Grid Design System & Brand Specification

**Project:** Exam Proctoring System (EPS)  
**Version:** 2.0 (Bento Grid Edition)  
**Status:** Authoritative Visual Design Specification  

---

## 1. Official Four-Color Sage Brand Identity

The official EPS visual identity uses the four-color sage palette selected from Color Hunt.

| Color Name | Hex Code | RGB Values | Semantic UI Role |
| :--- | :--- | :--- | :--- |
| **Primary Sage** | `#5C7057` | `rgb(92, 112, 87)` | Main brand color, primary action buttons, active navigation indicator, brand insignia, key visual accents. |
| **Secondary Sage** | `#89A482` | `rgb(137, 164, 130)` | Secondary buttons, chart data markers, interactive card focus rings, progress tracks. |
| **Light Sage** | `#ACC5A6` | `rgb(172, 197, 166)` | Subtle card borders, secondary information containers, stat card icon backgrounds. |
| **Mint Green** | `#D1EDD3` | `rgb(209, 237, 211)` | Featured card backgrounds, active item fills, badge highlights, gentle gradient accents. |

### Supporting Neutrals & Surfaces
- **Page Canvas:** `#F6F8F4` (`--eps-page-background`)
- **Card Surface:** `#FFFFFF` (`--eps-surface`)
- **Muted Surface:** `#F0F4ED` (`--eps-surface-muted`)
- **Primary Text:** `#263026` (`--eps-text-primary`) — high contrast dark sage slate
- **Secondary Text:** `#596459` (`--eps-text-secondary`)
- **Muted Caption Text:** `#7A8979` (`--eps-text-muted`)
- **Structural Border:** `#DFE6DB` (`--eps-border`)

### Functional Status Indicators (WCAG 2.2 AA Verified)
- **Success:** `#277044` on `#EAF5EE` (Border: `#C1E5CE`)
- **Warning / Review:** `#955600` on `#FDF4E6` (Border: `#F5DEB7`)
- **Danger / Incident:** `#B42318` on `#FDF0EF` (Border: `#F7C6C3`)
- **Info:** `#356B5A` on `#EDF6F3` (Border: `#C8E3DC`)

---

## 2. Bento Grid Layout Hierarchy & Rules

The Bento Grid organizes content as an asymmetric collection of rounded cards with purposeful sizing reflecting the operational importance of each widget.

### 2.1 CSS Grid Foundation
```css
.bento-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: var(--eps-grid-gap); /* 20px */
    align-items: stretch;
    width: 100%;
}
```

### 2.2 Card Variants
- **Standard Card (`.bento-card`):** Occupies 1 column x 1 row. Used for compact metrics, quick summaries, single status indicators.
- **Wide Card (`.bento-card--wide`):** `grid-column: span 2`. Used for analytics charts, short student rosters, split form fields, proctoring audio meters.
- **Tall Card (`.bento-card--tall`):** `grid-row: span 2`. Used for live telemetry feeds, question navigation palettes, activity timelines.
- **Feature Hero Card (`.bento-card--feature`):** `grid-column: span 2; grid-row: span 2`. Used for primary workflows (e.g. Next Scheduled Exam on Student Dashboard, Pending Approval Queue on Teacher Dashboard, System Health on Admin Dashboard).
- **Three-Quarter Card (`.bento-card--3col`):** `grid-column: span 3`. Used for question editor forms and detailed exam specifications.
- **Full-Width Card (`.bento-card--full`):** `grid-column: 1 / -1`. Used for data tables, exam catalogs, gradebooks, and audit logs.
- **Mint Card (`.bento-card--mint`):** Tinted with `#D1EDD3` for prominent information callouts.
- **Primary Hero Card (`.bento-card--primary`):** Styled with gradient `#5C7057` to `#89A482` with crisp white typography.
- **Interactive Card (`.bento-card--interactive`):** Includes hover lift (`translateY(-3px)`) and subtle shadow expansion for clickable items.

---

## 3. Application Shell & Navigation

1. **Top Application Header (`.app-header`):**
   - Height: `70px` sticky top.
   - Brand logo with sage gradient leaf icon.
   - Breadcrumb navigation or page context.
   - Unread notification bell with high-contrast red counter badge.
   - User identity chip displaying avatar circle, full name, and role badge.
   - Responsive mobile hamburger menu trigger.
2. **Collapsible Desktop Sidebar (`.app-sidebar`):**
   - Width: `260px` (Expanded) / `72px` (Collapsed).
   - Dynamic role-based navigation links for **Student**, **Teacher**, and **Administrator**.
   - Active route highlighted in Mint Green (`#D1EDD3`) with Primary Sage accent bar.
   - Sidebar collapse toggle with state preservation.
3. **Public Navigation (`.public-header`):**
   - Full-width responsive header for non-authenticated visitors (Home, Login, Student Registration, Teacher Registration).

---

## 4. Typography, Radii & Elevations

- **Font Family:** `Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
- **Monospace Family:** `ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace`
- **Border Radii:**
  - Control elements (inputs, standard buttons): `12px` (`--eps-radius-control`)
  - Cards: `20px` (`--eps-radius-card`)
  - Feature containers: `26px` (`--eps-radius-feature`)
  - Badges and chips: `9999px` (`--eps-radius-full`)
- **Elevations:**
  - Card Shadow: `0 4px 20px rgb(38 48 38 / 5%), 0 1px 3px rgb(38 48 38 / 3%)`
  - Hover Shadow: `0 8px 30px rgb(38 48 38 / 8%), 0 2px 6px rgb(38 48 38 / 4%)`
  - Feature Shadow: `0 12px 36px rgb(92 112 87 / 10%), 0 2px 8px rgb(38 48 38 / 4%)`

---

## 5. Responsive Behavior & Breakpoints

- **Desktop (> 1180px):** 4-column Bento grid with unrestricted spans.
- **Tablet (768px – 1180px):** 2-column Bento grid; feature and 3-column cards automatically scale to span 2 columns.
- **Mobile (< 768px):** 1-column layout; cards stack vertically in reading order; sidebar transitions to off-canvas drawer with backdrop overlay.
