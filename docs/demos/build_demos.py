#!/usr/bin/env python3
"""Build the README demo GIFs from real command output.

Reads ``docs/demos/demos.json``, runs every step's command for real, rewrites
home and sandbox paths to ``~`` so no personal path ships in a GIF, and renders
an animated terminal (purple backdrop, white window bar, typed commands,
revealed output) with Pillow. ``gifsicle`` shrinks the result when installed.

Nothing in a GIF is typed by hand: what the frames show is what the command
printed on the machine that built them. The ``show`` text is the command as a
user types it (``ai-agent-seo`` stands for the installed launcher path); the
``run`` text is what actually executes.

Usage:
    python3 docs/demos/build_demos.py                 # every demo
    python3 docs/demos/build_demos.py --only seo-audit-demo.gif
    python3 docs/demos/build_demos.py --launcher /path/to/scripts/ai-agent-seo

Needs Pillow (the plugin runtime has it):
    ~/.agents/skills/seo/.venv/bin/python docs/demos/build_demos.py
Prints a JSON summary of the GIFs written.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[2]
HOME = str(Path.home())
CONFIG = Path(__file__).with_name("demos.json")
DEFAULT_LAUNCHER = Path.home() / ".agents" / "skills" / "seo" / "scripts" / "ai-agent-seo"


def load_font(candidates: list[dict], size: int) -> ImageFont.FreeTypeFont:
    for spec in candidates:
        try:
            return ImageFont.truetype(spec["path"], size, index=spec.get("index", 0))
        except OSError:
            continue
    return ImageFont.load_default(size)


def hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


class Renderer:
    def __init__(self, config: dict, demo: dict):
        self.c = config
        self.t = {k: hex_rgb(v) for k, v in config["theme"].items()}
        self.w, self.h = config["canvas"]["width"], config["canvas"]["height"]
        fonts = config["fonts"]
        self.mono = load_font(fonts["mono"], 16)
        self.title_font = load_font(fonts["title"], 30)
        self.text_font = load_font(fonts["text"], 16)
        self.chip_font = load_font(fonts["title"], 15)
        self.bar_font = load_font(fonts["text"], 14)
        self.line_h = 23
        self.char_w = self.mono.getlength("M")
        self.win = (40, 112, self.w - 40, self.h - 70)
        self.body_top = self.win[1] + 38 + 14
        self.cols = int((self.win[2] - self.win[0] - 44) / self.char_w)
        self.rows = int((self.win[3] - 14 - self.body_top) / self.line_h)
        self.rules = [(re.compile(r["pattern"]), self.t[r["color"]]) for r in config["line_colors"]]
        self.base = self._base(demo)

    def _base(self, demo: dict) -> Image.Image:
        img = Image.new("RGB", (self.w, self.h))
        draw = ImageDraw.Draw(img)
        top, bottom = self.t["background_top"], self.t["background_bottom"]
        steps = 40  # banded gradient keeps the GIF palette small and stable
        for i in range(steps):
            mix = i / (steps - 1)
            color = tuple(round(a + (b - a) * mix) for a, b in zip(top, bottom))
            y0, y1 = round(self.h * i / steps), round(self.h * (i + 1) / steps)
            draw.rectangle((0, y0, self.w, y1), fill=color)
        glow = self.t["glow"]
        for r, alpha in ((260, 0.10), (180, 0.14)):
            overlay = Image.new("RGB", img.size, glow)
            mask = Image.new("L", img.size, 0)
            ImageDraw.Draw(mask).ellipse((self.w - r - 40, -r // 2, self.w - 40 + r, r), fill=int(255 * alpha))
            img = Image.composite(overlay, img, mask)
        draw = ImageDraw.Draw(img)
        draw.text((44, 26), demo["title"], font=self.title_font, fill=self.t["title"])
        draw.text((46, 70), demo.get("subtitle", ""), font=self.text_font, fill=self.t["subtitle"])
        x0, y0, x1, y1 = self.win
        draw.rounded_rectangle((x0 - 2, y0 - 2, x1 + 2, y1 + 2), 16, fill=self.t["window_border"])
        draw.rounded_rectangle(self.win, 14, fill=self.t["window_body"])
        draw.rounded_rectangle((x0, y0, x1, y0 + 38), 14, fill=self.t["window_bar"])
        draw.rectangle((x0, y0 + 24, x1, y0 + 38), fill=self.t["window_bar"])
        for i, dot in enumerate(("#FF5F57", "#FEBC2E", "#28C840")):
            cx = x0 + 22 + i * 20
            draw.ellipse((cx - 6, y0 + 13, cx + 6, y0 + 25), fill=hex_rgb(dot))
        label = demo.get("window_title", "ai-agent-seo")
        draw.text(((x0 + x1 - self.bar_font.getlength(label)) / 2, y0 + 11), label,
                  font=self.bar_font, fill=self.t["window_bar_text"])
        cx = 44
        for chip in self.c.get("chips", []):
            width = self.chip_font.getlength(chip) + 28
            draw.rounded_rectangle((cx, self.h - 50, cx + width, self.h - 22), 14, fill=self.t["chip_bg"])
            draw.text((cx + 14, self.h - 45), chip, font=self.chip_font, fill=self.t["chip_text"])
            cx += width + 10
        footer = self.c.get("footer", "")
        draw.text((self.w - 44 - self.text_font.getlength(footer), self.h - 46), footer,
                  font=self.text_font, fill=self.t["footer"])
        return img

    def color_for(self, text: str) -> tuple[int, int, int]:
        for pattern, color in self.rules:
            if pattern.search(text):
                return color
        return self.t["output"]

    def frame(self, lines: list[tuple[str, str]], cursor: bool) -> Image.Image:
        img = self.base.copy()
        draw = ImageDraw.Draw(img)
        visible = lines[-self.rows:]
        x = self.win[0] + 22
        for row, (kind, text) in enumerate(visible):
            y = self.body_top + row * self.line_h
            if kind == "cmd":
                draw.text((x, y), "$", font=self.mono, fill=self.t["prompt"])
                draw.text((x + self.char_w * 2, y), text, font=self.mono, fill=self.t["command"])
            elif kind == "cont":
                draw.text((x + self.char_w * 2, y), text, font=self.mono, fill=self.t["command"])
            else:
                draw.text((x, y), text, font=self.mono, fill=self.color_for(text))
        if cursor:
            kind, text = visible[-1] if visible else ("cmd", "")
            offset = 2 if kind in ("cmd", "cont") else 0
            cx = x + self.char_w * (offset + len(text))
            cy = self.body_top + (len(visible) - 1) * self.line_h
            draw.rectangle((cx + 1, cy + 2, cx + self.char_w - 1, cy + self.line_h - 4), fill=self.t["prompt"])
        return img


def wrap(text: str, width: int) -> list[str]:
    """Wrap a typed command at spaces, like a terminal soft-wrap that keeps words whole."""
    parts, line = [], ""
    for word in text.split(" "):
        candidate = f"{line} {word}" if line else word
        if len(candidate) <= width:
            line = candidate
            continue
        if line:
            parts.append(line)
        while len(word) > width:
            parts.append(word[:width])
            word = word[width:]
        line = word
    parts.append(line)
    return parts


def fill_in(text: str, values: dict) -> str:
    """Replace {sandbox}, {home} and {launcher} only; jq filters keep their braces."""
    for key, value in values.items():
        text = text.replace("{" + key + "}", value)
    return text


def run_step(cmd: str, env: dict) -> str:
    proc = subprocess.run(["bash", "-c", cmd], cwd=REPO, env=env, capture_output=True,
                          text=True, timeout=300)
    return proc.stdout if proc.stdout.strip() else proc.stderr


def redact(text: str, sandbox: str) -> str:
    for path in sorted({sandbox, os.path.realpath(sandbox), HOME}, key=len, reverse=True):
        text = text.replace(path, "~")
    return text.replace(str(REPO), ".")


def build(config: dict, demo: dict, launcher: Path) -> dict:
    renderer = Renderer(config, demo)
    sandbox = tempfile.mkdtemp(prefix="ai-agent-seo-demo-")
    try:
        for folder in demo.get("sandbox_dirs", []):
            Path(sandbox, folder).mkdir(parents=True, exist_ok=True)
        fill = {"sandbox": sandbox, "home": HOME, "launcher": f'"{launcher}"'}
        env = os.environ.copy()
        env.update({k: fill_in(v, fill) for k, v in demo.get("env", {}).items()})
        frames: list[tuple[Image.Image, int]] = []
        lines: list[tuple[str, str]] = []
        step_ms = config["canvas"]["fps_ms"]

        def snap(ms: int, cursor: bool = False) -> None:
            frames.append((renderer.frame(lines, cursor), ms))

        lines.append(("cmd", ""))
        snap(700, cursor=True)
        for index, step in enumerate(demo["steps"]):
            if index:
                lines.append(("blank", ""))
                lines.append(("cmd", ""))
            shown = wrap(step["show"], renderer.cols - 2)
            for n, part in enumerate(shown):
                if n:
                    lines.append(("cont", ""))
                for end in range(0, len(part) + 1, 3):
                    lines[-1] = (lines[-1][0], part[:end])
                    snap(step_ms, cursor=True)
                lines[-1] = (lines[-1][0], part)
            snap(450, cursor=True)
            output = redact(run_step(fill_in(step["run"], fill), env), sandbox)
            out_lines = [ln.rstrip() for ln in output.splitlines()]
            for i, raw in enumerate(out_lines):
                text = raw if len(raw) <= renderer.cols else raw[: renderer.cols - 1] + "…"
                lines.append(("out", text))
                if i % 2 == 1 or i == len(out_lines) - 1:
                    snap(70)
            snap(1600)
        snap(3200)
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)

    # One shared palette from the first and last frames plus every theme colour,
    # so small accents (window dots, chips) keep their exact colour in every frame.
    swatch = Image.new("RGB", (renderer.w, 40))
    colors = list(renderer.t.values()) + [hex_rgb(c) for c in ("#FF5F57", "#FEBC2E", "#28C840")]
    sd = ImageDraw.Draw(swatch)
    for i, color in enumerate(colors):
        sd.rectangle((i * 30, 0, i * 30 + 29, 39), fill=color)
    sheet = Image.new("RGB", (renderer.w, renderer.h * 2 + 40))
    sheet.paste(frames[0][0], (0, 0))
    sheet.paste(frames[-1][0], (0, renderer.h))
    sheet.paste(swatch, (0, renderer.h * 2))
    palette_src = sheet.quantize(colors=160, method=Image.Quantize.MEDIANCUT)
    images = [img.quantize(palette=palette_src, dither=Image.Dither.NONE) for img, _ in frames]
    durations = [ms for _, ms in frames]
    out = REPO / demo["output"]
    out.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(out, save_all=True, append_images=images[1:], duration=durations, loop=0, disposal=1)
    if shutil.which("gifsicle"):
        subprocess.run(["gifsicle", "-O3", "--batch", str(out)], check=False)
    return {"gif": demo["output"], "frames": len(images), "seconds": round(sum(durations) / 1000, 1),
            "bytes": out.stat().st_size}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build README demo GIFs from real command output.")
    parser.add_argument("--only", help="build one GIF by its file name")
    parser.add_argument("--launcher", default=str(DEFAULT_LAUNCHER), help="installed ai-agent-seo launcher")
    args = parser.parse_args(argv)
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    demos = [d for d in config["demos"] if not args.only or Path(d["output"]).name == args.only]
    if not demos:
        print(json.dumps({"error": f"no demo named {args.only}"}))
        return 2
    results = [build(config, demo, Path(args.launcher)) for demo in demos]
    print(json.dumps({"built": results}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
