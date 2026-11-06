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

"""Visual layer for LiteGen and the OPAL GARDEN design system.

The interface keeps the existing Gradio generation flow while swapping in a warm,
editorial, botanical palette with a fixed photographic mosaic background.

Exports:
    HEAD        -> fonts, pass as head=
    CSS         -> page styles, pass as css=
    HERO_HTML   -> branded hero + fixed local mosaic, render with gr.HTML(HERO_HTML)
    make_theme()-> Gradio theme override, pass as theme=
The Generate button must keep elem_id="flicker-generate" for callback compatibility.
"""

import base64
import io
import os

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet">'
)

# ---------------------------------------------------------------------------
# Fixed mosaic from local gallery assets
# ---------------------------------------------------------------------------
GALLERY_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "gallery"
)

_SPANS = [
    (2, 2), (1, 1), (1, 2), (2, 1), (1, 1), (1, 2),
    (2, 2), (1, 1), (2, 1), (1, 1), (1, 2), (1, 1),
]


def _thumb_data_uri(path, max_side=720):
    from PIL import Image

    with Image.open(path) as im:
        im = im.convert("RGB")
        im.thumbnail((max_side, max_side))
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=72, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def mosaic_html(max_images=14):
    """Build a fixed local-image mosaic from assets/gallery."""
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
    for i in range(max(18, len(uris) * 2)):
        cs, rs = _SPANS[i % len(_SPANS)]
        tiles.append(
            f'<div class="opal-tile" style="grid-column:span {cs};grid-row:span {rs};">'
            f'<img src="{uris[i % len(uris)]}" alt="" loading="lazy" decoding="async"></div>'
        )
    return '<div id="opal-mosaic" aria-hidden="true">' + "".join(tiles) + "</div>"


def side_gallery_html(side="left"):
    """Build static side image columns from the local gallery."""
    if not os.path.isdir(GALLERY_DIR):
        return ""
    files = sorted(
        f for f in os.listdir(GALLERY_DIR)
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
    )
    if not files:
        return ""
    uris = []
    for f in files:
        try:
            uris.append(_thumb_data_uri(os.path.join(GALLERY_DIR, f)))
        except Exception:
            continue
    if not uris:
        return ""

    selected = uris[:10]
    if side == "left":
        markup = [
            '<div class="flicker-side-gallery left" aria-hidden="true">',
            f'<div class="side-tile tall"><img src="{selected[0]}" alt="" loading="lazy" decoding="async"></div>' if len(selected) > 0 else '',
            f'<div class="side-tile"><img src="{selected[1]}" alt="" loading="lazy" decoding="async"></div>' if len(selected) > 1 else '',
            f'<div class="side-tile"><img src="{selected[2]}" alt="" loading="lazy" decoding="async"></div>' if len(selected) > 2 else '',
            f'<div class="side-tile"><img src="{selected[3]}" alt="" loading="lazy" decoding="async"></div>' if len(selected) > 3 else '',
            f'<div class="side-tile wide"><img src="{selected[4]}" alt="" loading="lazy" decoding="async"></div>' if len(selected) > 4 else '',
            '</div>'
        ]
    else:
        markup = [
            '<div class="flicker-side-gallery right" aria-hidden="true">',
            f'<div class="side-tile"><img src="{selected[5]}" alt="" loading="lazy" decoding="async"></div>' if len(selected) > 5 else '',
            f'<div class="side-tile tall"><img src="{selected[6]}" alt="" loading="lazy" decoding="async"></div>' if len(selected) > 6 else '',
            f'<div class="side-tile"><img src="{selected[7]}" alt="" loading="lazy" decoding="async"></div>' if len(selected) > 7 else '',
            f'<div class="side-tile wide"><img src="{selected[8]}" alt="" loading="lazy" decoding="async"></div>' if len(selected) > 8 else '',
            f'<div class="side-tile"><img src="{selected[9]}" alt="" loading="lazy" decoding="async"></div>' if len(selected) > 9 else '',
            '</div>'
        ]
    return ''.join(markup)


MOSAIC = mosaic_html()
HEAD = FONTS

CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@600;700;800&family=Inter:wght@400;500;600;700;800&display=swap');

