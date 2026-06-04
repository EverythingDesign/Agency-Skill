#!/usr/bin/env python3
"""
What's Happening → Webflow Embed Converter

Converts the Everything Design standalone bundled HTML newsletter
into a clean Webflow embed, extracting all images as individual files.

Usage:
    python3 convert.py "/path/to/standalone.html" [--output-dir /mnt/user-data/outputs]

Outputs:
    - All images as individual files (image_01.jpg, extra_01_Name.png, etc.)
    - webflow_embed.html — clean HTML ready for Webflow (with {{filename}} placeholders)
    - asset_manifest.json — UUID-to-filename mapping for reference
"""

import re
import base64
import os
import sys
import json


# ── Configuration ──────────────────────────────────────────────────

GOOGLE_FONTS_LINK = """<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Geist+Mono:ital,wght@0,100..900;1,100..900&family=Hanken+Grotesk:ital,wght@0,100..900;1,100..900&family=Open+Sans:ital,wght@0,300..800;1,300..800&family=Petrona:ital,wght@0,100..900;1,100..900&display=swap" rel="stylesheet">

"""

EXT_MAP = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/svg+xml": ".svg",
    "image/webp": ".webp",
    "image/avif": ".avif",
}

ENCODING_FIXES = {
    '\u2014': '&mdash;',
    '\u2013': '&ndash;',
    '\u2019': '&rsquo;',
    '\u2018': '&lsquo;',
    '\u201C': '&ldquo;',
    '\u201D': '&rdquo;',
    '\u2026': '&hellip;',
    '\u2022': '&bull;',
    '\u00A0': '&nbsp;',
    '\u2009': '&thinsp;',
    '\u200B': '&#8203;',
}


# ── Responsive CSS ─────────────────────────────────────────────────

