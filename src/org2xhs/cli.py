from __future__ import annotations

from pathlib import Path

import typer

from .render import RenderConfig, render_org_to_images

app = typer.Typer(add_completion=False)


@app.command()
def main(
    input_path: Path = typer.Argument(..., exists=True, dir_okay=False),  # noqa: B008
    template: str = typer.Option("clean", "--template", "-t"),  # noqa: B008
    out: Path = typer.Option(Path("dist"), "--out", "-o"),  # noqa: B008
    width: int = typer.Option(1242, "--width"),  # noqa: B008
    height: int = typer.Option(1660, "--height"),  # noqa: B008
):
    """Convert .org to Xiaohongshu-style images."""
    cfg = RenderConfig(width=width, height=height, template=template, out_dir=out)
    post_dir = render_org_to_images(input_path, cfg)
    typer.echo(str(post_dir))


if __name__ == "__main__":
    app()
