"""Visual layer for Flicker (Team Chaos Theory).

Background: soft butterflies drifting on wandering, slightly chaotic paths
over a warm ivory sky with floating petals. It is a nod to the butterfly effect, the best
known idea in chaos theory: small causes, large effects. Clicking Generate is
the "flap": the butterflies scatter from the button and the petals brighten.

Palette (Flicker): Deep Warm Brown #55423D, Muted Plum #76576B, Warm Taupe #8D7165,
Warm Clay #C98E78, Dusty Beige #D9C5B8, Pearl Cream #F1E8DA, Warm Ivory #F7F0E8,
Rose Quartz #E9A1A8.

Dreamy photo backdrop: a sunlit blossom-tree scene fills the viewport under a
blush-and-ivory veil with warm golden light, subtle film grain and a soft
vignette; the butterflies drift over it. The default photo is embedded in this
file (EMBEDDED_BACKGROUND); drop assets/background.jpg to replace it, or set
USE_BACKGROUND_PHOTO = False to go back to the plain ivory sky.

Mosaic mode: if assets/gallery/ contains images, an editorial mosaic of those
images sits behind the butterflies (they then fly over the gallery). Images are
shrunk to small JPEG thumbnails and embedded once at startup, so phones load
them fast and no static-file setup is needed.

Exports:
    HEAD        -> fonts + background script, pass as head=
    CSS         -> page styles, pass as css=
    HERO_HTML   -> header block, render with gr.HTML(HERO_HTML)
    make_theme()-> gradio theme, pass as theme=
The Generate button must have elem_id="flicker-generate".
"""

import base64
import io
import json
import os

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800'
    '&family=Manrope:wght@400;500;600;700&display=swap" rel="stylesheet">'
)

# ---------------------------------------------------------------------------
# Optional gallery mosaic
# ---------------------------------------------------------------------------
GALLERY_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "gallery"
)

# (column span, row span) pattern for an asymmetric editorial grid
_SPANS = [(2, 2), (1, 1), (1, 2), (2, 1), (1, 1), (1, 2),
          (2, 2), (1, 1), (2, 1), (1, 1), (1, 2), (1, 1)]


def _thumb_data_uri(path, max_side=480):
    from PIL import Image

    with Image.open(path) as im:
        im = im.convert("RGB")
        im.thumbnail((max_side, max_side))
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=72, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def mosaic_html(max_images=14):
    """Build the mosaic markup from assets/gallery; returns "" if there are no images."""
    if not os.path.isdir(GALLERY_DIR):
        return ""
    files = sorted(
        f for f in os.listdir(GALLERY_DIR)
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
    )[:max_images]
    uris = []
    for f in files:
        try:
            uris.append(_thumb_data_uri(os.path.join(GALLERY_DIR, f)))
        except Exception:
            continue
    if not uris:
        return ""
    tiles = []
    for i in range(max(24, len(uris) * 2)):
        cs, rs = _SPANS[i % len(_SPANS)]
        tiles.append(
            f'<div class="flicker-tile" style="grid-column:span {cs};grid-row:span {rs}">'
            f'<img src="{uris[i % len(uris)]}" alt="" loading="lazy" decoding="async"></div>'
        )
    return '<div id="flicker-mosaic" aria-hidden="true">' + "".join(tiles) + "</div>"


MOSAIC = mosaic_html()

# ---------------------------------------------------------------------------
# Dreamy background photo
# ---------------------------------------------------------------------------
USE_BACKGROUND_PHOTO = True
ASSETS_DIR = os.path.dirname(GALLERY_DIR)

EMBEDDED_BACKGROUND = (
    "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"
    "74b/AJUP9/8ADHrfaz//2Q=="
)


def background_data_uri(max_side=1920):
    """assets/background.* if present, else the embedded default; "" when disabled."""
    if not USE_BACKGROUND_PHOTO:
        return ""
    for name in ("background.jpg", "background.jpeg", "background.png", "background.webp"):
        path = os.path.join(ASSETS_DIR, name)
        if os.path.isfile(path):
            try:
                return _thumb_data_uri(path, max_side=max_side)
            except Exception:
                break
    return "data:image/jpeg;base64," + "".join(EMBEDDED_BACKGROUND)