RESPONSIVE_CSS = """

/* ==============================
   BASE RESPONSIVE SAFETY
   ============================== */
*, *::before, *::after { box-sizing: border-box; }
.page { max-width: 100%; }
.stack { max-width: 100%; }
img { max-width: 100%; height: auto; }

.ed-mega, .ed-cover, .ed-display, .ed-h1, .ed-h2, .ed-h3, .ed-h4, .ed-h5,
.h-display, .h-big, .h-mid, .recent, .updates, .cover-quote, .quote,
.bq-catch, .text-mark, .brand, .title, .name, .v, .n, .desc, p, span, div {
  overflow-wrap: break-word;
  word-wrap: break-word;
}

/* ==============================
   CUSTOM CSS (Webflow overrides)
   ============================== */
.img { border-radius: 0px; }
.body { background-color: transparent; }
.brand { display: block; padding: 0px; height: auto; }
.tag { flex-direction: row; align-items: center; }

/* ==============================
   TABLET (≤ 1024px)
   ============================== */
@media screen and (max-width: 1024px) {

  .page {
    width: 100% !important;
    min-height: auto !important;
    padding: 24px 20px !important;
    box-shadow: none !important;
    overflow: visible !important;
    position: relative;
  }

  :root, .page {
    --pad-x: 20px;
    --pad-y: 20px;
    --page-w: 100%;
    --page-h: auto;
    --t-mega: 60px;
    --t-cover: 50px;
    --t-display: 36px;
    --t-h1: 32px;
    --t-h2: 26px;
    --t-h3: 22px;
  }

  .stack { padding: 0 !important; }

  /* Chrome bars: pull into normal document flow */
  .chrome, .chrome.chrome--top, .chrome.chrome--bot {
    position: static !important;
    left: auto !important; right: auto !important;
    top: auto !important; bottom: auto !important;
    width: 100%;
    padding: 10px 0;
    border-bottom: 1px dotted var(--rule-2);
    margin-bottom: 10px;
    font-size: 9px !important;
  }
  .chrome.chrome--bot {
    border-bottom: none;
    border-top: 1px dotted var(--rule-2);
    margin-bottom: 0; margin-top: 12px; padding-top: 10px;
  }
  .page--dark .chrome.chrome--bot, .page--dark .chrome.chrome--top { border-color: var(--on-ink-rule); }
  .page--bq .chrome.chrome--bot, .page--bq .chrome.chrome--top { border-color: rgba(22,39,107,0.18); }

  .page-body { margin-top: 0 !important; }

  /* Heading line-heights: prevent overlap on wrap */
  .ed-mega { line-height: 1.05 !important; }
  .ed-cover { line-height: 1.08 !important; }
  .ed-display { line-height: 1.1 !important; }
  .ed-h1 { line-height: 1.1 !important; }
  .ed-h2 { line-height: 1.1 !important; }
  .ed-h3 { line-height: 1.12 !important; }

  .h-display { font-size: 34px !important; line-height: 1.1 !important; }
  .h-big { font-size: 28px !important; line-height: 1.12 !important; }
  .h-mid { font-size: 22px !important; line-height: 1.18 !important; }
  .recent, .updates { font-size: 60px !important; line-height: 0.95 !important; }
  .cover-quote { font-size: 38px !important; line-height: 1.1 !important; }
  .quote { font-size: 24px !important; line-height: 1.22 !important; }
  .bq-catch { font-size: 40px !important; line-height: 1.05 !important; }

  .tag, .meta { white-space: normal !important; }
  [style*="max-width"] { max-width: 100% !important; }

  /* Grid collapses */
  .cover-stamp-row, .mat-stats, .clients-grid, .bq-stamps {
    grid-template-columns: repeat(2, 1fr) !important;
  }
  .editor-grid, .copy, .bq-grid, .closing, .toc-list {
    grid-template-columns: 1fr !important;
  }
  .update { grid-template-columns: 1fr !important; gap: 12px !important; }
  .compact-row { grid-template-columns: 1fr !important; gap: 8px !important; }
  .tags-col { justify-content: flex-start !important; max-width: none !important; }
  .section-opener { grid-template-columns: 1fr !important; gap: 12px !important; }
  .cover-epigraph { grid-template-columns: 1fr !important; gap: 14px !important; }
  .cover-sub { max-width: 100% !important; }

  .closing .right {
    border-left: none !important; padding-left: 0 !important;
    border-top: 1px solid var(--on-ink-rule); padding-top: 16px;
  }
  .clients-strip { margin-left: 0 !important; margin-right: 0 !important; padding-left: 0 !important; padding-right: 0 !important; }
  .bq-band { margin-left: calc(var(--pad-x) * -1) !important; margin-right: calc(var(--pad-x) * -1) !important; flex-direction: column !important; gap: 8px !important; }
  .cover-eyebrow-row, .cover-masthead { flex-wrap: wrap; gap: 8px; }
  .bq-shot { height: auto !important; max-height: 250px; }
  .img { min-height: 0 !important; }

  /* BQ page */
  .bq-grid { grid-template-columns: 1fr !important; gap: 20px !important; }
  .bq-body { padding-left: 0 !important; }
  .bq-top { flex-direction: column !important; align-items: flex-start !important; gap: 10px; }
  .bq-stamps { grid-template-columns: 1fr !important; }

  /* Inline grid overrides (higher specificity than inline styles) */
  [style*="grid-template-columns: 1fr 1fr 1fr"],
  [style*="grid-template-columns: repeat(3, 1fr)"] {
    grid-template-columns: 1fr !important; gap: 12px !important;
  }
  [style*="grid-template-columns: 1fr 1fr"],
  [style*="grid-template-columns: 1fr 0.62fr"],
  [style*="grid-template-columns: 0.5fr 1fr"],
  [style*="grid-template-columns: 1.25fr 1fr"],
  [style*="grid-template-columns: 0.9fr 1fr"] {
    grid-template-columns: 1fr !important; gap: 12px !important;
  }

  /* Inline font size scaling */
  [style*="font-size: 37px"], [style*="font-size:37px"] { font-size: clamp(22px, 5vw, 37px) !important; line-height: 1.18 !important; }
  [style*="font-size: 34px"], [style*="font-size:34px"] { font-size: clamp(22px, 5vw, 34px) !important; line-height: 1.18 !important; }
  [style*="font-size: 22px"], [style*="font-size:22px"] { line-height: 1.22 !important; }
  [style*="font-size: 18px"], [style*="font-size:18px"] { line-height: 1.4 !important; }
  [style*="font-size: 17px"], [style*="font-size:17px"] { line-height: 1.4 !important; }
}

/* ==============================
   MOBILE (≤ 768px)
   ============================== */
@media screen and (max-width: 768px) {
  :root, .page {
    --pad-x: 14px; --pad-y: 14px;
    --t-mega: 36px; --t-cover: 32px; --t-display: 26px;
    --t-h1: 24px; --t-h2: 20px; --t-h3: 18px;
    --t-h4: 16px; --t-h5: 14px;
    --t-body: 13px; --t-body-lg: 14.5px;
  }
  .page { padding: 14px !important; }
  .chrome, .chrome.chrome--top, .chrome.chrome--bot { font-size: 7px !important; flex-wrap: wrap; gap: 4px; padding: 8px 0; }
  .ed-mega { line-height: 1.12 !important; }
  .ed-cover { line-height: 1.12 !important; }
  .ed-display, .ed-h1, .ed-h2 { line-height: 1.15 !important; }
  .h-display { font-size: 24px !important; }
  .h-big { font-size: 22px !important; }
  .h-mid { font-size: 18px !important; }
  .recent, .updates { font-size: 36px !important; line-height: 1.0 !important; }
  .cover-quote { font-size: 26px !important; line-height: 1.15 !important; }
  .quote { font-size: 20px !important; line-height: 1.28 !important; }
  .bq-catch { font-size: 28px !important; line-height: 1.1 !important; }
  [style*="font-size: 37px"], [style*="font-size:37px"] { font-size: 20px !important; }
  [style*="font-size: 34px"], [style*="font-size:34px"] { font-size: 20px !important; }
  [style*="font-size: 22px"], [style*="font-size:22px"] { font-size: 17px !important; line-height: 1.28 !important; }
  [style*="font-size: 18px"], [style*="font-size:18px"] { font-size: 15px !important; line-height: 1.4 !important; }
  [style*="font-size: 17px"], [style*="font-size:17px"] { font-size: 14px !important; line-height: 1.45 !important; }
  .cover-top { flex-direction: column; gap: 12px; }
  .meta-stack { text-align: left !important; }
  .cover-eyebrow-row { flex-direction: column; align-items: flex-start !important; gap: 6px; }
  .cover-masthead { flex-direction: column; align-items: flex-start !important; gap: 6px; }
  .copy { padding: 14px 16px 16px !important; }
  .chips { gap: 6px !important; }
  .chip, .tag { font-size: 8px !important; }
  .client-card { padding: 10px !important; }
  .client-card img, .client-card .brand { max-width: 100% !important; height: auto !important; }
  .bq-top { flex-direction: column; gap: 10px; align-items: flex-start !important; }
  .bq-logo { height: 36px !important; }
  .bq-shot { max-height: 180px; }
  .cover-stamp, .mat-stat, .bq-stamp { padding: 10px 12px !important; }
  .closing { padding: 18px 16px !important; gap: 14px !important; }
  .pill { font-size: 8px !important; padding: 3px 8px !important; }
  .meta-row { flex-wrap: wrap; gap: 6px !important; }
  .credit { font-size: 7.5px !important; }
  .cta { font-size: 11px !important; padding: 8px 14px !important; }
  .sub { font-size: 7px !important; }
  img { max-width: 100% !important; height: auto !important; }
  .page-body, .page-body > * { max-width: 100%; }
  .bq-body { padding-left: 0 !important; }
  [style*="grid-template-columns"] { grid-template-columns: 1fr !important; }
}

/* ==============================
   SMALL MOBILE (≤ 480px)
   ============================== */
@media screen and (max-width: 480px) {
  :root, .page {
    --t-mega: 28px; --t-cover: 26px; --t-display: 22px;
    --t-h1: 20px; --t-h2: 18px; --t-h3: 16px;
  }
  .ed-mega, .ed-cover { line-height: 1.18 !important; }
  .recent, .updates { font-size: 28px !important; }
  .cover-quote { font-size: 22px !important; }
  .bq-catch { font-size: 22px !important; }
  .cover-stamp-row, .mat-stats, .bq-stamps { grid-template-columns: 1fr !important; }
  .clients-grid { grid-template-columns: 1fr 1fr !important; gap: 10px 6px !important; }
  .clients-strip-head { flex-direction: column; align-items: flex-start !important; gap: 6px; }
  .top-row, .toc-head { flex-wrap: wrap; gap: 6px; }
}
"""


