# What's Happening — Style & Production Guide

**Everything Design** · Monthly Dispatch  
Version 1.0 · June 2026  
Based on Issue 02 (May 2026)

---

## Table of Contents

1. Overview & File Architecture
2. Conversion Workflow (Standalone HTML → Webflow Embed)
3. Image Extraction & Hosting
4. Font Setup
5. Text Encoding
6. Design Tokens — Colors
7. Design Tokens — Typography
8. Design Tokens — Spacing & Layout
9. Page Types & Variants
10. Component Reference
11. Responsive CSS
12. Webflow Custom Overrides
13. Checklist for New Issues

---

## 1. Overview & File Architecture

Each issue of "What's Happening" is authored as a standalone HTML file. This file is a **bundled archive** containing three parts inside `<script>` tags:

- **`__bundler/manifest`** — A JSON blob containing all embedded assets (images as base64 JPEG/PNG/SVG/WebP/AVIF, fonts as base64 WOFF2). Each asset is keyed by a UUID.
- **`__bundler/template`** — The actual HTML content, stored as a JSON-escaped string. Image and font references use UUIDs (e.g., `src="dcac824e-b8db-4d0c-a8f1-15d9785fc96a"`).
- **`__bundler/runtime`** — A JavaScript unpacker that, at page load, replaces UUIDs with `data:` URIs.

For Webflow, we strip the bundler wrapper, extract the clean HTML, replace UUIDs with CDN URLs, and keep only the `<style>` + body content needed for an Embed element.

### Page Structure (per issue)

Each issue consists of 16 pages rendered as `<section class="page">` elements stacked inside a `<div class="stack">`. Each page contains:

```
<section class="page [variant]">
  <div class="chrome chrome--top">  <!-- Header bar: page name + page number -->
  <div class="page-body">           <!-- Main content -->
  <div class="chrome chrome--bot">  <!-- Footer bar: location + issue date -->
</section>
```

---

## 2. Conversion Workflow

### Step 1 — Extract the Template HTML

```python
import re

with open("standalone_file.html", "r", errors="ignore") as f:
    content = f.read()

# Extract the template string
tmpl = re.search(
    r'<script type="__bundler/template">\s*"(.*?)"\s*</script>',
    content, re.DOTALL
)
html = tmpl.group(1)

# Unescape JSON encoding
html = html.replace('\\u002F', '/')
html = html.replace('\\"', '"')
html = html.replace('\\n', '\n')
html = html.replace('\\t', '\t')
html = html.replace('\\\\', '\\')
```

### Step 2 — Extract All Assets from the Manifest

```python
# Pattern matches every asset in the manifest
asset_pattern = r'"([a-f0-9\-]{36})":\{"mime":"([^"]+)","compressed":(true|false),"data":"([A-Za-z0-9+/=\s]+?)"\}'

all_assets = re.findall(asset_pattern, content)
# Returns: [(uuid, mime_type, compressed, base64_data), ...]
```

Asset types you'll find:

| MIME Type | Count (typical) | Description |
|-----------|-----------------|-------------|
| `image/jpeg` | ~18 | Photos, hero images, portraits |
| `image/png` | ~8 | Logos, icons, illustrations |
| `image/svg+xml` | ~3 | Vector logos (Zuora, Fractal, Z47) |
| `image/webp` | ~2 | Optimized logos |
| `image/avif` | ~2 | Background textures |
| `font/woff2` | ~36 | Embedded font files (4 families) |

### Step 3 — Save Images to Disk

```python
import base64, os

ext_map = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/svg+xml": ".svg",
    "image/webp": ".webp",
    "image/avif": ".avif",
}

for i, (uuid, mime, compressed, b64data) in enumerate(all_assets):
    if mime.startswith("image/"):
        ext = ext_map.get(mime, ".bin")
        b64clean = b64data.replace("\n","").replace("\r","").replace(" ","")
        img_bytes = base64.b64decode(b64clean)
        
        fname = f"image_{i+1:02d}{ext}"
        with open(fname, "wb") as out:
            out.write(img_bytes)
```

