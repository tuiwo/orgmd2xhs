from __future__ import annotations

from pathlib import Path
import typer

from .render import RenderConfig, render_org_to_images

app = typer.Typer(add_completion=False)

@app.command()
def main(
    input_path: Path = typer.Argument(..., exists=True, dir_okay=False),
    template: str = typer.Option("clean", "--template", "-t"),
    out: Path = typer.Option(Path("dist"), "--out", "-o"),
    width: int = typer.Option(1242, "--width"),
    height: int = typer.Option(1660, "--height"),
):
    """Convert .org to Xiaohongshu-style images."""
    cfg = RenderConfig(width=width, height=height, template=template, out_dir=out)
    post_dir = render_org_to_images(input_path, cfg)
    typer.echo(str(post_dir))

if __name__ == "__main__":
    app()
