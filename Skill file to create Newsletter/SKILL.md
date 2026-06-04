---
name: whats-happening-webflow
description: "Convert the Everything Design 'What's Happening' standalone HTML newsletter into a Webflow-ready embed. Triggers on any upload of a standalone HTML file that is a 'What's Happening' newsletter issue, or requests like 'convert this newsletter for Webflow', 'prepare this for Webflow embed', 'extract images from the newsletter', 'process the new What's Happening issue', 'convert the monthly dispatch', or any mention of 'What's Happening' combined with Webflow, embed, images, or conversion. Also triggers when the user mentions 'What's Happening Issue' followed by a number. This skill MUST be used whenever a standalone bundled HTML newsletter file is uploaded — do not attempt manual conversion without following this skill."
---

# What's Happening → Webflow Embed Conversion

This skill converts the Everything Design "What's Happening" monthly newsletter from a standalone bundled HTML file into a clean Webflow embed, extracting all assets as individual files.

## Overview

The source file is a **bundled standalone HTML** containing three `<script>` blocks:

1. `__bundler/manifest` — JSON blob with all images (JPEG, PNG, SVG, WebP, AVIF) and fonts (WOFF2) as base64 data, keyed by UUID
2. `__bundler/template` — The actual HTML content as a JSON-escaped string, referencing assets by UUID
3. `__bundler/runtime` — JavaScript unpacker (discarded)

The output is:
- **All images** extracted as individual files (JPG, PNG, WebP, AVIF, SVG) for upload to Webflow Assets
- **A clean HTML file** with UUID placeholders ready to swap for Webflow CDN URLs
- **Fonts loaded via Google Fonts** import link (not base64)
- **Responsive CSS** appended for mobile/tablet
- **Encoding-safe** text using HTML entities

---

## Step-by-Step Workflow

### Step 1: Run the Conversion Script

When the user uploads the standalone HTML file, run the conversion script:

```bash
python3 /path/to/skill/scripts/convert.py "/mnt/user-data/uploads/FILENAME.html"
```

This script does everything automatically:
1. Extracts the template HTML from the bundler
2. Unescapes JSON encoding
3. Extracts ALL images as individual files to `/mnt/user-data/outputs/`
4. Extracts font information (family names, weights)
5. Removes all `@font-face` blocks
6. Replaces UUIDs with placeholder filenames (e.g., `{{image_01.jpg}}`)
7. Fixes text encoding (Unicode → HTML entities)
8. Fixes inline inch-based widths
9. Strips HTML/HEAD/BODY wrappers, toolbar, scripts
10. Removes the Everything Design logo from cover
11. Restructures cover meta-stack to horizontal layout
12. Prepends Google Fonts `<link>` tags
13. Appends responsive CSS + custom overrides
14. Writes the final HTML to `/mnt/user-data/outputs/webflow_embed.html`

### Step 2: Present All Extracted Images

After the script runs, present all image files to the user using `present_files`. Group them clearly:

```
Content images (JPEGs):     image_01.jpg — image_XX.jpg
Client logos (PNG/WebP):    extra_01_ClientName.png, etc.
Vector logos (SVG):         extra_XX_Name.svg (note: Webflow doesn't host SVGs)
Backgrounds (PNG/AVIF):    extra_XX_background.ext
```

Tell the user:
> "Here are all the extracted images. Upload them to Webflow Assets and share the CDN URLs back. I'll replace the placeholders in the HTML with your URLs."
>
> **Note:** SVG files can't be uploaded to Webflow. These will stay as inline data URIs in the HTML.

### Step 3: Receive CDN URLs and Finalize

When the user shares CDN URLs, match each URL to its placeholder filename based on the filename in the URL (e.g., a URL ending in `_image_05.jpg` maps to `{{image_05.jpg}}`).

Run the replacement:

```python
for url in user_urls:
    # Extract the original filename from the CDN URL
    # e.g., "6a205243_image_05.jpg" → "image_05.jpg"
    filename = extract_filename(url)
    html = html.replace("{{" + filename + "}}", url)
```

For any remaining `{{...}}` placeholders (SVGs without CDN URLs), replace with the inline `data:` URI from the extracted data.

### Step 4: Present Final HTML

Present the final `webflow_embed.html` to the user. Confirm:
- Zero remaining `{{...}}` placeholders
- Zero bare UUIDs
- File size (should be ~50–100 KB if all images are CDN-hosted, up to ~250 KB if SVGs remain inline)

---

## Google Fonts Configuration