# ── Main Conversion Logic ──────────────────────────────────────────

def extract_template(content):
    """Extract and unescape the template HTML from the bundler."""
    tmpl = re.search(
        r'<script type="__bundler/template">\s*"(.*?)"\s*</script>',
        content, re.DOTALL
    )
    if not tmpl:
        raise ValueError("Could not find __bundler/template in the HTML file")

    html = tmpl.group(1)
    html = html.replace('\\u002F', '/')
    html = html.replace('\\"', '"')
    html = html.replace('\\n', '\n')
    html = html.replace('\\t', '\t')
    html = html.replace('\\\\', '\\')
    return html


def extract_assets(content):
    """Extract all assets from the bundler manifest."""
    pattern = r'"([a-f0-9\-]{36})":\{"mime":"([^"]+)","compressed":(true|false),"data":"([A-Za-z0-9+/=\s]+?)"\}'
    assets = []
    for uuid, mime, compressed, b64data in re.findall(pattern, content):
        b64clean = b64data.replace("\n", "").replace("\r", "").replace(" ", "")
        assets.append({
            "uuid": uuid,
            "mime": mime,
            "data": b64clean,
        })
    return assets


def save_images(assets, output_dir):
    """Save all image assets as individual files. Returns UUID→filename mapping."""
    uuid_to_file = {}
    jpeg_count = 0
    extra_count = 0

    # First pass: find alt text from template for naming
    # (will be populated later if template is available)

    for asset in assets:
        mime = asset["mime"]
        if not mime.startswith("image/"):
            continue

        ext = EXT_MAP.get(mime, ".bin")
        raw_bytes = base64.b64decode(asset["data"])

        if mime == "image/jpeg":
            jpeg_count += 1
            fname = f"image_{jpeg_count:02d}{ext}"
        else:
            extra_count += 1
            fname = f"extra_{extra_count:02d}{ext}"

        fpath = os.path.join(output_dir, fname)
        with open(fpath, "wb") as f:
            f.write(raw_bytes)

        uuid_to_file[asset["uuid"]] = fname
        print(f"  Saved {fname} ({len(raw_bytes):,} bytes) — {mime}")

    return uuid_to_file


