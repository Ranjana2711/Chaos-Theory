"""Visual layer for Flicker (Team Chaos Theory).

Background: glowing butterflies drifting on wandering, slightly chaotic paths
through a night sky of fireflies. It is a nod to the butterfly effect, the best
known idea in chaos theory: small causes, large effects. Clicking Generate is
the "flap": the butterflies scatter from the button and the fireflies brighten.

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
# Background script: butterflies + fireflies
# ---------------------------------------------------------------------------
SCRIPT = r"""
<script>
(function () {
  function start() {
    if (document.getElementById('flicker-bg')) return;
    document.documentElement.classList.add('dark');
    if (document.body) document.body.classList.add('dark');

    var MOSAIC = __MOSAIC__;
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

    // palette: moonlit cyan, honey gold, lilac, mint
    var WING = ['89,227,255', '255,201,92', '169,144,255', '111,242,194'];
    var FIRE = ['255,214,120', '150,236,255', '255,240,200'];

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
      sctx.fillStyle = '#060a12';
      sctx.fillRect(0, 0, w, h);
      var g1 = sctx.createRadialGradient(w * 0.15, h * 0.1, 0, w * 0.15, h * 0.1, Math.max(w, h) * 0.7);
      g1.addColorStop(0, 'rgba(70,52,140,0.45)');
      g1.addColorStop(1, 'rgba(70,52,140,0)');
      sctx.fillStyle = g1; sctx.fillRect(0, 0, w, h);
      var g2 = sctx.createRadialGradient(w * 0.85, h * 0.9, 0, w * 0.85, h * 0.9, Math.max(w, h) * 0.6);
      g2.addColorStop(0, 'rgba(20,110,130,0.35)');
      g2.addColorStop(1, 'rgba(20,110,130,0)');
      sctx.fillStyle = g2; sctx.fillRect(0, 0, w, h);
    }

    function resize() {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = c.width = Math.floor(window.innerWidth * dpr);
      h = c.height = Math.floor(window.innerHeight * dpr);
      c.style.width = window.innerWidth + 'px';
      c.style.height = window.innerHeight + 'px';
      if (!hasMosaic) paintSky();
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
        var a = (i / f.trail.length) * 0.28;
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
      ctx.shadowColor = 'rgba(' + f.col + ',0.95)';
      ctx.shadowBlur = 16 * dpr;
      ctx.fillStyle = 'rgba(' + f.col + ',0.82)';
      ctx.save(); ctx.scale(open, 1); wing(s); ctx.restore();
      ctx.save(); ctx.scale(-open, 1); wing(s); ctx.restore();
      ctx.shadowBlur = 0;
      ctx.fillStyle = 'rgba(255,255,255,0.85)';
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
      g.addColorStop(0, 'rgba(' + b.col + ',' + (a * 0.35) + ')');
      g.addColorStop(1, 'rgba(' + b.col + ',0)');
      ctx.fillStyle = g;
      ctx.beginPath(); ctx.arc(b.x, b.y, r * 6, 0, 6.283); ctx.fill();
      ctx.fillStyle = 'rgba(' + b.col + ',' + a + ')';
      ctx.beginPath(); ctx.arc(b.x, b.y, r, 0, 6.283); ctx.fill();
    }

    function draw(still) {
      if (hasMosaic) ctx.clearRect(0, 0, w, h);
      else ctx.drawImage(sky, 0, 0);
      ctx.globalCompositeOperation = 'lighter';
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

HEAD = FONTS + SCRIPT.replace("__MOSAIC__", json.dumps(MOSAIC))

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------
CSS = r"""
:root {
  --night: #060a12;
  --panel: rgba(10, 16, 30, 0.78);
  --panel-strong: rgba(6, 10, 18, 0.80);
  --line: rgba(200, 225, 255, 0.12);
  --text: #eaf2ff;
  --muted: #93a6c2;
  --gold: #ffc95c;
  --cyan: #59e3ff;
  --lilac: #a990ff;
}

html, body { background: var(--night) !important; }

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
  background: #0b0f18;
  overflow: hidden;
  pointer-events: none;
}
.flicker-tile { overflow: hidden; border-radius: 2px; background: #111726; }
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
    linear-gradient(90deg, rgba(6,10,18,0.88) 0%, rgba(6,10,18,0.70) 55%, rgba(6,10,18,0.38) 100%),
    linear-gradient(180deg, rgba(6,10,18,0.15) 0%, rgba(6,10,18,0.55) 100%);
}
body.flicker-has-mosaic .gradio-container .block,
body.flicker-has-mosaic .gradio-container .form,
body.flicker-has-mosaic .gradio-container .panel {
  background: rgba(8, 12, 22, 0.85) !important;
}

gradio-app, .gradio-container, .gradio-container .main, .gradio-container .contain {
  background: transparent !important;
}

.gradio-container {
  position: relative;
  z-index: 2;
  max-width: 1180px !important;
  font-family: 'Manrope', system-ui, sans-serif !important;
  color: var(--text) !important;
}

/* Header */
.flicker-hero { padding: 56px 4px 28px; max-width: 760px; }
.flicker-title {
  font-family: 'Syne', sans-serif;
  font-weight: 800;
  font-size: clamp(64px, 11vw, 148px);
  line-height: 0.9;
  letter-spacing: -0.045em;
  margin: 0;
  color: var(--text);
  text-shadow: 0 0 28px rgba(89, 227, 255, 0.25);
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
  color: var(--text);
  margin: 20px 0 10px;
  max-width: 34ch;
}
.flicker-facts {
  color: var(--muted);
  font-size: 15px;
  line-height: 1.65;
  max-width: 58ch;
  margin: 0;
}
.flicker-team { color: var(--muted); font-size: 14px; margin: 22px 0 0; }

/* Panels: frosted glass over the night sky */
.gradio-container .block,
.gradio-container .form,
.gradio-container .panel {
  background: var(--panel) !important;
  border: 1px solid var(--line) !important;
  border-radius: 16px !important;
}
.gradio-container .form .block { background: transparent !important; border: none !important; }

.gradio-container textarea,
.gradio-container input:not([type="checkbox"]):not([type="radio"]),
.gradio-container select {
  background: var(--panel-strong) !important;
  color: var(--text) !important;
  border: 1px solid var(--line) !important;
  border-radius: 10px !important;
  font-family: 'Manrope', system-ui, sans-serif !important;
}
.gradio-container textarea { font-size: 17px !important; line-height: 1.5 !important; }

.gradio-container label,
.gradio-container .label-wrap,
.gradio-container span[data-testid="block-info"] {
  color: var(--muted) !important;
  font-weight: 500 !important;
}

/* Checkboxes: keep the checked state visible */
.gradio-container input[type="checkbox"],
.gradio-container input[type="radio"] {
  accent-color: var(--gold);
  width: 18px; height: 18px;
}
.gradio-container input[type="checkbox"]:checked,
.gradio-container input[type="radio"]:checked {
  background-color: var(--gold) !important;
  border-color: var(--gold) !important;
}

/* Generate button: warm gold against the cool night */
#flicker-generate, .gradio-container button.primary {
  background: var(--gold) !important;
  color: #1a1206 !important;
  border: none !important;
  border-radius: 12px !important;
  font-family: 'Syne', sans-serif !important;
  font-weight: 700 !important;
  font-size: 18px !important;
  letter-spacing: -0.01em;
  box-shadow: 0 0 24px rgba(255, 201, 92, 0.35);
  transition: background 0.15s ease, box-shadow 0.15s ease;
}
#flicker-generate:hover, .gradio-container button.primary:hover {
  background: #ffd780 !important;
  box-shadow: 0 0 34px rgba(255, 201, 92, 0.55);
}

.gradio-container button.secondary {
  background: transparent !important;
  color: var(--text) !important;
  border: 1px solid var(--line) !important;
  border-radius: 999px !important;
}
.gradio-container button.secondary:hover { border-color: var(--cyan) !important; }

/* Keyboard focus */
.gradio-container :focus-visible {
  outline: 2px solid var(--cyan) !important;
  outline-offset: 2px !important;
}

.gradio-container .image-container img,
.gradio-container .grid-wrap img { border-radius: 12px; }

footer { opacity: 0.45; }

/* Dropdown list must float above the glass panels */
.gradio-container ul.options {
  background: #0b1120 !important;
  border: 1px solid var(--line) !important;
  border-radius: 10px !important;
  z-index: 100 !important;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.5);
}
.gradio-container ul.options li { color: var(--text) !important; }
.gradio-container ul.options li:hover,
.gradio-container ul.options li.selected { background: rgba(255, 201, 92, 0.18) !important; }

/* Let long checkbox labels wrap instead of scrolling sideways */
.gradio-container label span { white-space: normal !important; overflow-wrap: anywhere; }
.gradio-container .form > * { min-width: 0; }

@media (max-width: 768px) {
  #flicker-mosaic { grid-template-columns: repeat(3, 1fr); grid-auto-rows: 20vh; }
  #flicker-mosaic::after { background: rgba(6,10,18,0.78); }
  .flicker-hero { padding: 32px 0 16px; }
  .gradio-container { padding: 0 12px !important; }
}

@media (prefers-reduced-motion: reduce) {
  .flicker-title { animation: none; }
  .flicker-tile img { animation: none; }
}
"""

HERO_HTML = """
<div class="flicker-hero">
  <h1 class="flicker-title">Flicker</h1>
  <p class="flicker-tagline">Describe a scene and get an image in about a second.</p>
  <p class="flicker-facts">Flicker runs Stable Diffusion thirteen times faster than standard
  settings while keeping about 95% of its prompt alignment, and switches to a lighter model
  when the device is short on memory.</p>
  <p class="flicker-team">Built by Team Chaos Theory</p>
</div>
"""


def make_theme():
    """Dark theme matching the CSS; falls back to a plain theme if a key is unsupported."""
    import gradio as gr

    try:
        return gr.themes.Base(
            primary_hue="amber",
            neutral_hue="slate",
            font=[gr.themes.GoogleFont("Manrope"), "system-ui", "sans-serif"],
        ).set(
            body_background_fill="transparent",
            body_background_fill_dark="transparent",
            body_text_color="#eaf2ff",
            body_text_color_dark="#eaf2ff",
            block_background_fill="rgba(10,16,30,0.78)",
            block_background_fill_dark="rgba(10,16,30,0.78)",
            block_border_color="rgba(200,225,255,0.12)",
            block_border_color_dark="rgba(200,225,255,0.12)",
            input_background_fill="rgba(6,10,18,0.80)",
            input_background_fill_dark="rgba(6,10,18,0.80)",
            button_primary_background_fill="#ffc95c",
            button_primary_background_fill_dark="#ffc95c",
            button_primary_text_color="#1a1206",
            button_primary_text_color_dark="#1a1206",
        )
    except Exception:
        return gr.themes.Base()