PHOTO = background_data_uri()

# ---------------------------------------------------------------------------
# Hero artwork: an original cherry-blossom branch drawn as vector SVG
# (crisp at any resolution, no image files, no copyright concerns)
# ---------------------------------------------------------------------------
def _cubic(p0, p1, p2, p3, t):
    u = 1 - t
    return (u**3*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t**3*p3[0],
            u**3*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t**3*p3[1])


def blossom_svg(seed=7):
    import math
    import random

    rnd = random.Random(seed)
    # (start, ctrl1, ctrl2, end, stroke width, number of flowers)
    branches = [
        ((660, 20), (580, 35), (505, 85), (430, 140), 17, 7),
        ((430, 140), (360, 190), (250, 250), (140, 335), 11, 9),
        ((140, 335), (112, 352), (85, 362), (48, 372), 5, 3),
        ((505, 88), (478, 45), (428, 22), (362, 12), 6, 5),
        ((382, 176), (362, 236), (334, 286), (302, 330), 5, 4),
        ((300, 226), (252, 192), (192, 178), (132, 182), 4, 5),
        ((575, 45), (572, 102), (552, 152), (526, 196), 4, 4),
        ((226, 286), (210, 330), (196, 360), (172, 396), 3, 3),
    ]
    out = [
        '<svg class="flicker-art" viewBox="0 0 660 470" xmlns="http://www.w3.org/2000/svg" '
        'role="img" aria-label="Cherry blossom branch">',
        '<defs>'
        '<radialGradient id="fpetal" cx="50%" cy="85%" r="85%">'
        '<stop offset="0" stop-color="#E9A1A8"/><stop offset="0.55" stop-color="#F3C6C6"/>'
        '<stop offset="1" stop-color="#FBF4EE"/></radialGradient>'
        '<linearGradient id="fbark" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#55423D"/><stop offset="1" stop-color="#76576B"/></linearGradient>'
        '<filter id="fsoft" x="-20%" y="-20%" width="140%" height="140%">'
        '<feDropShadow dx="0" dy="6" stdDeviation="7" flood-color="#55423D" flood-opacity="0.16"/></filter>'
        '</defs><g filter="url(#fsoft)">',
    ]
    for p0, c1, c2, p3, wdt, _ in branches:
        out.append(
            f'<path d="M{p0[0]},{p0[1]} C{c1[0]},{c1[1]} {c2[0]},{c2[1]} {p3[0]},{p3[1]}" '
            f'fill="none" stroke="url(#fbark)" stroke-width="{wdt}" stroke-linecap="round"/>'
        )

    def flower(x, y, r, rot):
        g = [f'<g transform="translate({x:.1f},{y:.1f}) rotate({rot:.0f})">']
        for k in range(5):
            a = k * 72
            g.append(
                f'<ellipse cx="0" cy="{-r*0.52:.1f}" rx="{r*0.42:.1f}" ry="{r*0.55:.1f}" '
                f'fill="url(#fpetal)" stroke="#C98E78" stroke-opacity="0.28" stroke-width="0.8" '
                f'transform="rotate({a})"/>'
            )
        for k in range(7):
            a = math.radians(k * 51 + rot)
            ex, ey = math.cos(a) * r * 0.36, math.sin(a) * r * 0.36
            g.append(f'<line x1="0" y1="0" x2="{ex:.1f}" y2="{ey:.1f}" stroke="#76576B" '
                     f'stroke-width="0.9" stroke-opacity="0.7"/>')
            g.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="{r*0.05+0.7:.1f}" fill="#C98E78"/>')
        g.append(f'<circle r="{r*0.15:.1f}" fill="#C98E78"/></g>')
        return "".join(g)

    def bud(x, y, r, rot):
        return (f'<g transform="translate({x:.1f},{y:.1f}) rotate({rot:.0f})">'
                f'<ellipse rx="{r*0.45:.1f}" ry="{r*0.7:.1f}" fill="#E9A1A8"/>'
                f'<ellipse cy="{r*0.55:.1f}" rx="{r*0.3:.1f}" ry="{r*0.25:.1f}" fill="#8D7165"/></g>')

    for p0, c1, c2, p3, wdt, n in branches:
        for i in range(n):
            t = (i + 0.5) / n + rnd.uniform(-0.05, 0.05)
            x, y = _cubic(p0, c1, c2, p3, min(max(t, 0.02), 0.98))
            x += rnd.uniform(-14, 14)
            y += rnd.uniform(-14, 14)
            if rnd.random() < 0.18:
                out.append(bud(x, y, rnd.uniform(7, 10), rnd.uniform(0, 360)))
            else:
                out.append(flower(x, y, rnd.uniform(13, 23), rnd.uniform(0, 72)))
    # a few drifting petals
    for _ in range(9):
        x, y = rnd.uniform(40, 420), rnd.uniform(360, 465)
        rr = rnd.uniform(5, 8)
        out.append(
            f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{rr*0.75:.1f}" ry="{rr:.1f}" fill="url(#fpetal)" '
            f'opacity="0.8" transform="rotate({rnd.uniform(0,360):.0f} {x:.1f} {y:.1f})"/>'
        )
    out.append("</g></svg>")
    return "".join(out)


# ---------------------------------------------------------------------------
# Background script: butterflies + fireflies
# ---------------------------------------------------------------------------
SCRIPT = r"""
<script>
(function () {
  function start() {
    if (document.getElementById('flicker-bg')) return;
    // Flicker uses a light, warm theme: keep Gradio out of dark mode
    // only touch the class list when "dark" is actually present; an unconditional
    // remove() rewrites the attribute and would re-trigger the observer forever
    function noDark() {
      var de = document.documentElement, bd = document.body;
      if (de.classList.contains('dark')) de.classList.remove('dark');
      if (bd && bd.classList.contains('dark')) bd.classList.remove('dark');
    }
    noDark();
    new MutationObserver(noDark).observe(document.body, { attributes: true, attributeFilter: ['class'] });

    var PHOTO = __PHOTO__;
    var hasPhoto = !!PHOTO;
    if (hasPhoto) {
      var ph = document.createElement('div');
      ph.id = 'flicker-photo';
      ph.setAttribute('aria-hidden', 'true');
      ph.style.backgroundImage = 'url("' + PHOTO + '")';
      document.body.prepend(ph);
      document.body.classList.add('flicker-has-photo');
    }

    var MOSAIC = hasPhoto ? '' : __MOSAIC__;
    var hasMosaic = !!MOSAIC;
    if (hasMosaic) {
      var holder = document.createElement('div');
      holder.innerHTML = MOSAIC;
      document.body.prepend(holder.firstChild);
      document.body.classList.add('flicker-has-mosaic');
    }

    var c = document.createElement('canvas');
    c.id = 'flicker-bg';
    c.setAttribute('aria-hidden', 'true');
    document.body.prepend(c);
    var ctx = c.getContext('2d');
    var sky = document.createElement('canvas');
    var sctx = sky.getContext('2d');

    var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var small = window.innerWidth < 768;
    var w = 0, h = 0, dpr = 1, t = 0;

    // palette: muted plum, warm clay, rose quartz, warm taupe
    var WING = ['118,87,107', '201,142,120', '233,161,168', '141,113,101'];
    var FIRE = ['233,161,168', '201,142,120', '118,87,107'];

    function rand(a, b) { return a + Math.random() * (b - a); }

    var flies = [], bugs = [];
    var burst = 0, bx = 0, by = 0;

    function makeFlies() {
      flies = [];
      var n = small ? 7 : 14;
      for (var i = 0; i < n; i++) {
        flies.push({
          x: rand(0, w), y: rand(0, h), ang: rand(0, Math.PI * 2),
          speed: rand(0.45, 0.95), size: rand(small ? 9 : 10, small ? 15 : 22),
          phase: rand(0, 6.28), flap: rand(0.16, 0.26),
          w1: rand(0.004, 0.009), w2: rand(0.011, 0.02), o: rand(0, 100),
          col: WING[i % WING.length], trail: []
        });
      }
      bugs = [];
      var m = small ? 34 : 70;
      for (var j = 0; j < m; j++) {
        bugs.push({
          x: rand(0, w), y: rand(0, h), vx: rand(-0.15, 0.15), vy: rand(-0.12, 0.12),
          r: rand(0.8, 2.0), tw: rand(0.01, 0.035), o: rand(0, 100),
          col: FIRE[j % FIRE.length]
        });
      }
    }

    function paintSky() {
      sky.width = w; sky.height = h;
      sctx.fillStyle = '#F7F0E8';
      sctx.fillRect(0, 0, w, h);
      var g1 = sctx.createRadialGradient(w * 0.12, h * 0.08, 0, w * 0.12, h * 0.08, Math.max(w, h) * 0.65);
      g1.addColorStop(0, 'rgba(233,161,168,0.38)');
      g1.addColorStop(1, 'rgba(233,161,168,0)');
      sctx.fillStyle = g1; sctx.fillRect(0, 0, w, h);
      var g2 = sctx.createRadialGradient(w * 0.88, h * 0.92, 0, w * 0.88, h * 0.92, Math.max(w, h) * 0.6);
      g2.addColorStop(0, 'rgba(217,197,184,0.75)');
      g2.addColorStop(1, 'rgba(217,197,184,0)');
      sctx.fillStyle = g2; sctx.fillRect(0, 0, w, h);
      var g3 = sctx.createRadialGradient(w * 0.75, h * 0.2, 0, w * 0.75, h * 0.2, Math.max(w, h) * 0.45);
      g3.addColorStop(0, 'rgba(118,87,107,0.10)');
      g3.addColorStop(1, 'rgba(118,87,107,0)');
      sctx.fillStyle = g3; sctx.fillRect(0, 0, w, h);
    }

    function resize() {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = c.width = Math.floor(window.innerWidth * dpr);
      h = c.height = Math.floor(window.innerHeight * dpr);
      c.style.width = window.innerWidth + 'px';
      c.style.height = window.innerHeight + 'px';
      if (!hasMosaic && !hasPhoto) paintSky();
      makeFlies();
      if (reduce) draw(true);
    }

    function wing(s) {
      // upper lobe
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.bezierCurveTo(s * 0.2, -s * 1.15, s * 1.35, -s * 1.05, s * 1.05, -s * 0.15);
      ctx.bezierCurveTo(s * 0.9, 0, s * 0.3, 0.02 * s, 0, 0);
      ctx.fill();
      // lower lobe
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.bezierCurveTo(s * 0.7, s * 0.1, s * 0.95, s * 0.8, s * 0.48, s * 0.88);
      ctx.bezierCurveTo(s * 0.22, s * 0.92, s * 0.05, s * 0.42, 0, 0);
      ctx.fill();
    }

    function drawFly(f, still) {
      // trail of light behind it
      for (var i = 0; i < f.trail.length; i++) {
        var p = f.trail[i];
        var a = (i / f.trail.length) * 0.22;
        ctx.fillStyle = 'rgba(' + f.col + ',' + a + ')';
        ctx.beginPath();
        ctx.arc(p[0], p[1], 1.3 * dpr, 0, 6.283);
        ctx.fill();
      }
      var s = f.size * dpr;
      var open = still ? 1 : 0.22 + 0.78 * Math.abs(Math.cos(f.phase));
      ctx.save();
      ctx.translate(f.x, f.y);
      ctx.rotate(f.ang + Math.PI / 2);
      ctx.shadowColor = 'rgba(' + f.col + ',0.45)';
      ctx.shadowBlur = 10 * dpr;
      ctx.fillStyle = 'rgba(' + f.col + ',0.78)';
      ctx.save(); ctx.scale(open, 1); wing(s); ctx.restore();
      ctx.save(); ctx.scale(-open, 1); wing(s); ctx.restore();
      ctx.shadowBlur = 0;
      ctx.fillStyle = 'rgba(85,66,61,0.85)';
      ctx.beginPath();
      ctx.ellipse(0, 0, s * 0.07, s * 0.42, 0, 0, 6.283);
      ctx.fill();
      ctx.restore();
    }

    function moveFly(f) {
      f.ang += Math.sin(t * f.w1 + f.o) * 0.014 + Math.sin(t * f.w2 + f.o * 2) * 0.01;
      if (burst > 0.02) {
        var away = Math.atan2(f.y - by, f.x - bx);
        var d = away - f.ang;
        d = Math.atan2(Math.sin(d), Math.cos(d));
        f.ang += d * 0.08 * burst;
      }
      var spd = f.speed * (1 + burst * 4) * dpr;
      f.x += Math.cos(f.ang) * spd;
      f.y += Math.sin(f.ang) * spd + Math.sin(f.phase) * 0.25 * dpr;
      f.phase += f.flap * (1 + burst * 1.8);
      var m = 40 * dpr;
      if (f.x < -m) f.x = w + m; else if (f.x > w + m) f.x = -m;
      if (f.y < -m) f.y = h + m; else if (f.y > h + m) f.y = -m;
      f.trail.push([f.x, f.y]);
      if (f.trail.length > 24) f.trail.shift();
    }

    function drawBug(b, still) {
      if (!still) {
        b.x += b.vx * dpr; b.y += b.vy * dpr;
        b.vx += rand(-0.01, 0.01); b.vy += rand(-0.01, 0.01);
        b.vx = Math.max(-0.25, Math.min(0.25, b.vx));
        b.vy = Math.max(-0.2, Math.min(0.2, b.vy));
        if (b.x < 0) b.x = w; else if (b.x > w) b.x = 0;
        if (b.y < 0) b.y = h; else if (b.y > h) b.y = 0;
      }
      var a = 0.25 + 0.75 * (0.5 + 0.5 * Math.sin(t * b.tw + b.o));
      a = Math.min(1, a * (1 + burst * 0.8));
      var r = b.r * dpr;
      var g = ctx.createRadialGradient(b.x, b.y, 0, b.x, b.y, r * 6);
      g.addColorStop(0, 'rgba(' + b.col + ',' + (a * 0.22) + ')');
      g.addColorStop(1, 'rgba(' + b.col + ',0)');
      ctx.fillStyle = g;
      ctx.beginPath(); ctx.arc(b.x, b.y, r * 6, 0, 6.283); ctx.fill();
      ctx.fillStyle = 'rgba(' + b.col + ',' + (a * 0.7) + ')';
      ctx.beginPath(); ctx.arc(b.x, b.y, r * 1.2, 0, 6.283); ctx.fill();
    }

    function draw(still) {
      if (hasMosaic || hasPhoto) ctx.clearRect(0, 0, w, h);
      else ctx.drawImage(sky, 0, 0);
      ctx.globalCompositeOperation = 'source-over';
      bugs.forEach(function (b) { drawBug(b, still); });
      flies.forEach(function (f) { if (!still) moveFly(f); drawFly(f, still); });
      ctx.globalCompositeOperation = 'source-over';
    }

    function frame() {
      t += 1;
      draw(false);
      burst = burst * 0.97;
      requestAnimationFrame(frame);
    }

    window.addEventListener('click', function (e) {
      var btn = e.target && e.target.closest && e.target.closest('#flicker-generate');
      if (btn) { burst = 1; bx = e.clientX * dpr; by = e.clientY * dpr; }
    }, true);
    window.addEventListener('resize', resize);

    resize();
    if (!reduce) requestAnimationFrame(frame);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
})();
</script>
"""

HEAD = FONTS + SCRIPT.replace("__PHOTO__", json.dumps(PHOTO)).replace("__MOSAIC__", json.dumps(MOSAIC))

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------
CSS = r"""
:root {
  --brown: #55423D;
  --plum: #76576B;
  --taupe: #8D7165;
  --clay: #C98E78;
  --beige: #D9C5B8;
  --pearl: #F1E8DA;
  --ivory: #F7F0E8;
  --rose: #E9A1A8;
  --panel: rgba(255, 251, 246, 0.82);
  --field: #FFFCF8;
  --line: rgba(85, 66, 61, 0.14);
}

html, body { background: var(--ivory) !important; }

#flicker-bg {
  position: fixed;
  inset: 0;
  z-index: 1;
  pointer-events: none;
}

/* Optional gallery mosaic, sits under the butterflies */
#flicker-mosaic {
  position: fixed;
  inset: 0;
  z-index: 0;
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  grid-auto-rows: 17vh;
  grid-auto-flow: dense;
  gap: 4px;
  padding: 4px;
  background: var(--pearl);
  overflow: hidden;
  pointer-events: none;
}
.flicker-tile { overflow: hidden; border-radius: 2px; background: var(--beige); }
.flicker-tile img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  animation: flicker-drift 40s ease-in-out infinite alternate;
}
.flicker-tile:nth-child(3n) img { animation-duration: 52s; animation-delay: -12s; }
.flicker-tile:nth-child(4n) img { animation-duration: 46s; animation-delay: -24s; }
@keyframes flicker-drift {
  from { transform: scale(1.02); }
  to { transform: scale(1.12); }
}
#flicker-mosaic::after {
  content: "";
  position: fixed;
  inset: 0;
  background:
    linear-gradient(90deg, rgba(247,240,232,0.94) 0%, rgba(247,240,232,0.78) 55%, rgba(247,240,232,0.42) 100%),
    linear-gradient(180deg, rgba(247,240,232,0.10) 0%, rgba(247,240,232,0.55) 100%);
}
body.flicker-has-mosaic .gradio-container .block,
body.flicker-has-mosaic .gradio-container .form,
body.flicker-has-mosaic .gradio-container .panel {
  background: rgba(255, 251, 246, 0.90) !important;
}

/* Dreamy photo backdrop, under the butterflies */
#flicker-photo {
  position: fixed;
  inset: -16px;
  z-index: 0;
  background-color: var(--ivory);
  background-size: cover;
  background-position: center 58%;
  filter: blur(1px) saturate(0.9) sepia(0.04) hue-rotate(-8deg);
  pointer-events: none;
  animation: flicker-breathe 32s ease-in-out infinite alternate;
}
@keyframes flicker-breathe {
  from { transform: scale(1.0); }
  to { transform: scale(1.05); }
}
/* blush haze + warm golden light, ivory veil strongest where the text sits */
#flicker-photo::after {
  content: "";
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 55% 45% at 80% 10%, rgba(255, 216, 160, 0.40) 0%, rgba(255, 216, 160, 0) 70%),
    radial-gradient(ellipse 70% 55% at 15% 95%, rgba(233, 161, 168, 0.26) 0%, rgba(233, 161, 168, 0) 70%),
    linear-gradient(90deg, rgba(247,240,232,0.70) 0%, rgba(247,238,234,0.40) 45%, rgba(244,228,228,0.12) 100%),
    linear-gradient(180deg, rgba(240,205,208,0.14) 0%, rgba(247,240,232,0.30) 100%),
    linear-gradient(0deg, rgba(238, 186, 192, 0.16), rgba(238, 186, 192, 0.16));
}
/* vintage film grain + soft vignette (very subtle, never blocks clicks) */
body.flicker-has-photo::after {
  content: "";
  position: fixed;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  opacity: 0.09;
  mix-blend-mode: multiply;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0.33  0 0 0 0 0.26  0 0 0 0 0.24  0 0 0 0.9 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
}
body.flicker-has-photo::before {
  content: "";
  position: fixed;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  background: radial-gradient(ellipse at center, rgba(0,0,0,0) 62%, rgba(118, 87, 107, 0.14) 100%);
}
body.flicker-has-photo .gradio-container .block,
body.flicker-has-photo .gradio-container .form,
body.flicker-has-photo .gradio-container .panel {
  background: rgba(255, 251, 246, 0.86) !important;
}
/* the header block stays see-through so the title floats on the photo */
body .gradio-container .block:has(.flicker-hero-wrap) {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

gradio-app, .gradio-container, .gradio-container .main, .gradio-container .contain {
  background: transparent !important;
}

.gradio-container {
  position: relative;
  z-index: 2;
  max-width: 1180px !important;
  font-family: 'Manrope', system-ui, sans-serif !important;
  color: var(--brown) !important;
}
.gradio-container .prose, .gradio-container .prose * { color: var(--brown); }

/* Header */
.flicker-hero { padding: 56px 4px 28px; max-width: 760px; }
.flicker-title {
  font-family: 'Syne', sans-serif;
  font-weight: 800;
  font-size: clamp(64px, 11vw, 148px);
  line-height: 0.9;
  letter-spacing: -0.045em;
  margin: 0;
  color: var(--brown);
  text-shadow: 0 6px 30px rgba(233, 161, 168, 0.55);
  animation: flicker-on 1.4s steps(1, end) 1 both;
}
@keyframes flicker-on {
  0% { opacity: 0; }
  8% { opacity: 0.9; }
  12% { opacity: 0.1; }
  20% { opacity: 1; }
  26% { opacity: 0.25; }
  34%, 100% { opacity: 1; }
}
.flicker-tagline {
  font-size: clamp(18px, 2.2vw, 24px);
  line-height: 1.45;
  color: var(--brown);
  margin: 20px 0 10px;
  max-width: 34ch;
}
.flicker-facts {
  color: var(--plum);
  font-size: 15px;
  line-height: 1.65;
  max-width: 58ch;
  margin: 0;
}
.flicker-team { color: var(--taupe); font-size: 14px; margin: 22px 0 0; }

/* Panels: soft pearl cards */
.gradio-container .block,
.gradio-container .form,
.gradio-container .panel {
  background: var(--panel) !important;
  border: 1px solid var(--line) !important;
  border-radius: 16px !important;
  box-shadow: 0 8px 28px rgba(85, 66, 61, 0.06);
}
.gradio-container .form .block { background: transparent !important; border: none !important; box-shadow: none; }

.gradio-container textarea,
.gradio-container input:not([type="checkbox"]):not([type="radio"]),
.gradio-container select {
  background: var(--field) !important;
  color: var(--brown) !important;
  border: 1px solid var(--line) !important;
  border-radius: 10px !important;
  font-family: 'Manrope', system-ui, sans-serif !important;
}
.gradio-container textarea { font-size: 17px !important; line-height: 1.5 !important; }
.gradio-container textarea::placeholder { color: var(--taupe) !important; opacity: 0.8; }

.gradio-container label,
.gradio-container .label-wrap,
.gradio-container span[data-testid="block-info"] {
  color: var(--plum) !important;
  font-weight: 600 !important;
}

/* Checkboxes: keep the checked state visible */
.gradio-container input[type="checkbox"],
.gradio-container input[type="radio"] {
  accent-color: var(--clay);
  width: 18px; height: 18px;
}
.gradio-container input[type="checkbox"]:checked,
.gradio-container input[type="radio"]:checked {
  background-color: var(--clay) !important;
  border-color: var(--clay) !important;
}

/* Generate button: deep warm brown, rose glow */
#flicker-generate, .gradio-container button.primary {
  background: var(--brown) !important;
  color: var(--ivory) !important;
  border: none !important;
  border-radius: 12px !important;
  font-family: 'Syne', sans-serif !important;
  font-weight: 700 !important;
  font-size: 18px !important;
  letter-spacing: -0.01em;
  box-shadow: 0 8px 24px rgba(233, 161, 168, 0.55);
  transition: background 0.15s ease, box-shadow 0.15s ease;
}
#flicker-generate:hover, .gradio-container button.primary:hover {
  background: var(--plum) !important;
  box-shadow: 0 10px 30px rgba(233, 161, 168, 0.75);
}

.gradio-container button.secondary {
  background: var(--field) !important;
  color: var(--brown) !important;
  border: 1px solid var(--line) !important;
  border-radius: 999px !important;
}
.gradio-container button.secondary:hover { border-color: var(--clay) !important; background: var(--pearl) !important; }

/* Keyboard focus */
.gradio-container :focus-visible {
  outline: 2px solid var(--plum) !important;
  outline-offset: 2px !important;
}

.gradio-container .image-container img,
.gradio-container .grid-wrap img { border-radius: 12px; }

footer { opacity: 0.6; }

/* Dropdown list */
.gradio-container ul.options {
  background: var(--field) !important;
  border: 1px solid var(--line) !important;
  border-radius: 10px !important;
  z-index: 100 !important;
  box-shadow: 0 12px 32px rgba(85, 66, 61, 0.18);
}
.gradio-container ul.options li { color: var(--brown) !important; }
.gradio-container ul.options li:hover,
.gradio-container ul.options li.selected { background: rgba(233, 161, 168, 0.35) !important; }

/* Let long checkbox labels wrap instead of scrolling sideways */
.gradio-container label span { white-space: normal !important; overflow-wrap: anywhere; }
.gradio-container .form > * { min-width: 0; }


/* Hero artwork beside the title */
.flicker-hero-wrap {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.flicker-art {
  flex: 0 0 auto;
  width: min(46vw, 600px);
  height: auto;
  margin: 12px -8px 0 0;
}
.gradio-container .block:has(.flicker-hero-wrap) {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}
@media (max-width: 900px) {
  .flicker-hero-wrap { display: block; }
  .flicker-art {
    position: absolute;
    right: -30px;
    top: 0;
    width: 78vw;
    opacity: 0.38;
    z-index: -1;
    margin: 0;
  }
}

@media (max-width: 768px) {
  #flicker-mosaic { grid-template-columns: repeat(3, 1fr); grid-auto-rows: 20vh; }
  #flicker-mosaic::after { background: rgba(247,240,232,0.85); }
  .flicker-hero { padding: 32px 0 16px; }
  .gradio-container { padding: 0 12px !important; }
}

@media (max-width: 768px) {
  #flicker-photo { background-position: 30% center; }
  #flicker-photo::after {
    background:
      radial-gradient(ellipse 90% 40% at 85% 4%, rgba(255, 216, 160, 0.32) 0%, rgba(255, 216, 160, 0) 70%),
      linear-gradient(180deg, rgba(247,238,234,0.50) 0%, rgba(247,240,232,0.62) 100%);
  }
}

@media (prefers-reduced-motion: reduce) {
  #flicker-photo { animation: none; }
  .flicker-title { animation: none; }
  .flicker-tile img { animation: none; }
}
"""

# The vector cherry-blossom branch beside the title (off: it overlapped the text)
SHOW_BLOSSOM_ART = False

HERO_HTML = """
<div class="flicker-hero-wrap">
  <div class="flicker-hero">
    <h1 class="flicker-title">Flicker</h1>
    <p class="flicker-tagline">Describe a scene and get an image in about a second.</p>
    <p class="flicker-facts">Flicker runs Stable Diffusion thirteen times faster than standard
    settings while keeping about 95% of its prompt alignment, and switches to a lighter model
    when the device is short on memory.</p>
    <p class="flicker-team">Built by Team Chaos Theory</p>
  </div>
""" + (blossom_svg() if SHOW_BLOSSOM_ART else "") + """
</div>
"""


def make_theme():
    """Warm light theme matching the CSS; falls back to a plain theme if a key is unsupported."""
    import gradio as gr

    try:
        return gr.themes.Base(
            primary_hue="rose",
            neutral_hue="stone",
            font=[gr.themes.GoogleFont("Manrope"), "system-ui", "sans-serif"],
        ).set(
            body_background_fill="#F7F0E8",
            body_background_fill_dark="#F7F0E8",
            body_text_color="#55423D",
            body_text_color_dark="#55423D",
            body_text_color_subdued="#76576B",
            body_text_color_subdued_dark="#76576B",
            block_background_fill="rgba(255,251,246,0.82)",
            block_background_fill_dark="rgba(255,251,246,0.82)",
            block_border_color="rgba(85,66,61,0.14)",
            block_border_color_dark="rgba(85,66,61,0.14)",
            block_label_text_color="#76576B",
            block_label_text_color_dark="#76576B",
            input_background_fill="#FFFCF8",
            input_background_fill_dark="#FFFCF8",
            button_primary_background_fill="#55423D",
            button_primary_background_fill_dark="#55423D",
            button_primary_text_color="#F7F0E8",
            button_primary_text_color_dark="#F7F0E8",
        )
    except Exception:
        return gr.themes.Base()