def improve_extra_names(uuid_to_file, html):
    """Rename extra files using alt text from the template HTML."""
    renames = {}
    for uuid, fname in uuid_to_file.items():
        if not fname.startswith("extra_"):
            continue

        # Find alt text near this UUID in the template
        alt_match = re.search(
            rf'src="{re.escape(uuid)}"[^>]*alt="([^"]+)"',
            html
        )
        if not alt_match:
            # Try escaped version
            alt_match = re.search(
                rf'src=\\"{re.escape(uuid)}\\"[^>]*alt=\\"([^"\\]+)\\"',
                html
            )

        if alt_match:
            label = alt_match.group(1).strip().replace(" ", "_").replace("/", "-")[:40]
            ext = os.path.splitext(fname)[1]
            # Extract the number part without extension (e.g., "01" from "extra_01.png")
            num = os.path.splitext(fname)[0].split("_")[1]
            new_fname = f"extra_{num}_{label}{ext}"
            renames[fname] = new_fname
        else:
            # Check if used as background
            bg_check = re.search(rf'url\([^)]*{re.escape(uuid)}', html)
            if bg_check:
                ext = os.path.splitext(fname)[1]
                num = os.path.splitext(fname)[0].split("_")[1]
                new_fname = f"extra_{num}_background{ext}"
                renames[fname] = new_fname

    return renames


def fix_encoding(html):
    """Replace Unicode special characters with HTML entities."""
    # Don't replace inside data: URIs
    parts = re.split(r'(data:[^")\s]+)', html)
    new_parts = []
    for part in parts:
        if part.startswith('data:'):
            new_parts.append(part)
        else:
            for char, entity in ENCODING_FIXES.items():
                part = part.replace(char, entity)
            new_parts.append(part)
    return ''.join(new_parts)


