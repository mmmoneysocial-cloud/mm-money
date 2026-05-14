#!/usr/bin/env python3
"""
MM·Money update script.
Usage: python3 update.py path/to/export.csv

Writes a public-only CSV (5 columns), generates all country pages,
regenerates sitemap.xml, and patches the item count in index.html.
"""

import csv
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

BASE_URL = "https://mmmoneybanknotes.com"
SCRIPT_DIR = Path(__file__).parent

REQUIRED_COLUMNS = {"id_auction", "title", "present_price", "visits_number", "end_date"}
PUBLIC_COLUMNS   = ["id_auction", "title", "present_price", "visits_number", "end_date"]

MULTI_WORD_COUNTRIES = [
    "SOUTH AFRICA", "WEST GERMANY", "HONG KONG", "EAST GERMANY",
    "PAPUA NEW GUINEA", "CENTRAL AFRICA", "NEW ZEALAND", "SIERRA LEONE",
    "SAUDI ARABIA", "EQUATORIAL GUINEA", "DOMINICAN REPUBLIC",
    "NORTH KOREA", "SOUTH KOREA", "COSTA RICA", "PUERTO RICO",
    "TRINIDAD TOBAGO", "IVORY COAST", "BURKINA FASO", "CAPE VERDE",
    "SRI LANKA", "EL SALVADOR", "CZECH REPUBLIC",
    "GERMAN DEMOCRATIC REPUBLIC", "NETHERLANDS ANTILLES", "WESTERN SAMOA",
]


# ── helpers ───────────────────────────────────────────────────────────────────

def id_to_img(id_str):
    p = str(id_str).zfill(12)
    return (
        f"https://www.delcampe.net/static/img_large/auction"
        f"/{p[0:3]}/{p[3:6]}/{p[6:9]}/{p[9:12]}_001.jpg"
    )


def id_to_url(id_str, title):
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:80]
    return (
        f"https://www.delcampe.net/it/collezionismo/monete-banconote"
        f"/banconote/{slug}-{id_str}.html"
    )


def country_slug(country_name):
    return re.sub(r"[^a-z0-9]+", "-", country_name.lower()).strip("-")


def extract_country(title):
    t = title.upper().strip()
    for mw in MULTI_WORD_COUNTRIES:
        if t.startswith(mw):
            return mw.title()
    words = t.split()
    return words[0].title() if words else "Unknown"


def detect_badges(title):
    badges = []
    if re.search(r"\*?rare\*?|\*?scarce", title, re.I):
        badges.append("Rare")
    if re.search(r"specimen", title, re.I):
        badges.append("Specimen")
    if re.search(r"overprint", title, re.I):
        badges.append("Overprint")
    if re.search(r"error", title, re.I):
        badges.append("Error")
    return badges


def format_price(price_str):
    try:
        val = float(price_str)
        return f"{val:.2f}"
    except (ValueError, TypeError):
        return price_str


def parse_end_date(end_date_str):
    try:
        return datetime.strptime(end_date_str.strip(), "%Y-%m-%d %H:%M:%S").date()
    except (ValueError, AttributeError):
        return None


def is_urgent(end_date):
    if end_date is None:
        return False
    delta = end_date - date.today()
    return 0 <= delta.days <= 1


def format_date_display(end_date):
    if end_date is None:
        return ""
    return end_date.strftime("%-d %b %Y")


def html_escape(s):
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ── CSV loading ───────────────────────────────────────────────────────────────

def load_csv(path):
    items = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            print(f"ERROR: CSV is missing required columns: {missing}", file=sys.stderr)
            sys.exit(1)
        for row in reader:
            id_str = row["id_auction"].strip()
            title  = row["title"].strip()
            if not id_str or not title:
                continue
            end_date = parse_end_date(row.get("end_date", ""))
            items.append({
                "id":           id_str,
                "title":        title,
                "price":        format_price(row.get("present_price", "")),
                "views":        str(int(row.get("visits_number", "0").strip() or "0")),
                "end_date":     end_date,
                "img_url":      id_to_img(id_str),
                "listing_url":  id_to_url(id_str, title),
                "country":      extract_country(title),
                "badges":       detect_badges(title),
                "urgent":       is_urgent(end_date),
                "date_display": format_date_display(end_date),
            })
    return items