**Always use this exact link** — do not embed fonts as base64:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Geist+Mono:ital,wght@0,100..900;1,100..900&family=Hanken+Grotesk:ital,wght@0,100..900;1,100..900&family=Open+Sans:ital,wght@0,300..800;1,300..800&family=Petrona:ital,wght@0,100..900;1,100..900&display=swap" rel="stylesheet">
```

### Font Families

| CSS Variable | Font | Usage |
|-------------|------|-------|
| `--sans` | Open Sans | Body text, descriptions |
| `--display` | Petrona | Headings, display text, quotes |
| `--mono` | Geist Mono | Labels, tags, metadata, eyebrows |
| (direct use) | Hanken Grotesk | BQ highlight section only |

---

## Responsive CSS

The responsive CSS is appended automatically by the conversion script. Three breakpoints:

| Breakpoint | Width | Key Changes |
|-----------|-------|-------------|
| Tablet | ≤ 1024px | Page 100% width, chrome bars static, 4→2 col grids, 2→1 col grids |
| Mobile | ≤ 768px | Smaller type scale, all grids 1 col, cover stacks vertically |
| Small | ≤ 480px | Tightest type scale, stamp grids 1 col |

### Critical Responsive Fixes

1. **Chrome bars** — Must switch from `position: absolute` to `position: static` to prevent text overlap
2. **Inline grid layouts** — Must use `[style*="grid-template-columns"]` attribute selectors with `!important` to override inline styles
3. **Heading line-heights** — Must increase from tight values (0.88, 0.92) to looser values (1.05, 1.1) to prevent line overlap when text wraps
4. **BQ page** — `.bq-grid` and `.bq-body` need specific overrides for padding and stacking

### Custom Webflow Overrides

Always included in the responsive CSS block:

```css
.img { border-radius: 0px; }
.body { background-color: transparent; }
.brand { display: block; padding: 0px; height: auto; }
.tag { flex-direction: row; align-items: center; }
```

---

## Text Encoding Rules

**Always replace these Unicode characters with HTML entities** before outputting the final HTML. This prevents mojibake (`â€"`, `â€™`) when the embed lacks a charset declaration:

| Character | Entity | Usage |
|-----------|--------|-------|
| — (em dash) | `&mdash;` | Separators |
| – (en dash) | `&ndash;` | Ranges |
| ' (right quote) | `&rsquo;` | Apostrophes |
| ' (left quote) | `&lsquo;` | Open single quote |
| " (left double) | `&ldquo;` | Open double quote |
| " (right double) | `&rdquo;` | Close double quote |
| … (ellipsis) | `&hellip;` | Ellipsis |
| · (middle dot) | `&middot;` | Separators |
|   (nbsp) | `&nbsp;` | Non-breaking space |

---

## Cover Customizations

For every issue, apply these changes to the cover page:

1. **Remove** the `<div class="logo">` containing the Everything Design image
2. **Restructure** `.meta-stack` to horizontal:
```html
<div class="meta-stack" style="text-align:left; flex-direction:row; display:flex; gap:12px; align-items:baseline;">
  <span class="mono-label">Monthly Dispatch</span>
  <span class="mono-label" style="color:var(--ink);">Vol. I &middot; No. XX</span>
</div>
```
3. **Update** the issue number and volume to match the current issue

---

## Image Naming Convention

The script names extracted images based on their order in the manifest and their alt text (if available):

- **JPEG content images**: `image_01.jpg` through `image_XX.jpg`
- **Non-JPEG assets**: `extra_XX_AltText.ext` (e.g., `extra_03_91_Ninjas.png`)
- **Backgrounds without alt text**: `extra_XX_background.ext`

### Webflow Upload Rules

| Format | Upload to Webflow? | In HTML as... |
|--------|-------------------|---------------|
| `.jpg` | ✅ Yes | CDN URL |
| `.png` | ✅ Yes | CDN URL |
| `.webp` | ✅ Yes | CDN URL |
| `.avif` | ✅ Yes | CDN URL |
| `.svg` | ❌ No | Inline `data:` URI |

---

## Design System Reference

For the full design token reference (colors, typography scale, spacing, components), see `references/style_guide.md` in this skill folder.

### Key Color Tokens

```
Default:  --paper: #ffffff  --ink: #0e0d0c  --accent: #ff542d
Dark:     background: var(--ink)  color: var(--on-ink) (#ffffff)
BQ:       --bq-paper: #f4f1e6  --bq-ink: #16276b  --bq-olive: #8c9a36
```

### Page Variants

| Class | Usage |
|-------|-------|
| `.page` | Default light page |
| `.page.cover` | Cover page |
| `.page.page--dark` | Dark background (clients, studio, back cover) |
| `.page.page--bq` | BQ highlight (custom navy/cream palette) |

---

## Troubleshooting

### Text overlapping on mobile
The chrome bars (`chrome--top`, `chrome--bot`) are absolutely positioned at base. The responsive CSS switches them to `position: static`. If overlap persists, verify the responsive CSS was appended correctly and the breakpoint triggers at ≤ 1024px.

### Fonts not loading
Ensure the Google Fonts `<link>` tags are at the very top of the embed HTML, before `<style>`. The CSS variables `--sans`, `--display`, `--mono` must reference the correct font names.

### Mojibake characters (â€", â€™)
Run the encoding fix step. All em dashes, smart quotes, and ellipses must be HTML entities.

### Images not showing
Verify UUIDs were fully replaced. Search the HTML for any remaining UUID pattern (`[a-f0-9]{8}-[a-f0-9]{4}-...`). If found, check the manifest extraction step.

### Inline grids not collapsing
Grids set via `style="grid-template-columns: ..."` require attribute selector overrides with `!important`. Verify these selectors are in the responsive CSS block.
