#!/usr/bin/env python3
"""Generate the gta6-meme-x-01 meme: a Vice City sunset scene with the
make.fun ghost mascot, drawn entirely with the Python standard library.

Usage:  python3 meme.py <ghost-png> <output-png>

The ghost is make.fun's own press-kit mark (https://make.fun/press/,
mark-1024.png): a white ghost with a black outline, sparkle eyes and a
magenta star coin. It is decoded, scaled and alpha-composited into a
sunset scene drawn pixel by pixel in this script. No third-party
packages are used: PNG encode/decode is done with zlib + struct.
"""

import struct
import sys
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- PNG codec

def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def save_png(path, w, h, rgba):
    """rgba: bytearray of w*h*4 bytes, 8-bit RGBA. Writes a PNG, filter 0."""
    raw = bytearray()
    stride = w * 4
    for y in range(h):
        raw.append(0)
        raw += rgba[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def load_png(path):
    """Decode a non-interlaced 8-bit RGBA/RGB PNG. Returns (w, h, bytearray)."""
    data = open(path, "rb").read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    pos = 8
    idat = bytearray()
    w = h = None
    ctype = None
    while pos < len(data):
        ln, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + ln]
        if kind == b"IHDR":
            w, h, depth, ctype, _, _, inter = struct.unpack(">IIBBBBB", body)
            assert depth == 8 and inter == 0, "unsupported PNG flavour"
            assert ctype in (2, 6), "need RGB or RGBA PNG"
        elif kind == b"IDAT":
            idat += body
        elif kind == b"IEND":
            break
        pos += 12 + ln
    bpp = 4 if ctype == 6 else 3
    raw = zlib.decompress(bytes(idat))
    stride = w * bpp
    out = bytearray(w * h * 4)
    prev = bytearray(stride)
    for y in range(h):
        f = raw[y * (stride + 1)]
        row = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            a = row[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if f == 1:
                row[i] = (row[i] + a) & 0xFF
            elif f == 2:
                row[i] = (row[i] + b) & 0xFF
            elif f == 3:
                row[i] = (row[i] + (a + b) // 2) & 0xFF
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                row[i] = (row[i] + pr) & 0xFF
        prev = row
        for x in range(w):
            o = (y * w + x) * 4
            s = x * bpp
            out[o] = row[s]
            out[o + 1] = row[s + 1]
            out[o + 2] = row[s + 2]
            out[o + 3] = row[s + 3] if bpp == 4 else 255
    return w, h, out


# ---------------------------------------------------------------- canvas

def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    return tuple(int(round(lerp(a, b, t))) for a, b in zip(c1, c2))


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = bytearray(w * h * 4)

    def set(self, x, y, color, alpha=255):
        if 0 <= x < self.w and 0 <= y < self.h:
            o = (y * self.w + x) * 4
            if alpha >= 255:
                self.px[o:o + 4] = bytes((*color, 255))
            else:
                inv = 255 - alpha
                for i in range(3):
                    self.px[o + i] = (color[i] * alpha + self.px[o + i] * inv) // 255
                self.px[o + 3] = 255

    def fill_rect(self, x0, y0, x1, y1, color, alpha=255):
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.w, x1)
        y1 = min(self.h, y1)
        for y in range(y0, y1):
            o = (y * self.w + x0) * 4
            if alpha >= 255:
                self.px[o:o + (x1 - x0) * 4] = bytes((*color, 255)) * (x1 - x0)
            else:
                inv = 255 - alpha
                for x in range(x0, x1):
                    oo = (y * self.w + x) * 4
                    for i in range(3):
                        self.px[oo + i] = (color[i] * alpha + self.px[oo + i] * inv) // 255

    def disc(self, cx, cy, r, color, alpha=255):
        r2 = r * r
        for y in range(max(0, cy - r), min(self.h, cy + r + 1)):
            dy = y - cy
            dx = int((r2 - dy * dy) ** 0.5)
            self.fill_rect(cx - dx, y, cx + dx + 1, y + 1, color, alpha)

    def ring(self, cx, cy, r0, r1, color, alpha=255):
        for y in range(max(0, cy - r1), min(self.h, cy + r1 + 1)):
            dy = y - cy
            for r, lo in ((r1, r0),):
                dx = int((r * r - dy * dy) ** 0.5) if abs(dy) < r else -1
                if dx < 0:
                    continue
                dx0 = int((lo * lo - dy * dy) ** 0.5) if abs(dy) < lo else -1
                if dx0 < 0:
                    self.fill_rect(cx - dx, y, cx + dx + 1, y + 1, color, alpha)
                else:
                    self.fill_rect(cx - dx, y, cx - dx0, y + 1, color, alpha)
                    self.fill_rect(cx + dx0 + 1, y, cx + dx + 1, y + 1, color, alpha)

    def thick_line(self, x0, y0, x1, y1, width, color, alpha=255):
        steps = max(abs(x1 - x0), abs(y1 - y0), 1) * 2
        r = width // 2
        for i in range(steps + 1):
            t = i / steps
            x = int(round(lerp(x0, x1, t)))
            y = int(round(lerp(y0, y1, t)))
            self.disc(x, y, r, color, alpha)

    def blit(self, src_w, src_h, src, dx, dy, dw, dh):
        """Bilinear scale + alpha composite of an RGBA image onto the canvas."""
        for y in range(dh):
            sy = (y + 0.5) * src_h / dh - 0.5
            y0 = int(sy)
            fy = sy - y0
            if y0 < 0:
                y0, fy = 0, 0.0
            if y0 >= src_h - 1:
                y0, fy = src_h - 2, 1.0
            ty = dy + y
            if not (0 <= ty < self.h):
                continue
            for x in range(dw):
                sx = (x + 0.5) * src_w / dw - 0.5
                x0 = int(sx)
                fx = sx - x0
                if x0 < 0:
                    x0, fx = 0, 0.0
                if x0 >= src_w - 1:
                    x0, fx = src_w - 2, 1.0
                tx = dx + x
                if not (0 <= tx < self.w):
                    continue
                acc = [0.0, 0.0, 0.0, 0.0]
                for wy, yy in ((1 - fy, y0), (fy, y0 + 1)):
                    for wx, xx in ((1 - fx, x0), (fx, x0 + 1)):
                        o = (yy * src_w + xx) * 4
                        wgt = wx * wy
                        for i in range(4):
                            acc[i] += src[o + i] * wgt
                a = acc[3] / 255.0
                if a <= 0:
                    continue
                o = (ty * self.w + tx) * 4
                for i in range(3):
                    self.px[o + i] = int(round(acc[i] * a + self.px[o + i] * (1 - a)))
                self.px[o + 3] = 255


# ---------------------------------------------------------------- 5x7 font

# Each glyph: 7 rows, 5 bits each (MSB = leftmost pixel).
FONT = {
    "A": (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "B": (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    "C": (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    "D": (0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E),
    "E": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    "F": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    "G": (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
    "H": (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "I": (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "J": (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
    "K": (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    "L": (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    "M": (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    "N": (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    "O": (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "P": (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    "Q": (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    "R": (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    "S": (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    "T": (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    "U": (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "V": (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    "W": (0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11),
    "X": (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    "Y": (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    "Z": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    "0": (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    "1": (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "2": (0x0E, 0x11, 0x01, 0x06, 0x08, 0x10, 0x1F),
    "3": (0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E),
    "4": (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    "5": (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    "6": (0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    "7": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    "8": (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    "9": (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C),
    " ": (0, 0, 0, 0, 0, 0, 0),
    ".": (0, 0, 0, 0, 0, 0x0C, 0x0C),
    ",": (0, 0, 0, 0, 0x0C, 0x04, 0x08),
    "!": (0x04, 0x04, 0x04, 0x04, 0x04, 0, 0x04),
    "?": (0x0E, 0x11, 0x01, 0x02, 0x04, 0, 0x04),
    "-": (0, 0, 0, 0x0E, 0, 0, 0),
    ":": (0, 0, 0x04, 0, 0, 0x04, 0),
    "/": (0x01, 0x01, 0x02, 0x04, 0x08, 0x10, 0x10),
    "'": (0x04, 0x04, 0x08, 0, 0, 0, 0),
}


def text_width(text, scale):
    return len(text) * 6 * scale - scale


def draw_text_raw(cv, text, x, y, scale, color):
    """Draw text once, bold (each glyph stamped twice, offset right)."""
    bold = max(1, scale // 4)
    for ch in text:
        glyph = FONT.get(ch)
        if glyph is None:
            raise ValueError(f"no glyph for {ch!r}")
        for ox in (0, bold):
            for row, bits in enumerate(glyph):
                for col in range(5):
                    if bits & (1 << (4 - col)):
                        cv.fill_rect(x + ox + col * scale, y + row * scale,
                                     x + ox + (col + 1) * scale, y + (row + 1) * scale,
                                     color)
        x += 6 * scale


def draw_text(cv, text, cx, y, scale, fill, outline=(10, 6, 20)):
    """Centred outlined text: black outline pass, then fill pass."""
    w = text_width(text, scale)
    x = cx - w // 2
    o = max(2, scale // 3)
    for dx, dy in ((-o, 0), (o, 0), (0, -o), (0, o),
                   (-o, -o), (o, -o), (-o, o), (o, o)):
        draw_text_raw(cv, text, x + dx, y + dy, scale, outline)
    draw_text_raw(cv, text, x, y, scale, fill)


# ---------------------------------------------------------------- scene

def _lcg(seed):
    state = seed & 0xFFFFFFFF

    def nxt():
        nonlocal state
        state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
        return state / 2**32

    return nxt


def draw_scene(cv, ghost_path):
    # Sky gradient: deep purple -> magenta -> orange, down to the horizon.
    stops = [(0, (43, 16, 85)), (220, (122, 48, 120)),
             (420, (226, 84, 110)), (640, (255, 158, 61))]
    for y in range(0, 641):
        for i in range(len(stops) - 1):
            y0, c0 = stops[i]
            y1, c1 = stops[i + 1]
            if y0 <= y <= y1:
                cv.fill_rect(0, y, W, y + 1, lerp_color(c0, c1, (y - y0) / (y1 - y0)))
                break

    # Sun with a soft glow, left of centre so the ghost floats beside it.
    for r, a in ((215, 40), (195, 60), (180, 90)):
        cv.disc(300, 390, r, (255, 190, 110), a)
    cv.disc(300, 390, 165, (255, 243, 196))

    # Skyline silhouette along the horizon.
    rnd = _lcg(20261119)
    x = -10
    while x < W + 10:
        bw = int(50 + rnd() * 90)
        bh = int(60 + rnd() * 110)
        cv.fill_rect(x, 640 - bh, x + bw, 641, (30, 11, 46))
        # A few lit windows.
        for wy in range(640 - bh + 12, 632, 22):
            for wx in range(x + 8, x + bw - 8, 18):
                if rnd() < 0.35:
                    cv.fill_rect(wx, wy, wx + 7, wy + 9, (255, 214, 120), 200)
        x += bw + int(rnd() * 14)

    # Ocean: deep blue-purple gradient with shimmer streaks.
    for y in range(640, H):
        t = (y - 640) / (H - 640)
        cv.fill_rect(0, y, W, y + 1, lerp_color((38, 48, 110), (11, 16, 48), t))
    rnd2 = _lcg(77)
    for _ in range(46):
        sy = int(650 + rnd2() * 360)
        sx = int(rnd2() * W)
        ln = int(30 + rnd2() * 130)
        cv.fill_rect(sx, sy, min(W, sx + ln), sy + 3, (255, 170, 120), int(40 + rnd2() * 70))
    # Sun reflection column under the sun.
    rnd3 = _lcg(9)
    for _ in range(26):
        sy = int(650 + rnd3() * 340)
        ln = int(60 + rnd3() * 160)
        cv.fill_rect(300 - ln // 2, sy, 300 + ln // 2, sy + 3, (255, 200, 120), 90)

    # The make.fun ghost, large, floating over Vice City beside the sun.
    gw, gh, gpix = load_png(ghost_path)
    cv.disc(575, 530, 228, (20, 8, 38), 35)  # soft shadow behind the ghost
    cv.blit(gw, gh, gpix, 340, 290, 440, 440)

    # Palm silhouettes framing the scene.
    ink = (22, 10, 36)
    for base_x, crown_x, crown_y, lean in ((95, 150, 500, 1), (935, 880, 520, -1)):
        # Curved trunk: quadratic bezier from base to crown.
        cx, cy = base_x, H
        px, py = base_x, H
        for i in range(1, 41):
            t = i / 40
            bx = (1 - t) ** 2 * base_x + 2 * (1 - t) * t * (base_x + lean * 30) + t * t * crown_x
            by = (1 - t) ** 2 * H + 2 * (1 - t) * t * 760 + t * t * crown_y
            cv.thick_line(int(px), int(py), int(bx), int(by), 15, ink)
            px, py = bx, by
        # Fronds: drooping arcs out of the crown.
        for ang, ln in ((-160, 150), (-130, 170), (-100, 175), (-70, 170),
                        (-40, 155), (-15, 135)):
            import math
            rad = math.radians(ang)
            ex = crown_x + int(ln * math.cos(rad))
            ey = crown_y + int(ln * math.sin(rad) * 0.55) + 42
            mx = crown_x + int(ln * 0.55 * math.cos(rad))
            my = crown_y + int(ln * 0.55 * math.sin(rad) * 0.55) - 26
            # Quadratic segment crown -> mid -> tip, drawn as short chords.
            qx, qy = crown_x, crown_y
            for j in range(1, 13):
                t = j / 12
                bx = (1 - t) ** 2 * crown_x + 2 * (1 - t) * t * mx + t * t * ex
                by = (1 - t) ** 2 * crown_y + 2 * (1 - t) * t * my + t * t * ey
                cv.thick_line(int(qx), int(qy), int(bx), int(by), 9, ink)
                qx, qy = bx, by
        cv.disc(crown_x, crown_y, 12, ink)  # coconut cluster

    # Captions: big, outlined, readable at 480x480.
    draw_text(cv, "WAITED 13 YEARS", W // 2, 34, 9, (255, 255, 255))
    draw_text(cv, "FOR GTA 6", W // 2, 118, 9, (255, 255, 255))
    draw_text(cv, "MY AI AGENT ALREADY", W // 2, 836, 7, (255, 228, 92))
    draw_text(cv, "GOT PAID ON MAKE.FUN", W // 2, 912, 7, (255, 228, 92))


def main():
    ghost_path, out_path = sys.argv[1], sys.argv[2]
    cv = Canvas(W, H)
    draw_scene(cv, ghost_path)
    save_png(out_path, W, H, cv.px)
    print(f"wrote {out_path} ({W}x{H})")


if __name__ == "__main__":
    main()