### Step 4 — Upload to Webflow & Build URL Map

Upload all extracted images to Webflow Assets. Build a UUID → CDN URL mapping:

```python
uuid_to_cdn = {
    "dcac824e-b8db-4d0c-a8f1-15d9785fc96a": "https://cdn.prod.website-files.com/.../image_01.jpg",
    # ... one entry per image
}
```

**Note:** Webflow does not accept `.svg` uploads. For SVGs, keep them as inline `data:image/svg+xml;base64,...` data URIs.

### Step 5 — Replace UUIDs in HTML

```python
# Replace images with CDN URLs
for uuid, url in uuid_to_cdn.items():
    html = html.replace(uuid, url)

# Replace remaining assets (SVGs, fonts) with data URIs
for uuid, mime, compressed, b64data in all_assets:
    if uuid not in uuid_to_cdn:
        b64clean = b64data.replace("\n","").replace("\r","").replace(" ","")
        data_uri = f"data:{mime};base64,{b64clean}"
        html = html.replace(uuid, data_uri)
```

### Step 6 — Strip to Webflow Embed Format

```python
# Extract <style> blocks
styles = re.findall(r'<style>(.*?)</style>', html, re.DOTALL)

# Extract <body> content
body_match = re.search(r'<body[^>]*>(.*)</body>', html, re.DOTALL)
body = body_match.group(1)

# Remove toolbar and scripts
body = re.sub(r'<div class="toolbar"[^>]*>.*?</div>', '', body, flags=re.DOTALL)
body = re.sub(r'<script>.*?</script>', '', body, flags=re.DOTALL)

# Assemble embed HTML
embed = '<style>\n' + '\n'.join(s.strip() for s in styles) + '\n</style>\n\n' + body.strip()
```

### Step 7 — Remove Embedded Fonts, Add Google Fonts

Remove all `@font-face` blocks (they contain base64 WOFF2 data — typically 1.5 MB):

```python
embed = re.sub(r'@font-face\s*\{[^}]+\}', '', embed)
```

Prepend the Google Fonts link:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Geist+Mono:ital,wght@0,100..900;1,100..900&family=Hanken+Grotesk:ital,wght@0,100..900;1,100..900&family=Open+Sans:ital,wght@0,300..800;1,300..800&family=Petrona:ital,wght@0,100..900;1,100..900&display=swap" rel="stylesheet">
```

### Step 8 — Fix Text Encoding

Replace Unicode characters with HTML entities for reliable rendering in embed contexts:

| Character | Entity | Usage |
|-----------|--------|-------|
| `—` (em dash) | `&mdash;` | Separators, parenthetical |
| `–` (en dash) | `&ndash;` | Ranges |
| `'` (right quote) | `&rsquo;` | Apostrophes |
| `'` (left quote) | `&lsquo;` | Opening single quote |
| `"` (left double) | `&ldquo;` | Opening quote |
| `"` (right double) | `&rdquo;` | Closing quote |
| `…` (ellipsis) | `&hellip;` | Ellipsis |
| `·` (middle dot) | `&middot;` | Separator dot |

### Step 9 — Replace Inline Inch Widths

All inline `max-width` values using inches must be converted to percentages:

```python
html = re.sub(r'(max-width:\s*)[\d.]+in', r'\g<1>100%', html)
```

Fixed pixel widths should become max-widths:

```python
html = re.sub(r'width:\s*322px', 'max-width: 322px; width: 100%', html)
```

### Step 10 — Remove the Logo

Remove the Everything Design logo from the cover:

```html
<!-- REMOVE this entire div -->
<div class="logo">
  <img src="..." alt="Everything Design">
</div>
```

Restructure `.meta-stack` to horizontal layout:

```html
<div class="meta-stack" style="text-align:left; flex-direction:row; display:flex; gap:12px; align-items:baseline;">
  <span class="mono-label">Monthly Dispatch</span>
  <span class="mono-label" style="color:var(--ink);">Vol. I &middot; No. XX</span>
</div>
```

### Step 11 — Append Responsive CSS + Custom Overrides

See sections 11 and 12 below. Add these before the closing `</style>` tag.

