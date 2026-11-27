#!/usr/bin/env python3
"""Draw Learning Hub scratch pads as PNG pictures, with no extra libraries.

Usage: python3 -I pad_png.py rows.json out_dir
rows.json is a JSON list of database rows, each {"col": "scratch" or "scratchtutor", "id": "...", "data": {...}},
for example the result of:
  select col, id, data from docs where col in ('scratch','scratchtutor') and updated_at > <last run>
A pad's data: s = strokes [{c: "ink"|"red"|"tutor", w: width, p: [x1, y1, x2, y2, ...]}] in a space 1000 units wide,
t = typed text. A row with an id ending in .c<digits> and lessonId "cleared:<lesson>" is a copy of a pad he cleared.
Writes one <id>.png per pad (his strokes in black and red, the tutor's layer in purple on top) and <id>.txt with
the typed text, and prints one line per pad: id, stroke count, picture file.
"""
import json, os, struct, sys, zlib

COL = {'ink': (19, 33, 43), 'red': (192, 57, 43), 'tutor': (123, 63, 228)}
SCALE = 0.8   # pixels per pad unit: 1000 units -> 800 px

def png(path, w, h, px):
    raw = b''.join(b'\x00' + bytes(px[y * w * 3:(y + 1) * w * 3]) for y in range(h))
    def chunk(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
                + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))

def draw(strokes_layers):
    pts = [v for layer in strokes_layers for st in layer[0] for v in (st.get('p') or [])]
    xs, ys = pts[0::2] or [0], pts[1::2] or [0]
    w = int(max(1000, max(xs) + 40) * SCALE); h = int(max(200, max(ys) + 40) * SCALE)
    w, h = min(w, 4000), min(h, 6000)
    px = bytearray([255]) * (w * h * 3)
    for gx in range(0, w, int(40 * SCALE)):            # light grid like the pad
        for y in range(h): px[(y * w + gx) * 3:(y * w + gx) * 3 + 3] = b'\xe6\xea\xee'
    for gy in range(0, h, int(40 * SCALE)):
        px[gy * w * 3:(gy + 1) * w * 3] = b'\xe6\xea\xee' * w
    def dot(cx, cy, r, c):
        r2 = r * r
        for y in range(max(0, int(cy - r)), min(h, int(cy + r) + 1)):
            for x in range(max(0, int(cx - r)), min(w, int(cx + r) + 1)):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r2: i = (y * w + x) * 3; px[i:i + 3] = bytes(c)
    for strokes, force in strokes_layers:
        for st in strokes:
            p = [float(v) * SCALE for v in (st.get('p') or [])]
            c = COL[force or ('red' if st.get('c') == 'red' else 'ink')]
            r = max(1.0, float(st.get('w') or 5) * SCALE / 2)
            for i in range(0, len(p) - 1, 2):
                x0, y0 = p[i], p[i + 1]
                x1, y1 = (p[i + 2], p[i + 3]) if i + 3 < len(p) else (x0, y0)
                n = max(1, int(max(abs(x1 - x0), abs(y1 - y0)) / max(1.0, r / 2)))
                for k in range(n + 1): dot(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n, r, c)
    return w, h, px

def main():
    rows, out = json.load(open(sys.argv[1])), sys.argv[2]
    os.makedirs(out, exist_ok=True)
    tut = {r['id']: r['data'] for r in rows if r.get('col') == 'scratchtutor'}
    for r in rows:
        if r.get('col') != 'scratch': continue
        d = r.get('data') or {}; t = tut.get(r['id']) or {}
        layers = [(d.get('s') or [], None), (t.get('s') or [], 'tutor')]
        safe = ''.join(ch if ch.isalnum() or ch in '.-_' else '_' for ch in r['id'])
        n = len(d.get('s') or [])
        if n or (t.get('s')):
            w, h, px = draw(layers); png(os.path.join(out, safe + '.png'), w, h, px)
        text = (d.get('t') or '').strip(); tt = (t.get('t') or '').strip()
        if text or tt:
            with open(os.path.join(out, safe + '.txt'), 'w') as f: f.write(text + ('\n\nTutor: ' + tt if tt else ''))
        print(r['id'], n, 'strokes', (safe + '.png') if n or t.get('s') else '(no drawing)', '+text' if text else '')

if __name__ == '__main__':
    main()