:root {
  --page-bg: #641C32;
  --page-bg-deep: #421222;
  --surface: rgba(250, 247, 241, 0.94);
  --surface-soft: rgba(250, 247, 241, 0.12);
  --surface-strong: rgba(250, 247, 241, 0.2);
  --border: rgba(100, 28, 50, 0.18);
  --border-strong: rgba(100, 28, 50, 0.3);
  --text: #302622;
  --text-primary: #302622;
  --text-secondary: #641C32;
  --text-muted: #68565A;
  --text-soft: rgba(48, 38, 34, 0.76);
  --text-muted-soft: rgba(48, 38, 34, 0.58);
  --warm-cream: #FAF7F1;
  --warm-cream-soft: rgba(250,247,241,0.74);
  --peach: #F3C9B5;
  --apricot: #A3AD91;
  --rose: #641C32;
  --shadow: rgba(48, 38, 34, 0.2);
  --input-bg: rgba(250,247,241,0.9);
  --input-border: rgba(100,28,50,0.2);

}

html, body {
  background: linear-gradient(135deg, #826860 0%, #735c53 30%, #5c4742 100%) !important;
  color: var(--text) !important;
}

body {
  min-height: 100vh;
  position: relative;
  overflow-x: hidden;
}

body::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  opacity: 0.08;
  background-image:
    linear-gradient(rgba(255,255,255,0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.06) 1px, transparent 1px);
  background-size: 18px 18px;
}

#flicker-shell {
  display: grid !important;
  grid-template-columns: minmax(120px, 0.9fr) minmax(0, 4.4fr) minmax(120px, 0.9fr);
  gap: 18px;
  align-items: start;
  width: min(100%, 1280px);
  max-width: 1280px;
  margin: 0 auto;
}

#flicker-shell > div {
  min-width: 0;
  width: 100%;
}

#opal-mosaic {
  position: relative;
  z-index: 0;
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  grid-auto-rows: minmax(80px, 11.5vh);
  grid-auto-flow: dense;
  gap: 8px;
  padding: 10px;
  width: min(100%, 1200px);
  height: clamp(350px, 42vh, 470px);
  margin: 6px auto 0;
  border-radius: 28px;
  overflow: hidden;
  pointer-events: none;
  background: rgba(255, 248, 242, 0.12);
  border: 1px solid rgba(255,255,255,0.12);
  box-shadow: 0 28px 52px rgba(51, 35, 31, 0.15), 0 0 0 1px rgba(255,255,255,0.04);
}

#opal-mosaic::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, rgba(74,56,52,0.20) 0%, rgba(74,56,52,0.08) 34%, rgba(74,56,52,0.04) 100%);
}

.opal-tile {
  position: relative;
  overflow: hidden;
  border-radius: 18px;
  border: 1px solid rgba(255,255,255,0.14);
  box-shadow: 0 14px 30px rgba(38, 27, 23, 0.14);
  background: rgba(255,255,255,0.08);
}

.opal-tile img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transform: scale(1.02);
  filter: saturate(0.85) contrast(1.06) brightness(0.98);
}

.flicker-side-gallery {
  position: relative;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-auto-rows: minmax(90px, 1fr);
  gap: 10px;
  width: 100%;
  max-width: 210px;
  margin: 0 auto;
  align-content: start;
  padding-top: 8px;
  opacity: 0.92;
}

.flicker-side-gallery .side-tile {
  overflow: hidden;
  border-radius: 18px;
  border: 1px solid rgba(255,255,255,0.12);
  box-shadow: 0 10px 22px rgba(46, 33, 29, 0.12);
  background: rgba(255,255,255,0.08);
  max-width: 100%;
}

.flicker-side-gallery .side-tile.tall { grid-row: span 2; }
.flicker-side-gallery .side-tile.wide { grid-column: span 2; }

.flicker-side-gallery .side-tile img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  filter: saturate(0.86) contrast(1.05) brightness(0.96);
}

.gradio-container,
.gradio-app, .gradio-container .main, .gradio-container .contain {
  background: transparent !important;
}

.gradio-container {
  position: relative;
  z-index: 2;
  max-width: 1500px !important;
  padding: 12px 18px 32px !important;
  font-family: 'Inter', sans-serif !important;
  color: var(--text) !important;
}

.gradio-container .row {
  gap: 18px !important;
  margin-top: 0 !important;
  align-items: stretch !important;
}

.gradio-container .form {
  padding: 0 !important;
}