---

## 3. Image Extraction & Hosting

### Naming Convention

Images extracted from the manifest follow this naming:

- **JPEGs:** `image_01.jpg` through `image_18.jpg` (photos, hero shots, portraits)
- **Extras:** `extra_01_ClientName.png`, `extra_02_ClientName.png`, etc. (logos, icons)

### What Goes to Webflow CDN

| Format | Upload to Webflow? | Handling |
|--------|-------------------|----------|
| `.jpg` | Yes | Replace UUID with CDN URL |
| `.png` | Yes | Replace UUID with CDN URL |
| `.webp` | Yes | Replace UUID with CDN URL |
| `.avif` | Yes | Replace UUID with CDN URL |
| `.svg` | No (not supported) | Keep as inline `data:` URI |

### Typical Image Inventory (Issue 02)

| # | Image | Type | Description |
|---|-------|------|-------------|
| 01-18 | `image_XX.jpg` | JPEG | Content photos, project screenshots, portraits |
| extra_01-06 | Client logos | PNG | Mojro, Cloudphysician, 91 Ninjas, Kandou AI, Light Metrics, Becoming Quotient |
| extra_07-09 | Client logos | SVG | Zuora, Fractal, Z47 (keep inline) |
| extra_10 | Header logo | WebP | Everything Design logo (removed in final) |
| extra_11-12 | Client logos | PNG | Turno, Ayr Energy |
| extra_13 | Illustration | PNG | "What an opportunity" graphic |
| extra_14-15 | Backgrounds | PNG | Decorative backgrounds |
| extra_16-17 | Backgrounds | AVIF | Decorative backgrounds |

---

## 4. Font Setup

### Families

| CSS Variable | Font Family | Weight Range | Usage |
|-------------|-------------|--------------|-------|
| `--sans` | Open Sans | 300–800 | Body text, descriptions |
| `--display` | Petrona | 100–900 | Headings, display text, quotes |
| `--mono` | Geist Mono | 100–900 | Labels, tags, metadata, eyebrows |
| (direct) | Hanken Grotesk | 100–900 | BQ highlight section only |

### Fallback Stacks

```css
--sans: "Open Sans", -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
--display: "Petrona", "Newsreader", Georgia, serif;
--mono: "Geist Mono", ui-monospace, "JetBrains Mono", Menlo, monospace;
```

### Google Fonts Embed

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Geist+Mono:ital,wght@0,100..900;1,100..900&family=Hanken+Grotesk:ital,wght@0,100..900;1,100..900&family=Open+Sans:ital,wght@0,300..800;1,300..800&family=Petrona:ital,wght@0,100..900;1,100..900&display=swap" rel="stylesheet">
```

---

## 5. Text Encoding

The standalone HTML uses native Unicode characters. When stripped of the `<meta charset="utf-8">` tag for Webflow embedding, browsers may misinterpret these as mojibake (`â€"`, `â€™`, etc.).

**Rule:** Always convert special characters to HTML entities before embedding. See the entity table in Step 8 above.

---

## 6. Design Tokens — Colors

### Default Theme (Light Pages)

```css
--paper:         #ffffff;       /* Page background */
--paper-2:       #f3f1ec;       /* Secondary background / image placeholders */
--paper-3:       #e9e4d8;       /* Tertiary background */

--ink:           #0e0d0c;       /* Primary text */
--ink-2:         #2a2723;       /* Body text */
--ink-3:         #4a463e;       /* Secondary text */
--muted:         #6a655c;       /* Muted text / labels */
--muted-2:       #8a8478;       /* Lighter muted */

--rule:          #0e0d0c14;     /* Faintest rule (8% opacity) */
--rule-2:        #0e0d0c33;     /* Dotted rules (20% opacity) */
--rule-3:        #0e0d0c66;     /* Stronger rules (40% opacity) */

--accent:        #ff542d;       /* Primary accent (orange-red) */
--accent-press:  #c93a17;       /* Accent pressed state */
--accent-soft:   #ffd7c9;       /* Accent soft background */
--accent-2:      #f5a623;       /* Secondary accent (gold) */

--on-ink:        #ffffff;       /* Text on dark backgrounds */
--on-ink-2:      #d9d4c5;       /* Secondary text on dark */
--on-ink-muted:  #c2bcad;       /* Muted text on dark */
--on-ink-rule:   #ffffff1e;     /* Rules on dark backgrounds */
```

