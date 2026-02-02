from __future__ import annotations

from pathlib import Path
from PIL import Image

from org2xhs.render import RenderConfig, render_org_to_images

def test_smoke_render(tmp_path: Path):
    org = Path("tests/fixtures/sample.org")
    out = tmp_path / "dist"
    cfg = RenderConfig(out_dir=out, template="clean", width=1242, height=1660, max_pages=10)
    post_dir = render_org_to_images(org, cfg)

    assert (post_dir / "caption.txt").exists()
    assert (post_dir / "render.html").exists()

    pngs = sorted(post_dir.glob("*.png"))
    assert len(pngs) >= 1

    im = Image.open(pngs[0])
    assert im.size == (1242, 1660)