def fix_inline_widths(html):
    """Convert inline inch widths to responsive values."""
    html = re.sub(r'(max-width:\s*)[\d.]+in', r'\g<1>100%', html)
    html = re.sub(r'width:\s*322px', 'max-width: 322px; width: 100%', html)
    html = re.sub(r'width:\s*263px', 'max-width: 263px; width: 100%', html)
    return html


def remove_logo(html):
    """Remove the Everything Design logo from the cover."""
    html = re.sub(
        r'<div class="logo">\s*<img[^>]*alt="Everything Design"[^>]*>\s*</div>',
        '',
        html,
        flags=re.DOTALL
    )
    return html


def restructure_meta_stack(html):
    """Restructure the cover meta-stack to horizontal layout."""
    html = re.sub(
        r'<div class="meta-stack">\s*<span class="mono-label">Monthly Dispatch</span>\s*<span class="mono-label"[^>]*>([^<]*)</span>\s*</div>',
        r'<div class="meta-stack" style="text-align:left; flex-direction:row; display:flex; gap:12px; align-items:baseline;">'
        r'\n          <span class="mono-label">Monthly Dispatch</span>'
        r'\n          <span class="mono-label" style="color:var(--ink);">\1</span>'
        r'\n        </div>',
        html,
        flags=re.DOTALL
    )
    return html


def strip_to_embed(html):
    """Strip HTML/HEAD/BODY wrappers, keep only style + body content."""
    styles = re.findall(r'<style>(.*?)</style>', html, re.DOTALL)
    body_m = re.search(r'<body[^>]*>(.*)</body>', html, re.DOTALL)
    body = body_m.group(1) if body_m else html

    # Remove toolbar and scripts
    body = re.sub(r'<div class="toolbar"[^>]*>.*?</div>', '', body, flags=re.DOTALL)
    body = re.sub(r'<script>.*?</script>', '', body, flags=re.DOTALL)

    embed = "<style>\n" + "\n".join(s.strip() for s in styles) + "\n</style>\n\n" + body.strip()
    return embed


def remove_font_faces(html):
    """Remove all @font-face blocks (base64 font data)."""
    html = re.sub(r'@font-face\s*\{[^}]+\}', '', html)
    html = re.sub(r'\n{3,}', '\n\n', html)
    return html