### Dark Page Theme (`page--dark`)

Dark pages use the same variables but invert `--paper` and `--ink` contextually. The dark background comes from the `.clients-strip` and `.closing` components which use `background: var(--ink)` and `color: var(--on-ink)`.

### BQ Highlight Theme (`page--bq`)

```css
--bq-paper:  #f4f1e6;          /* Warm cream background */
--bq-ink:    #16276b;          /* Deep navy text */
--bq-olive:  #8c9a36;          /* Olive accent */
--bq-yellow: #f3e84f;          /* Yellow accent */
--bq-ochre:  #c79a3f;          /* Ochre accent */
```

---

## 7. Design Tokens — Typography

### Type Scale (CSS Variables)

```css
--t-mega:     124px;    /* Hero / splash numbers */
--t-cover:     96px;    /* Cover headline */
--t-display:   62px;    /* Section display */
--t-h1:        54px;    /* Heading 1 */
--t-h2:        42px;    /* Heading 2 */
--t-h3:        30px;    /* Heading 3 */
--t-h4:        24px;    /* Heading 4 */
--t-h5:        18px;    /* Heading 5 */
--t-h6:        15px;    /* Heading 6 */
--t-body:      14.5px;  /* Body text */
--t-body-lg:   16px;    /* Large body */
--t-small:     11.5px;  /* Small text */
--t-mono:      10.5px;  /* Mono labels */
--t-mono-sm:    9.5px;  /* Small mono */
```

### Typography Classes

**Editorial headings** (use CSS variable scale):

| Class | Font | Weight | Size | Line Height | Tracking |
|-------|------|--------|------|-------------|----------|
| `.ed-mega` | `--display` | 800 | `--t-mega` | 0.88 | -0.045em |
| `.ed-cover` | `--display` | 800 | `--t-cover` | 0.92 | -0.04em |
| `.ed-display` | `--display` | 700 | `--t-display` | 0.95 | -0.035em |
| `.ed-h1` | `--display` | 700 | `--t-h1` | 0.95 | -0.035em |
| `.ed-h2` | `--display` | 700 | `--t-h2` | 0.96 | -0.03em |
| `.ed-h3` | `--display` | 700 | `--t-h3` | 1.0 | -0.025em |
| `.ed-h4` | `--display` | 700 | `--t-h4` | 1.05 | -0.02em |
| `.ed-h5` | `--display` | 600 | `--t-h5` | 1.2 | -0.01em |
| `.ed-h6` | `--display` | 600 | `--t-h6` | 1.25 | -0.005em |
| `.ed-body` | `--sans` | 400 | `--t-body` | 1.5 | — |
| `.ed-body-lg` | `--sans` | 400 | `--t-body-lg` | 1.45 | -0.005em |
| `.ed-small` | `--sans` | 400 | `--t-small` | 1.45 | — |

**Layout headings** (fixed sizes):

| Class | Font | Weight | Size | Line Height |
|-------|------|--------|------|-------------|
| `.h-display` | `--display` | 700 | 48px | 0.98 |
| `.h-big` | `--display` | 700 | 38px | 1.02 |
| `.h-mid` | `--display` | 700 | 26px | 1.08 |
| `.recent` / `.updates` | `--display` | 800 | 108px | 0.88 |
| `.cover-quote` | `--display` | 800 | 60px | 0.99 |
| `.quote` | `--display` | 700 | 30px | 1.12 |
| `.bq-catch` | Hanken Grotesk | 800 | 62px | 0.92 |

**Body & labels:**

