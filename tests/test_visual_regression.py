from __future__ import annotations

from pathlib import Path

from PIL import Image
from pixelmatch.contrib.PIL import pixelmatch

from org2xhs.render import RenderConfig, render_org_to_images


def _compare_images(
    baseline: Path, actual: Path, diff_out: Path, threshold: float = 0.10
) -> int:
    img1 = Image.open(baseline).convert("RGBA")
    img2 = Image.open(actual).convert("RGBA")

    if img1.size != img2.size:
        raise AssertionError(
            f"Size mismatch: {baseline.name} {img1.size} vs {actual.name} {img2.size}"
        )

    diff = Image.new("RGBA", img1.size)
    diff_pixels = pixelmatch(img1, img2, diff, threshold=threshold)
    if diff_pixels:
        diff_out.parent.mkdir(parents=True, exist_ok=True)
        diff.save(diff_out)
    return diff_pixels


def test_visual_regression_clean_sample(tmp_path: Path):
    # Generate actual images
    org = Path("tests/fixtures/sample.org")
    out = tmp_path / "dist"
    cfg = RenderConfig(
        out_dir=out, template="clean", width=1242, height=1660, max_pages=10
    )
    post_dir = render_org_to_images(org, cfg)

    baseline_dir = Path("tests/baseline/sample/clean")
    actual_pngs = sorted(post_dir.glob("*.png"))
    baseline_pngs = sorted(baseline_dir.glob("*.png"))

    assert baseline_pngs, "No baseline images found. Did you commit tests/baseline/...?"
    assert len(actual_pngs) == len(baseline_pngs), (
        f"Page count changed: {len(actual_pngs)} vs {len(baseline_pngs)}"
    )

    diff_dir = Path("test-results/visual-diff/clean")
    total_diff = 0
    for b, a in zip(baseline_pngs, actual_pngs, strict=True):
        diff_path = diff_dir / b.name
        total_diff += _compare_images(b, a, diff_path, threshold=0.10)

    assert total_diff == 0, (
        f"Visual regression detected: {total_diff} differing pixels. See diff artifacts."
    )
