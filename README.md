# MM·Money — World Banknote Shop

Static showcase website for the MM·Money banknote shop on Delcampe and eBay.

**Live site:** https://mm-money.github.io  
**eBay:** https://www.ebay.com/str/mmmoney  
**Instagram:** [@mm.money_banknotes](https://www.instagram.com/mm.money_banknotes/)  
**Email:** info.mmmoney@gmail.com

---

## Update the collection

```bash
python3 update.py path/to/export_file_*.csv
git add -A
git commit -m "Update collection - $(date +%Y-%m-%d)"
git push
```

GitHub Pages si aggiorna in ~60 secondi.

---

## Local preview

```bash
python3 -m http.server 8000
```

Apri [localhost:8000](http://localhost:8000).

---

## File structure

```
mm site/
├── index.html          ← SPA principale
├── about.html          ← Pagina negozio (SEO)
├── robots.txt
├── sitemap.xml         ← Generato da update.py
├── update.py           ← Script aggiornamento
├── data/
│   └── collection.csv  ← Solo 5 colonne pubbliche
└── countries/
    └── *.html          ← 208 pagine statiche (generate)
```