| Class | Font | Weight | Size | Line Height |
|-------|------|--------|------|-------------|
| `.body` | `--sans` | 400 | 14.5px | 1.5 |
| `.body-lg` | `--sans` | 400 | 16px | 1.45 |
| `.small` | `--sans` | 400 | 11.5px | 1.45 |
| `.eyebrow` | `--mono` | — | 10.5px | — |
| `.mono-label` | `--mono` | — | 10px | — |
| `.tag` | `--mono` | — | 9px | — |
| `.chip` | `--mono` | — | 10px | — |
| `.pill` | `--mono` | — | 9.5px | — |
| `.credit` | `--mono` | — | 9px | — |

All mono-set text uses `text-transform: uppercase` and `letter-spacing: 0.12em–0.16em`.

### Tracking Variables

```css
--track-mono:     0.16em;
--track-mono-sm:  0.08em;
--track-tight:   -0.025em;
--track-display: -0.035em;
--track-mega:    -0.045em;
```

---

## 8. Design Tokens — Spacing & Layout

### Page Dimensions

```css
--page-w:  210mm;     /* A4 width (becomes 100% on responsive) */
--page-h:  297mm;     /* A4 height (becomes auto on responsive) */
--pad-x:    16mm;     /* Horizontal padding */
--pad-y:    16mm;     /* Vertical padding */
```

### Spacing Scale

```css
--space-1:   4px;
--space-2:   8px;
--space-3:  12px;
--space-4:  16px;
--space-5:  20px;
--space-6:  24px;
--space-7:  32px;
--space-8:  40px;
--space-9:  56px;
--space-10: 80px;
```

### Border Radii

```css
--radius-1:  2px;      /* Cards, features */
--radius-2:  3px;      /* Client cards */
--radius-3:  999px;    /* Pills, tags, CTAs (fully rounded) */
```

### Shadows

```css
--shadow-page: 0 24px 60px -20px rgba(0,0,0,0.5), 0 4px 10px rgba(0,0,0,0.2);
--shadow-soft: 0 10px 30px rgba(0,0,0,0.08);
```

### Rule Patterns

- **Dashed:** `1px dashed var(--ink)` — Major section dividers
- **Dotted:** `1px dotted var(--rule-2)` — Item separators, minor dividers
- **Solid:** `1px solid var(--ink)` — Card borders, feature borders

---

## 9. Page Types & Variants

### All 16 Pages (Issue 02)

| # | Label | Class | Description |
|---|-------|-------|-------------|
| 01 | Cover | `.page.cover` | Hero quote, stats strip, feature image |
| 02 | Contents | `.page` | Table of contents, 34 entries |
| 03 | Editor | `.page` | Editor's note, at-a-glance stats |
| 04–09 | Updates A–F | `.page` | Project update logs (detailed + compact) |
| 10 | Updates G | `.page` | Final updates page |
| 10 | Clients | `.page.page--dark` | Client logo grid (dark background) |
| 11 | BQ Highlight | `.page.page--bq` | Becoming Quotient spotlight (custom palette) |
| 13 | Studio | `.page.page--dark` | Studio note (dark background) |
| 14 | Quotes | `.page` | Client testimonials |
| 15 | Closing | `.page` | Sign-off, monthly picks, CTA |
| 16 | Back Cover | `.page.page--dark` | LinkedIn CTAs (dark) |

### Page Variant Classes

- **`.page`** — Default light theme
- **`.page.cover`** — Cover page (special layout, no top margin on page-body)
- **`.page.page--dark`** — Dark background (`var(--ink)` bg, `var(--on-ink)` text)
- **`.page.page--bq`** — BQ highlight (custom `--bq-*` color palette)

---

## 10. Component Reference

### Chrome Bars

```html
<div class="chrome chrome--top">   <!-- Page name + number -->
<div class="chrome chrome--bot">   <!-- Location + issue info -->
```

Position: Absolute in base, static on responsive. Contains mono-label text.

### Section Opener

```html
<div class="section-opener">
  <div class="eyebrow-block">
    <span class="eyebrow">Section Name</span>
    <h2 class="h-display">Title</h2>
  </div>
  <span class="mono-label">Subtitle</span>
</div>
```

Grid: `1fr auto` — collapses to `1fr` on responsive.

### Update Entry (Detailed)

