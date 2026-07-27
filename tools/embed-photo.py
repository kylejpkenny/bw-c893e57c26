#!/usr/bin/env python3
"""
Embed a photo into index.html as a base64 data URI.

The game is deliberately one self-contained file, so photos live inside it
rather than beside it. Each photo has a named slot:

    bowen   the head on the running character
    kyle    the head on the dinosaurs
    intro   the family photo the game opens on

Usage
-----
    python3 tools/embed-photo.py bowen path/to/photo.png
    python3 tools/embed-photo.py kyle  path/to/kyle.jpg  --circle
    python3 tools/embed-photo.py intro path/to/family.jpg --crop 0,60,988,1180

Options
-------
    --crop L,T,R,B   crop box in source pixels, applied before anything else
    --width N        output width in px (default: 128 for heads, 420 for intro)
    --circle         cut to a circle (for headshots on a plain background)
    --no-trim        keep transparent borders instead of trimming them

Re-running a slot replaces whatever was there before, so it is safe to iterate.
"""
import argparse
import base64
import io
import pathlib
import re
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required:  python3 -m pip install pillow")

ROOT = pathlib.Path(__file__).resolve().parent.parent
HTML = ROOT / "index.html"

SLOTS = {
    "bowen": ("BOWEN_FACE_SRC", 128),
    "kyle":  ("KYLE_FACE_SRC", 128),
    "intro": ("INTRO_PHOTO_SRC", 420),
}


def circle_mask(img):
    """Feathered circular cut-out, sized to the shorter side."""
    from PIL import ImageDraw, ImageFilter
    w, h = img.size
    d = min(w, h)
    ss = 4                                    # supersample for a smooth edge
    mask = Image.new("L", (d * ss, d * ss), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, d * ss - 1, d * ss - 1), fill=255)
    mask = mask.resize((d, d), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.6))
    out = Image.new("RGBA", (d, d), (0, 0, 0, 0))
    out.paste(img.crop(((w - d) // 2, (h - d) // 2, (w - d) // 2 + d, (h - d) // 2 + d)),
              (0, 0), mask)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slot", choices=sorted(SLOTS))
    ap.add_argument("image")
    ap.add_argument("--crop", help="L,T,R,B in source pixels")
    ap.add_argument("--width", type=int)
    ap.add_argument("--circle", action="store_true")
    ap.add_argument("--no-trim", action="store_true")
    args = ap.parse_args()

    var, default_w = SLOTS[args.slot]
    width = args.width or default_w

    img = Image.open(args.image).convert("RGBA")
    if args.crop:
        box = tuple(int(v) for v in args.crop.split(","))
        if len(box) != 4:
            sys.exit("--crop needs exactly four numbers: L,T,R,B")
        img = img.crop(box)
    if args.circle:
        img = circle_mask(img)
    if not args.no_trim:
        bbox = img.split()[3].getbbox()
        if bbox:
            img = img.crop(bbox)

    img = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    uri = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

    html = HTML.read_text()
    pattern = re.compile(r'(const\s+' + var + r'\s*=\s*)"[^"]*"')
    if not pattern.search(html):
        sys.exit(f"could not find {var} in index.html")
    html = pattern.sub(lambda m: m.group(1) + '"' + uri + '"', html, count=1)
    HTML.write_text(html)

    print(f"{args.slot}: {img.size[0]}x{img.size[1]}, "
          f"{len(buf.getvalue()):,} bytes -> index.html now {HTML.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