.gradio-container .block,
.gradio-container .form,
.gradio-container .panel,
.gradio-container .accordion {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 20px !important;
  box-shadow: 0 18px 30px rgba(47, 35, 31, 0.12) !important;
  backdrop-filter: blur(20px) saturate(1.08);
  -webkit-backdrop-filter: blur(20px) saturate(1.08);
}

.gradio-container .block {
  padding: 18px 18px 14px !important;
}

.gradio-container .form .block,
.gradio-container .accordion .block,
.gradio-container .accordion .panel {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

.opal-header {
  position: relative;
  z-index: 2;
  max-width: 1200px;
  margin: 8px auto 12px;
  padding: 24px 16px 8px;
  text-align: center;
}

.opal-header::before {
  content: "";
  position: absolute;
  inset: 10% 18% 8% 18%;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255,255,255,0.16) 0%, rgba(233, 161, 168, 0.12) 32%, transparent 72%);
  filter: blur(26px);
  pointer-events: none;
}

.opal-header .eyebrow {
  display: inline-block;
  margin-bottom: 10px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255,255,255,0.12);
  color: #f4d2b4;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.22em;
  text-transform: uppercase;
}

.opal-header h1 {
  position: relative;
  margin: 0;
  font-family: 'Cormorant Garamond', Georgia, serif;
  font-weight: 700;
  font-size: clamp(54px, 7vw, 120px);
  line-height: 0.84;
  letter-spacing: -0.05em;
  color: #f9f0ea;
  text-shadow: 0 0 14px rgba(255,255,255,0.16), 0 0 30px rgba(247, 240, 232, 0.18), 0 0 42px rgba(201, 142, 120, 0.12);
}

.opal-header .subtitle {
  position: relative;
  margin: 10px auto 0;
  max-width: 660px;
  font-size: 13px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(247, 240, 232, 0.8);
}

.gradio-container textarea,
.gradio-container input:not([type="checkbox"]):not([type="radio"]),
.gradio-container select {
  background: rgba(255,255,255,0.24) !important;
  color: var(--text-primary) !important;
  border: 1px solid rgba(122, 97, 90, 0.32) !important;
  border-radius: 12px !important;
  font-family: 'Inter', sans-serif !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.12);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.gradio-container textarea {
  min-height: 144px !important;
  padding: 16px 14px !important;
  font-size: 17px !important;
  line-height: 1.5 !important;
  color: var(--text-primary) !important;
}

.gradio-container textarea::selection,
.gradio-container input::selection,
.gradio-container select::selection {
  background: rgba(233, 161, 168, 0.35);
  color: #2f201d;
}

.gradio-container input::placeholder,
.gradio-container textarea::placeholder {
  color: rgba(47, 32, 29, 0.8) !important;
  text-shadow: none !important;
}

.gradio-container textarea:focus,
.gradio-container input:focus,
.gradio-container select:focus {
  border-color: rgba(233, 161, 168, 0.8) !important;
  box-shadow: 0 0 0 3px rgba(233, 161, 168, 0.16), 0 0 18px rgba(233, 161, 168, 0.08) !important;
  outline: none !important;
}

.gradio-container label,
.gradio-container .label-wrap,
.gradio-container span[data-testid="block-info"],
.gradio-container .checkbox-container,
.gradio-container .markdown,
.gradio-container .markdown p,
.gradio-container .markdown li,
.gradio-container .json,
.gradio-container .gr-textbox,
.gradio-container .gr-dropdown,
.gradio-container .gr-number {
  color: var(--text-primary) !important;
  font-weight: 600 !important;
}

.gradio-container .checkbox-container label,
.gradio-container .checkbox-container span,
.gradio-container .checkbox-container * {
  color: var(--text-primary) !important;
}

#flicker-generate, .gradio-container button.primary {
  width: 100%;
  background: linear-gradient(135deg, #eec6b5 0%, #f1d29c 100%) !important;
  color: #352726 !important;
  border: none !important;
  border-radius: 14px !important;
  font-weight: 800 !important;
  font-size: 16px !important;
  letter-spacing: 0.01em;
  box-shadow: 0 16px 28px rgba(77, 58, 49, 0.2), 0 0 18px rgba(241, 210, 156, 0.18);
  transition: transform 0.2s ease, box-shadow 0.2s ease, filter 0.2s ease;
}

#flicker-generate:hover, .gradio-container button.primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 18px 30px rgba(77, 58, 49, 0.26), 0 0 22px rgba(241, 210, 156, 0.2);
  filter: saturate(1.02) brightness(1.02);
}

