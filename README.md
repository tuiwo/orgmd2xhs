# org2xhs (starter)

Convert `.org` documents into elegant Xiaohongshu-style images (default **1242×1660**, 3:4).

## What you get (v0)
- Mode: **original** (no cover page; starts with the article page)
- Template: `clean`
- Output:
  - `dist/<post_id>/001.png ...`
  - `dist/<post_id>/caption.txt`

## Quickstart

### 1) Install
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip
pip install -e .
```

### 2) Install browser for rendering
```bash
playwright install chromium
```

### 3) Run
```bash
org2xhs tests/fixtures/sample.org --template clean --out dist
```

## Notes
- `pandoc` must be installed and available on PATH.
- Rendering uses Playwright (Chromium) and DOM-based pagination before screenshots.

## License
MIT