```html
<div class="update">
  <div class="left">         <!-- Image + tags -->
  <div class="right">        <!-- Title, description, credits -->
</div>
```

Grid: `0.62fr 1fr` — collapses to `1fr` on responsive.

### Update Entry (Compact)

```html
<div class="compact-row">    <!-- Number, title, meta, tags -->
```

Grid: `36px 1.5fr 1fr auto` — collapses to `1fr` on responsive.

### Cover Feature

```html
<div class="cover-feature">
  <a class="img-link"><img class="img"></a>
  <div class="copy">         <!-- 1.5fr 1fr grid: description + metadata -->
</div>
```

### Stat Strips

```html
<div class="cover-stamp-row">   <!-- 4-column grid -->
  <div class="cover-stamp">     <!-- Label + value -->
</div>

<div class="mat-stats">         <!-- 4-column grid -->
  <div class="mat-stat">        <!-- Label + value -->
</div>
```

### Client Grid

```html
<div class="clients-strip">     <!-- Dark background container -->
  <div class="clients-grid">    <!-- 4-column grid -->
    <div class="client-cell">
      <div class="client-card"> <!-- Logo card -->
      <span class="sub">        <!-- Client name -->
    </div>
  </div>
</div>
```

### Closing Card

```html
<div class="closing">           <!-- 1.1fr 1fr dark grid -->
  <div class="left">            <!-- Main message + CTA -->
  <div class="right">           <!-- Secondary content -->
</div>
```

### Tags & Pills

```html
<span class="pill"><span class="dot"></span>Status</span>
<div class="chips"><span class="chip">Tag</span></div>
<div class="tags"><span class="tag"><span class="d"></span>Label</span></div>
```

### BQ Components

```html
<div class="bq-top">            <!-- Logo + eyebrow -->
<div class="bq-hero">           <!-- Large catch phrase + subtitle -->
<div class="bq-grid">           <!-- 1fr 1fr grid: narrative + body -->
<div class="bq-quotes">         <!-- Testimonials -->
<div class="bq-stamps">         <!-- Stats (4-column) -->
<div class="bq-band">           <!-- Bottom accent bar -->
```

---

## 11. Responsive CSS

### Breakpoints

| Name | Width | Rationale |
|------|-------|-----------|
| Tablet | ≤ 1024px | Catches Webflow containers that are narrower than viewport |
| Mobile | ≤ 768px | Standard mobile breakpoint |
| Small Mobile | ≤ 480px | Narrow phones |

### What Changes at Each Breakpoint

**Tablet (≤ 1024px):**

- `.page` becomes `width: 100%`, `min-height: auto`, no box-shadow
- Chrome bars switch from `position: absolute` to `position: static` (prevents overlap)
- All 4-column grids become 2-column
- All 2-column grids become 1-column
- Heading line-heights increase (0.88→1.05, 0.92→1.08, etc.)
- Large display text scales down (108px→60px, 60px→38px, 62px→40px)
- `white-space: nowrap` removed from tags and meta
- Inline `max-width` values in inches become `100%`
- Inline grid layouts override with `!important` attribute selectors
- BQ grid stacks, body padding-left removed

**Mobile (≤ 768px):**

- Typography scale drops further (mega 36px, cover 32px, display 26px)
- Cover layout stacks vertically
- All inline font sizes scale down (37px→20px, 22px→17px, 18px→15px)
- Chrome bars smaller (7px font)
- Stamps/stats padding reduced

**Small Mobile (≤ 480px):**

- Tightest type scale (mega 28px, cover 26px)
- 4-column stamp/stat grids become 1-column
- Clients grid remains 2-column

### Chrome Bar Handling

The chrome bars are the most critical responsive fix. At base, they're absolutely positioned with `top: 0.4in` / `bottom: 0.4in`. On responsive, they must become static:

```css
@media screen and (max-width: 1024px) {
  .chrome,
  .chrome.chrome--top,
  .chrome.chrome--bot {
    position: static !important;
    left: auto !important;
    right: auto !important;
    top: auto !important;
    bottom: auto !important;
  }
}
```