#flicker-generate:active, .gradio-container button.primary:active {
  transform: translateY(0);
  filter: brightness(0.98);
}

.gradio-container .examples,
.gradio-container .example-set,
.gradio-container .example-item {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.gradio-container .example-item {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  max-width: 100%;
  min-height: 36px;
  padding: 8px 14px !important;
  border: 1px solid rgba(118, 87, 107, 0.18) !important;
  background: rgba(255,255,255,0.18) !important;
  color: var(--text-primary) !important;
  border-radius: 999px !important;
  font-size: 13px !important;
  line-height: 1.3 !important;
  font-weight: 700 !important;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  max-width: 220px;
  text-shadow: 0 0 8px rgba(246, 214, 175, 0.08);
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease, color 0.2s ease;
}

.gradio-container .example-item:hover {
  border-color: rgba(133, 101, 88, 0.7) !important;
  background: rgba(255,255,255,0.28) !important;
  color: var(--text-primary) !important;
  transform: translateY(-1px);
  box-shadow: 0 0 0 1px rgba(255,255,255,0.06), 0 0 18px rgba(243, 204, 142, 0.14);
  text-shadow: 0 0 10px rgba(243, 204, 142, 0.1), 0 0 12px rgba(233, 161, 168, 0.04);
}

.gradio-container .accordion {
  border: 1px solid var(--border) !important;
  background: rgba(255,255,255,0.08) !important;
}

.gradio-container .progress {
  background: rgba(255,255,255,0.1) !important;
  border-radius: 999px !important;
}

.gradio-container .progress-bar {
  background: linear-gradient(135deg, #eab6ac 0%, #f1d09d 100%) !important;
  border-radius: 999px !important;
}

.gradio-container ::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}

.gradio-container ::-webkit-scrollbar-thumb {
  background: rgba(255,255,255,0.2);
  border-radius: 999px;
}

.gradio-container ::-webkit-scrollbar-track {
  background: rgba(255,255,255,0.04);
}

footer,
.gradio-container footer,
.gradio-footer,
.footer {
  display: none !important;
  visibility: hidden !important;
  height: 0 !important;
  overflow: hidden !important;
  margin: 0 !important;
  padding: 0 !important;
}

@media (max-width: 1100px) {
  #flicker-shell {
    grid-template-columns: minmax(120px, 0.7fr) minmax(0, 2.2fr) minmax(120px, 0.7fr);
  }
}

@media (max-width: 900px) {
  #flicker-shell {
    grid-template-columns: 1fr;
    width: 100%;
    max-width: 100%;
    gap: 14px;
  }

  .flicker-side-gallery {
    display: none !important;
  }

  .gradio-container {
    padding: 8px 12px 24px !important;
    max-width: 100% !important;
  }

  .gradio-container .row {
    flex-direction: column !important;
    width: 100% !important;
  }

  #opal-mosaic {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    grid-auto-rows: minmax(72px, 14vh);
    gap: 6px;
    padding: 8px;
    width: 100%;
    height: clamp(220px, 26vw, 320px);
    border-radius: 22px;
  }

  .opal-header {
    padding: 18px 8px 8px;
  }

  .opal-header h1 {
    font-size: clamp(42px, 12vw, 72px);
  }

  .opal-header .subtitle {
    font-size: 11px;
    letter-spacing: 0.08em;
  }
}

@media (max-width: 768px) {
  html, body {
    overflow-x: hidden;
  }

  .gradio-container {
    padding: 8px 10px 20px !important;
  }

  .gradio-container .block {
    padding: 14px 12px 10px !important;
  }

  .gradio-container textarea,
  .gradio-container input:not([type="checkbox"]):not([type="radio"]),
  .gradio-container select {
    width: 100% !important;
    min-height: 48px !important;
    font-size: 15px !important;
  }

  .gradio-container textarea {
    min-height: 120px !important;
  }

  #flicker-generate, .gradio-container button.primary {
    min-height: 48px !important;
    font-size: 15px !important;
  }

  .gradio-container .example-set,
  .gradio-container .examples {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .gradio-container .example-item {
    flex: 1 1 140px;
    max-width: none;
    min-height: 34px;
    white-space: normal;
    text-overflow: clip;
    padding: 8px 12px !important;
    font-size: 12px !important;
    line-height: 1.35 !important;
  }

  .gradio-container .accordion {
    width: 100%;
  }

  .gradio-container .accordion .label-wrap {
    min-height: 44px;
    display: flex;
    align-items: center;
  }

  .gradio-container .progress,
  .gradio-container .progress-bar {
    min-width: 0;
  }
}

