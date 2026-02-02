from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image

TITLE_RE = re.compile(r"^#\+TITLE:\s*(.+)\s*$", re.IGNORECASE | re.MULTILINE)


@dataclass(frozen=True)
class RenderConfig:
    width: int = 1242
    height: int = 1660
    template: str = "clean"
    out_dir: Path = Path("dist")
    max_pages: int = 30  # safety guard


def _ensure_pandoc() -> None:
    if shutil.which("pandoc") is None:
        raise RuntimeError("pandoc not found on PATH. Please install pandoc first.")


def _extract_title(org_text: str, fallback: str) -> str:
    m = TITLE_RE.search(org_text)
    return m.group(1).strip() if m else fallback


def org_to_html_fragment(org_path: Path) -> tuple[str, str]:
    """Convert org to HTML fragment via pandoc. Returns (title, html_fragment)."""
    _ensure_pandoc()
    org_text = org_path.read_text(encoding="utf-8")
    title = _extract_title(org_text, fallback=org_path.stem)

    res = subprocess.run(
        ["pandoc", str(org_path), "--from=org", "--to=html5"],
        check=True,
        capture_output=True,
        text=True,
    )
    return title, res.stdout


def make_caption(title: str, html_fragment: str, max_len: int = 200) -> str:
    text = re.sub(r"<[^>]+>", " ", html_fragment)
    text = re.sub(r"\s+", " ", text).strip()
    snippet = text[:max_len].rstrip()
    return f"{title}\n\n{snippet}"


def render_html(title: str, html_fragment: str, cfg: RenderConfig) -> str:
    templates_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    tpl = env.get_template(f"{cfg.template}.html.j2")
    return tpl.render(
        title=title, content_html=html_fragment, width=cfg.width, height=cfg.height
    )


async def _screenshot_pages(html_path: Path, out_dir: Path, cfg: RenderConfig) -> int:
    from playwright.async_api import async_playwright

    out_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            viewport={"width": cfg.width, "height": cfg.height},
            device_scale_factor=2,
        )
        await page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
        await page.add_style_tag(
            content="* { animation: none !important; transition: none !important; }"
        )

        await page.evaluate("""() => {
            if (window.__ORG2XHS_PAGINATED__) return;
            window.__ORG2XHS_PAGINATED__ = true;

            const content = document.querySelector('#content');
            const pagesRoot = document.querySelector('#pages');
            const pageW = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--page-width'));
            const pageH = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--page-height'));
            const padTop = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--page-pad-top'));
            const padBottom = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--page-pad-bottom'));
            const contentH = pageH - padTop - padBottom;

            function makePage() {
              const page = document.createElement('div');
              page.className = 'page';
              page.style.width = pageW + 'px';
              page.style.height = pageH + 'px';
              const inner = document.createElement('div');
              inner.className = 'page-inner';
              page.appendChild(inner);
              pagesRoot.appendChild(page);
              return inner;
            }

            const staging = document.createElement('div');
            staging.innerHTML = content.innerHTML;
            content.innerHTML = '';

            const nodes = Array.from(staging.childNodes).filter(n => !(n.nodeType === Node.TEXT_NODE && !n.textContent.trim()));

            let inner = makePage();
            const titleText = document.querySelector('#doc-title')?.textContent?.trim();
            if (titleText) {
              const h1 = document.createElement('h1');
              h1.className = 'doc-title';
              h1.textContent = titleText;
              inner.appendChild(h1);
            }

            for (const node of nodes) {
              inner.appendChild(node);
              if (inner.scrollHeight > contentH) {
                inner.removeChild(node);
                inner = makePage();
                inner.appendChild(node);
              }
            }

            const pages = Array.from(document.querySelectorAll('.page'));
            pages.forEach((pg, idx) => {
              const footer = document.createElement('div');
              footer.className = 'page-footer';
              footer.textContent = String(idx + 1);
              pg.appendChild(footer);
            });
        }""")

        pages = page.locator(".page")
        count = await pages.count()
        if count == 0:
            raise RuntimeError(
                "pagination produced 0 pages; check template and input content."
            )
        count = min(count, cfg.max_pages)

        for i in range(count):
            out_path = out_dir / f"{i + 1:03d}.png"
            await pages.nth(i).screenshot(path=str(out_path), type="png")

            # Downscale to the target size (keep output exactly width×height)
            from PIL import Image

            im = Image.open(out_path)
            if im.size != (cfg.width, cfg.height):
                im = im.resize(
                    (cfg.width, cfg.height), resample=Image.Resampling.LANCZOS
                )
                im.save(out_path)

        await browser.close()
        return count


def _verify_images(out_dir: Path, cfg: RenderConfig) -> None:
    for p in sorted(out_dir.glob("*.png")):
        im = Image.open(p)
        if im.size != (cfg.width, cfg.height):
            raise RuntimeError(
                f"Image {p.name} has size {im.size}, expected {(cfg.width, cfg.height)}"
            )


def render_org_to_images(org_path: Path, cfg: RenderConfig) -> Path:
    title, frag = org_to_html_fragment(org_path)
    html = render_html(title, frag, cfg)

    post_id = org_path.stem
    post_dir = (cfg.out_dir / post_id).resolve()
    post_dir.mkdir(parents=True, exist_ok=True)

    html_path = post_dir / "render.html"
    html_path.write_text(html, encoding="utf-8")

    (post_dir / "caption.txt").write_text(make_caption(title, frag), encoding="utf-8")

    import asyncio

    pages = asyncio.run(_screenshot_pages(html_path, post_dir, cfg))
    _verify_images(post_dir, cfg)

    meta = {
        "title": title,
        "pages": pages,
        "width": cfg.width,
        "height": cfg.height,
        "template": cfg.template,
    }
    (post_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return post_dir