def write_public_csv(src_path, dest_path):
    """Write only the 5 public columns — strips all private fields."""
    with open(src_path, newline="", encoding="utf-8-sig") as src, \
         open(dest_path, "w", newline="", encoding="utf-8") as dst:
        reader = csv.DictReader(src)
        writer = csv.DictWriter(dst, fieldnames=PUBLIC_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(reader)


# ── static card HTML (country pages) ─────────────────────────────────────────

BADGE_COLORS = {
    "Rare":      "#a04838",
    "Specimen":  "#3a6ea8",
    "Overprint": "#5a7a3a",
    "Error":     "#7a3a8a",
}


def static_card_html(item):
    badges_html = ""
    for badge in item["badges"][:1]:
        color = BADGE_COLORS.get(badge, "#555")
        badges_html = (
            f'<span class="badge" style="background:{color}">'
            f'{html_escape(badge)}</span>'
        )

    date_style = ' style="color:#a04838"' if item["urgent"] else ""
    date_part  = (
        f'<span{date_style}>⧖ {html_escape(item["date_display"])}</span>'
        if item["date_display"] else ""
    )

    return f"""<div class="card">
  <a href="{html_escape(item["listing_url"])}" target="_blank" rel="noopener">
    <div class="card-img-wrap">
      {badges_html}
      <img src="{html_escape(item["img_url"])}"
           alt="{html_escape(item["title"])}"
           loading="lazy"
           onerror="this.parentNode.innerHTML='<div class=\\'img-placeholder\\'>◈</div>'"
      >
    </div>
    <div class="card-body">
      <p class="card-title">{html_escape(item["title"])}</p>
      <p class="card-price">€ {html_escape(item["price"])}</p>
      <p class="card-meta">◉ {html_escape(item["views"])} views &nbsp; {date_part}</p>
    </div>
    <div class="card-cta">View on Delcampe →</div>
  </a>
</div>"""


# ── country page generation ───────────────────────────────────────────────────

COUNTRY_PAGE_CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300&family=Outfit:wght@300;400;500&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0a0906;color:#e8e0d0;font-family:'Outfit',sans-serif;line-height:1.5}
a{color:inherit;text-decoration:none}
nav{background:#110f0c;border-bottom:1px solid #1e1b16;padding:.8rem 1.5rem;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:10}
.logo{font-family:'Cormorant Garamond',serif;font-size:1.3rem;color:#c8a45a;letter-spacing:.05em}
.back-link{color:#c8a45a;font-size:.85rem}
h1{font-family:'Cormorant Garamond',serif;font-weight:300;font-size:2.2rem;margin:2rem 1.5rem .5rem;color:#c8a45a}
.intro{margin:0 1.5rem 2rem;color:#7a6e5e;font-size:.9rem;max-width:600px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:1px;background:#1e1b16;margin:0 1rem}
.card{background:#110f0c;display:flex;flex-direction:column}
.card a{display:flex;flex-direction:column;height:100%}
.card-img-wrap{position:relative;aspect-ratio:8/5;overflow:hidden;background:#1a1712}
.card-img-wrap img{width:100%;height:100%;object-fit:contain;transition:transform .3s}
.card:hover .card-img-wrap img{transform:scale(1.04)}
.img-placeholder{width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-size:2rem;color:#7a6030;background:#1a1712}
.badge{position:absolute;top:6px;left:6px;font-size:.65rem;font-weight:500;padding:2px 6px;color:#fff;font-family:'Outfit',sans-serif;letter-spacing:.04em}
.card-body{padding:.6rem .7rem;flex:1}
.card-title{font-family:'Cormorant Garamond',serif;font-size:.9rem;line-height:1.3;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;margin-bottom:.4rem}
.card-price{color:#c8a45a;font-size:1.1rem;font-weight:500;margin-bottom:.3rem}
.card-meta{font-size:.72rem;color:#7a6e5e}
.card-cta{padding:.5rem .7rem;font-size:.78rem;color:#7a6030;border-top:1px solid #1e1b16;transition:background .2s,color .2s}
.card:hover .card-cta{background:#1a1712;color:#c8a45a}
.view-all{display:block;text-align:center;margin:2.5rem auto;padding:.7rem 2rem;border:1px solid #7a6030;color:#c8a45a;font-size:.9rem;max-width:300px;transition:background .2s}
.view-all:hover{background:#1a1712}
footer{text-align:center;padding:2rem;color:#7a6e5e;font-size:.8rem;border-top:1px solid #1e1b16;margin-top:3rem}
</style>
"""


def generate_country_page(country_name, items, countries_dir):
    slug  = country_slug(country_name)
    count = len(items)
    page_url      = f"{BASE_URL}/countries/{slug}.html"
    display_items = items[:12]

    ld_products = []
    for item in items[:20]:
        ld_products.append({
            "@type": "Product",
            "name": item["title"],
            "offers": {
                "@type": "Offer",
                "price": item["price"],
                "priceCurrency": "EUR",
                "availability": "https://schema.org/InStock",
                "url": item["listing_url"],
            },
        })

    ld = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": f"{country_name} Banknotes — MM·Money",
        "url": page_url,
        "numberOfItems": count,
        "hasPart": ld_products,
    }

    cards_html   = "\n".join(static_card_html(it) for it in display_items)
    view_all_url = f"../index.html#country={slug}"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html_escape(country_name)} Banknotes for Sale · MM·Money Shop</title>
<meta name="description" content="Browse {count} {html_escape(country_name)} banknotes from MM·Money. Historic series, UNC and VF grades. Buy on Delcampe or eBay.">
<link rel="canonical" href="{html_escape(page_url)}">
<meta property="og:title" content="{html_escape(country_name)} Banknotes — MM·Money">
<meta property="og:description" content="{count} {html_escape(country_name)} banknotes for sale.">
<meta property="og:url" content="{html_escape(page_url)}">
{COUNTRY_PAGE_CSS}
<script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False, indent=2)}
</script>
</head>
<body>
<nav>
  <span class="logo">MM·MONEY</span>
  <a class="back-link" href="../index.html">← Back to full catalogue</a>
</nav>
<h1>{html_escape(country_name)} Banknotes</h1>
<p class="intro">{count} item{"s" if count != 1 else ""} available from the MM·Money shop on Delcampe and eBay.</p>
<div class="grid">
{cards_html}
</div>
{"" if count <= 12 else f'<a class="view-all" href="{html_escape(view_all_url)}">View all {count} {html_escape(country_name)} banknotes →</a>'}
<footer>MM·Money &mdash; <a href="https://www.instagram.com/mm.money_banknotes/" target="_blank" rel="noopener">@mm.money_banknotes</a> &mdash; <a href="mailto:info.mmmoney@gmail.com">info.mmmoney@gmail.com</a></footer>
</body>
</html>"""

    out_path = countries_dir / f"{slug}.html"
    out_path.write_text(html, encoding="utf-8")
    return slug


# ── sitemap ───────────────────────────────────────────────────────────────────

def generate_sitemap(country_slugs, output_path):
    today = date.today().isoformat()
    urls  = [
        f"  <url><loc>{BASE_URL}/</loc><lastmod>{today}</lastmod><priority>1.0</priority></url>",
        f"  <url><loc>{BASE_URL}/about.html</loc><lastmod>{today}</lastmod><priority>0.8</priority></url>",
    ]
    for slug in sorted(country_slugs):
        urls.append(
            f"  <url><loc>{BASE_URL}/countries/{slug}.html</loc>"
            f"<lastmod>{today}</lastmod><priority>0.7</priority></url>"
        )
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )
    output_path.write_text(sitemap, encoding="utf-8")


# ── patch index.html ──────────────────────────────────────────────────────────

def patch_index_html(index_path, count):
    if not index_path.exists():
        return
    text = index_path.read_text(encoding="utf-8")
    if "<!-- ITEM_COUNT -->" not in text:
        print("WARNING: <!-- ITEM_COUNT --> marker not found in index.html", file=sys.stderr)
    patched = re.sub(r"<!-- ITEM_COUNT -->[\d,]*", f"<!-- ITEM_COUNT -->{count:,}", text)
    patched = re.sub(r'"numberOfItems":\s*\d+', f'"numberOfItems": {count}', patched)
    index_path.write_text(patched, encoding="utf-8")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 update.py path/to/export.csv", file=sys.stderr)
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        print(f"ERROR: File not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    data_dir     = SCRIPT_DIR / "data"
    countries_dir = SCRIPT_DIR / "countries"
    data_dir.mkdir(exist_ok=True)
    countries_dir.mkdir(exist_ok=True)

    print(f"Loading {csv_path.name} …")
    items = load_csv(csv_path)
    print(f"  {len(items):,} items loaded")

    dest_csv = data_dir / "collection.csv"
    if csv_path.resolve() == dest_csv.resolve():
        print(f"  Using {dest_csv} (already in place — already stripped)")
    else:
        write_public_csv(csv_path, dest_csv)
        print(f"  Written (public columns only) → {dest_csv}")

    country_map: dict[str, list] = {}
    for item in items:
        country_map.setdefault(item["country"], []).append(item)

    print(f"\nGenerating {len(country_map)} country pages …")
    existing_pages = {p.stem for p in countries_dir.glob("*.html")}
    slugs = []
    for country_name, country_items in sorted(country_map.items()):
        slug = generate_country_page(country_name, country_items, countries_dir)
        slugs.append(slug)

    for stale in existing_pages - set(slugs):
        (countries_dir / f"{stale}.html").unlink(missing_ok=True)
        print(f"  Removed stale: {stale}.html")

    print("\nGenerating sitemap.xml …")
    generate_sitemap(slugs, SCRIPT_DIR / "sitemap.xml")

    print("Patching index.html item count …")
    patch_index_html(SCRIPT_DIR / "index.html", len(items))

    print(f"\n✓ {len(items):,} items · {len(country_map)} countries · {len(slugs)} pages generated")


if __name__ == "__main__":
    main()