@media (max-width: 430px) {
  .gradio-container {
    padding: 6px 8px 18px !important;
  }

  .opal-header {
    padding-top: 10px;
  }

  .opal-header h1 {
    font-size: clamp(34px, 14vw, 52px);
    line-height: 0.9;
  }

  .opal-header .subtitle {
    font-size: 10px;
    letter-spacing: 0.06em;
  }

  #opal-mosaic {
    height: clamp(180px, 28vw, 220px);
    border-radius: 18px;
  }

  .gradio-container .block {
    border-radius: 16px !important;
  }
}

@media (max-width: 390px) {
  .gradio-container {
    padding: 4px 6px 16px !important;
  }

  .gradio-container label,
  .gradio-container .label-wrap,
  .gradio-container .checkbox-container,
  .gradio-container span[data-testid="block-info"] {
    font-size: 13px !important;
  }

  .gradio-container .example-item {
    font-size: 11.5px !important;
    flex-basis: 100%;
  }
}

@media (max-width: 320px) {
  .opal-header .subtitle {
    letter-spacing: 0.04em;
  }

  .gradio-container textarea,
  .gradio-container input:not([type="checkbox"]):not([type="radio"]),
  .gradio-container select {
    font-size: 14px !important;
  }
}

/* FLICKER — glowing interactive buttons */

.gradio-container button {
  border-radius: 14px !important;
  transition: all 0.25s ease !important;
}

#flicker-generate,
.gradio-container button.primary {
  background: linear-gradient(
    135deg,
    #F3C9B5,
    #A3AD91
  ) !important;

  color: #302622 !important;
  border: 1px solid rgba(243,201,181,0.7) !important;

  box-shadow:
    0 0 10px rgba(243,201,181,0.35),
    0 0 25px rgba(100,28,50,0.25),
    0 8px 22px rgba(48,38,34,0.2) !important;
}

#flicker-generate:hover,
.gradio-container button.primary:hover {
  transform: translateY(-3px) !important;

  box-shadow:
    0 0 14px rgba(243,201,181,0.65),
    0 0 32px rgba(163,173,145,0.4),
    0 12px 28px rgba(48,38,34,0.25) !important;
}

.gradio-container button:not(.primary):hover {
  border-color: #F3C9B5 !important;
  box-shadow: 0 0 14px rgba(243,201,181,0.35) !important;
  transform: translateY(-2px);
}

"""

SIDE_GALLERY_LEFT = """
<div class="flicker-side-gallery left" aria-hidden="true">
  <div class="side-tile tall"><img src="{left_1}" alt="" loading="lazy" decoding="async"></div>
  <div class="side-tile"><img src="{left_2}" alt="" loading="lazy" decoding="async"></div>
  <div class="side-tile"><img src="{left_3}" alt="" loading="lazy" decoding="async"></div>
  <div class="side-tile"><img src="{left_4}" alt="" loading="lazy" decoding="async"></div>
  <div class="side-tile wide"><img src="{left_5}" alt="" loading="lazy" decoding="async"></div>
</div>
""".format(
    left_1=_thumb_data_uri(os.path.join(GALLERY_DIR, sorted([f for f in os.listdir(GALLERY_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))])[0])) if os.path.isdir(GALLERY_DIR) and sorted([f for f in os.listdir(GALLERY_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]) else '',
    left_2=_thumb_data_uri(os.path.join(GALLERY_DIR, sorted([f for f in os.listdir(GALLERY_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))])[1])) if os.path.isdir(GALLERY_DIR) and len(sorted([f for f in os.listdir(GALLERY_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))])) > 1 else '',
    left_3=_thumb_data_uri(os.path.join(GALLERY_DIR, sorted([f for f in os.listdir(GALLERY_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))])[2])) if os.path.isdir(GALLERY_DIR) and len(sorted([f for f in os.listdir(GALLERY_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))])) > 2 else '',
    left_4=_thumb_data_uri(os.path.join(GALLERY_DIR, sorted([f for f in os.listdir(GALLERY_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))])[3])) if os.path.isdir(GALLERY_DIR) and len(sorted([f for f in os.listdir(GALLERY_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))])) > 3 else '',
    left_5=_thumb_data_uri(os.path.join(GALLERY_DIR, sorted([f for f in os.listdir(GALLERY_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))])[4])) if os.path.isdir(GALLERY_DIR) and len(sorted([f for f in os.listdir(GALLERY_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))])) > 4 else '',
)

SIDE_GALLERY_RIGHT = """
<div class="flicker-side-gallery right" aria-hidden="true">
  <div class="side-tile"><img src="{right_1}" alt="" loading="lazy" decoding="async"></div>
  <div class="side-tile tall"><img src="{right_2}" alt="" loading="lazy" decoding="async"></div>
  <div class="side-tile"><img src="{right_3}" alt="" loading="lazy" decoding="async"></div>
  <div class="side-tile wide"><img src="{right_4}" alt="" loading="lazy" decoding="async"></div>
  <div class="side-tile"><img src="{right_5}" alt="" loading="lazy" decoding="async"></div>