def convert(input_path, output_dir):
    """Main conversion pipeline."""
    print(f"\n{'='*60}")
    print(f"  What's Happening → Webflow Converter")
    print(f"{'='*60}\n")

    # Read source file
    print(f"Reading: {input_path}")
    with open(input_path, "r", errors="ignore") as f:
        content = f.read()
    print(f"  Source size: {len(content):,} chars\n")

    # Extract template
    print("Step 1: Extracting template HTML...")
    html = extract_template(content)
    print(f"  Template size: {len(html):,} chars\n")

    # Extract all assets
    print("Step 2: Extracting assets from manifest...")
    assets = extract_assets(content)
    images = [a for a in assets if a["mime"].startswith("image/")]
    fonts = [a for a in assets if a["mime"].startswith("font/")]
    print(f"  Found {len(images)} images, {len(fonts)} fonts\n")

    # Save images
    print("Step 3: Saving images as individual files...")
    os.makedirs(output_dir, exist_ok=True)
    uuid_to_file = save_images(assets, output_dir)

    # Improve extra names with alt text
    renames = improve_extra_names(uuid_to_file, content)
    for old_name, new_name in renames.items():
        old_path = os.path.join(output_dir, old_name)
        new_path = os.path.join(output_dir, new_name)
        if os.path.exists(old_path):
            os.rename(old_path, new_path)
            # Update the mapping
            for uuid, fname in uuid_to_file.items():
                if fname == old_name:
                    uuid_to_file[uuid] = new_name
                    break
            print(f"  Renamed: {old_name} → {new_name}")

    print(f"  Total images saved: {len(uuid_to_file)}\n")

    # Replace image UUIDs with {{filename}} placeholders
    print("Step 4: Replacing image UUIDs with placeholders...")
    for uuid, fname in uuid_to_file.items():
        html = html.replace(uuid, "{{" + fname + "}}")

    # Replace font UUIDs with data URIs (fonts stay inline until Google Fonts replaces them)
    font_count = 0
    for asset in assets:
        if not asset["mime"].startswith("font/") and not asset["mime"].startswith("image/"):
            continue
        if asset["uuid"] not in uuid_to_file:
            # This is a font or unhandled asset — inline as data URI
            data_uri = f"data:{asset['mime']};base64,{asset['data']}"
            if html.count(asset["uuid"]) > 0:
                html = html.replace(asset["uuid"], data_uri)
                font_count += 1
    print(f"  Image placeholders: {len(uuid_to_file)}")
    print(f"  Font data URIs (temporary): {font_count}\n")

    # Strip to embed format
    print("Step 5: Stripping to Webflow embed format...")
    html = strip_to_embed(html)

    # Remove @font-face blocks
    print("Step 6: Removing base64 font data...")
    before_size = len(html)
    html = remove_font_faces(html)
    saved = before_size - len(html)
    print(f"  Removed {saved:,} chars of font data\n")

    # Fix encoding
    print("Step 7: Fixing text encoding (Unicode → HTML entities)...")
    html = fix_encoding(html)

    # Fix inline widths
    print("Step 8: Fixing inline widths...")
    html = fix_inline_widths(html)

    # Remove logo
    print("Step 9: Removing Everything Design logo from cover...")
    html = remove_logo(html)

    # Restructure meta-stack
    print("Step 10: Restructuring cover meta-stack...")
    html = restructure_meta_stack(html)

    # Prepend Google Fonts
    print("Step 11: Adding Google Fonts import link...")
    html = GOOGLE_FONTS_LINK + html

    # Append responsive CSS
    print("Step 12: Appending responsive CSS...")
    html = html.replace('</style>', RESPONSIVE_CSS + '\n</style>', 1)

    # Verify
    remaining_uuids = set(re.findall(
        r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}',
        html
    ))
    remaining_placeholders = set(re.findall(r'\{\{([^}]+)\}\}', html))

    print(f"\n{'='*60}")
    print(f"  Conversion Complete")
    print(f"{'='*60}")
    print(f"  Output size: {len(html):,} chars ({len(html)/1024:.0f} KB)")
    print(f"  Image placeholders: {len(remaining_placeholders)} (replace with CDN URLs)")
    print(f"  Bare UUIDs remaining: {len(remaining_uuids)}")
    if remaining_uuids:
        for u in remaining_uuids:
            print(f"    WARNING: {u}")
    print()

    # Write output HTML
    output_path = os.path.join(output_dir, "webflow_embed.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  HTML: {output_path}")

    # Write asset manifest
    manifest = {
        "images": [
            {"uuid": uuid, "filename": fname, "needs_cdn_url": not fname.endswith(".svg")}
            for uuid, fname in sorted(uuid_to_file.items(), key=lambda x: x[1])
        ],
        "placeholders": sorted(remaining_placeholders),
        "svg_inline": [
            fname for fname in uuid_to_file.values() if fname.endswith(".svg")
        ]
    }
    manifest_path = os.path.join(output_dir, "asset_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"  Manifest: {manifest_path}")

    # List all output files
    print(f"\n  All output files:")
    for fname in sorted(os.listdir(output_dir)):
        fpath = os.path.join(output_dir, fname)
        size = os.path.getsize(fpath)
        print(f"    {fname} ({size:,} bytes)")

    print(f"\n  Next step: Upload images to Webflow Assets,")
    print(f"  then replace {{{{filename}}}} placeholders with CDN URLs.\n")

    return output_path, uuid_to_file, remaining_placeholders


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 convert.py <input.html> [--output-dir <dir>]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_dir = "/mnt/user-data/outputs"

    if "--output-dir" in sys.argv:
        idx = sys.argv.index("--output-dir")
        output_dir = sys.argv[idx + 1]

    convert(input_path, output_dir)