### Inline Grid Override Pattern

Grids defined with `style="grid-template-columns: ..."` need attribute selectors:

```css
@media screen and (max-width: 1024px) {
  [style*="grid-template-columns: 1fr 1fr 1fr"],
  [style*="grid-template-columns: repeat(3, 1fr)"],
  [style*="grid-template-columns: 1fr 1fr"],
  [style*="grid-template-columns: 1fr 0.62fr"],
  [style*="grid-template-columns: 0.5fr 1fr"],
  [style*="grid-template-columns: 1.25fr 1fr"],
  [style*="grid-template-columns: 0.9fr 1fr"] {
    grid-template-columns: 1fr !important;
  }
}
```

---

## 12. Webflow Custom Overrides

These are applied on top of the extracted CSS:

```css
/* Image border radius reset */
.img { border-radius: 0px; }

/* Transparent body for Webflow container */
.body { background-color: transparent; }

/* Brand cards */
.brand { display: block; padding: 0px; height: auto; }

/* Tags horizontal layout */
.tag { flex-direction: row; align-items: center; }
```

### Base Responsive Safety (no media query needed)

```css
.page { max-width: 100%; }
.stack { max-width: 100%; }
img { max-width: 100%; height: auto; }
```

---

## 13. Checklist for New Issues

Use this checklist when converting a new issue of "What's Happening" for Webflow:

### Extraction

- [ ] Open the standalone HTML file
- [ ] Extract template HTML from `__bundler/template` script tag
- [ ] Unescape JSON encoding (`\\u002F`, `\\"`, `\\n`, `\\t`, `\\\\`)
- [ ] Extract all image assets from `__bundler/manifest`
- [ ] Save images to disk with proper extensions

### Image Handling

- [ ] Upload all `.jpg`, `.png`, `.webp`, `.avif` images to Webflow Assets
- [ ] Record CDN URLs for each uploaded image
- [ ] Build UUID → CDN URL mapping
- [ ] Keep `.svg` images as inline data URIs
- [ ] Replace all UUIDs in HTML with CDN URLs / data URIs
- [ ] Verify zero bare UUIDs remain

### Fonts

- [ ] Remove all `@font-face` blocks from the CSS
- [ ] Add Google Fonts `<link>` tags at the top of the file
- [ ] Verify CSS variables (`--sans`, `--display`, `--mono`) still reference correct families

### Encoding & Cleanup

- [ ] Replace Unicode em dashes, quotes, ellipses with HTML entities
- [ ] Replace inline `max-width` inch values with `100%`
- [ ] Convert fixed `width: Xpx` to `max-width: Xpx; width: 100%`
- [ ] Strip `<html>`, `<head>`, `<body>` wrappers
- [ ] Remove toolbar div and inline `<script>` blocks

### Cover Customization

- [ ] Remove Everything Design logo from `.cover-top`
- [ ] Update `.meta-stack` to horizontal layout
- [ ] Update issue number, date, and volume in meta labels

### Responsive CSS

- [ ] Append custom overrides (`.img`, `.body`, `.brand`, `.tag`)
- [ ] Append base responsive safety (max-width: 100% on page, images)
- [ ] Append tablet breakpoint (≤ 1024px)
- [ ] Append mobile breakpoint (≤ 768px)
- [ ] Append small mobile breakpoint (≤ 480px)
- [ ] Include inline grid attribute-selector overrides
- [ ] Include BQ page-specific responsive fixes

### Final Verification

- [ ] Open the file in a browser at full width — confirm layout matches original
- [ ] Resize to tablet width (~768px) — all grids collapse, chrome bars in flow
- [ ] Resize to mobile width (~375px) — text readable, no overlap, no horizontal scroll
- [ ] Check all images load from CDN
- [ ] Check fonts render (Petrona for headings, Open Sans for body, Geist Mono for labels)
- [ ] Check no mojibake characters (`â€"`, `â€™`, etc.)
- [ ] Paste into Webflow Embed element and preview
- [ ] Test on actual mobile device

---

*This guide should be updated as the design system evolves with future issues.*