</div>
""".format(
    right_1=_thumb_data_uri(os.path.join(GALLERY_DIR, sorted([f for f in os.listdir(GALLERY_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))])[5])) if os.path.isdir(GALLERY_DIR) and len(sorted([f for f in os.listdir(GALLERY_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))])) > 5 else '',
    right_2=_thumb_data_uri(os.path.join(GALLERY_DIR, sorted([f for f in os.listdir(GALLERY_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))])[6])) if os.path.isdir(GALLERY_DIR) and len(sorted([f for f in os.listdir(GALLERY_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))])) > 6 else '',
    right_3=_thumb_data_uri(os.path.join(GALLERY_DIR, sorted([f for f in os.listdir(GALLERY_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))])[7])) if os.path.isdir(GALLERY_DIR) and len(sorted([f for f in os.listdir(GALLERY_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))])) > 7 else '',
    right_4=_thumb_data_uri(os.path.join(GALLERY_DIR, sorted([f for f in os.listdir(GALLERY_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))])[8])) if os.path.isdir(GALLERY_DIR) and len(sorted([f for f in os.listdir(GALLERY_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))])) > 8 else '',
    right_5=_thumb_data_uri(os.path.join(GALLERY_DIR, sorted([f for f in os.listdir(GALLERY_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))])[9])) if os.path.isdir(GALLERY_DIR) and len(sorted([f for f in os.listdir(GALLERY_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))])) > 9 else '',
)

HERO_HTML = f"""
{MOSAIC}
<div class="opal-header">
  <div class="eyebrow">Flicker</div>
  <h1>Flicker</h1>
  <div class="subtitle">Creative prompt studio for cinematic image generation</div>
</div>
"""


def make_theme():
    """Warm editorial theme that preserves Gradio functionality and the OPAL GARDEN palette."""
    import gradio as gr

    try:
        return gr.themes.Base(
            primary_hue="pink",
            neutral_hue="stone",
            font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"],
        ).set(
            body_background_fill="#1C1917",
            body_background_fill_dark="#1C1917",
            body_text_color="#F5EDE6",
            body_text_color_dark="#F5EDE6",
            body_text_color_subdued="rgba(245, 237, 230, 0.72)",
            body_text_color_subdued_dark="rgba(245, 237, 230, 0.72)",
            block_background_fill="rgba(255,255,255,0.05)",
            block_background_fill_dark="rgba(255,255,255,0.05)",
            block_border_color="rgba(255,255,255,0.10)",
            block_border_color_dark="rgba(255,255,255,0.10)",
            block_border_width="1px",
            block_radius="20px",
            block_label_text_color="#F5EDE6",
            block_label_text_color_dark="#F5EDE6",
            input_background_fill="rgba(255,255,255,0.07)",
            input_background_fill_dark="rgba(255,255,255,0.07)",
            input_border_color="rgba(255,255,255,0.12)",
            input_border_color_dark="rgba(255,255,255,0.12)",
            input_radius="12px",
            checkbox_background_color_selected="#F4C07A",
            checkbox_background_color_selected_dark="#F4C07A",
            button_primary_background_fill="#E8A0AC",
            button_primary_background_fill_dark="#E8A0AC",
            button_primary_text_color="#2F201D",
            button_primary_text_color_dark="#2F201D",
            shadow_drop="0 18px 34px rgba(12,10,10,0.42)",
        )
    except Exception:
        return gr.themes.Base()