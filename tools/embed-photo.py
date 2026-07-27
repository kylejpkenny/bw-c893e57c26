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
    "bowen":       ("BOWEN_FACE_SRC", 128),
    "kyle":        ("KYLE_FACE_SRC", 128),
    "intro-left":  ("INTRO_PHOTO_L_SRC", 300),
    "intro-right": ("INTRO_PHOTO_R_SRC", 300),
}


def cut_background(img, tol=26):
    """Knock out the background by flooding inwards from the border.

    A plain white-threshold would also eat teeth and eye whites, so this only
    clears pixels reachable from the edge, which leaves the subject intact.
    """
    from collections import deque
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()
    seen = bytearray(w * h)
    q = deque()

    def like_edge(p, ref):
        return abs(p[0] - ref[0]) <= tol and abs(p[1] - ref[1]) <= tol and abs(p[2] - ref[2]) <= tol

    corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    ref = max(corners, key=lambda c: c[0] + c[1] + c[2])       # the lightest corner

    for x in range(w):
        for y in (0, h - 1):
            if not seen[y * w + x] and like_edge(px[x, y], ref):
                seen[y * w + x] = 1; q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if not seen[y * w + x] and like_edge(px[x, y], ref):
                seen[y * w + x] = 1; q.append((x, y))

    while q:
        x, y = q.popleft()
        px[x, y] = (px[x, y][0], px[x, y][1], px[x, y][2], 0)
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx] and like_edge(px[nx, ny], ref):
                seen[ny * w + nx] = 1; q.append((nx, ny))
    return img


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
    ap.add_argument("--cutout", action="store_true",
                    help="knock out a plain background by flooding in from the edges")
    ap.add_argument("--tol", type=int, default=26, help="--cutout colour tolerance")
    ap.add_argument("--quality", type=int, default=82, help="JPEG quality for opaque images")
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
    if args.cutout:
        img = cut_background(img, args.tol)
    if args.circle:
        img = circle_mask(img)
    if not args.no_trim:
        bbox = img.split()[3].getbbox()
        if bbox:
            img = img.crop(bbox)

    img = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)

    # transparency needs PNG; a plain photo is far smaller as JPEG
    alpha = img.split()[3]
    transparent = alpha.getextrema()[0] < 250

    buf = io.BytesIO()
    if transparent:
        img.save(buf, "PNG", optimize=True)
        mime = "image/png"
    else:
        img.convert("RGB").save(buf, "JPEG", quality=args.quality, optimize=True, progressive=True)
        mime = "image/jpeg"
    uri = f"data:{mime};base64," + base64.b64encode(buf.getvalue()).decode()

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
