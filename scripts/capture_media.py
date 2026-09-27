# /// script
# dependencies = ["playwright"]
# ///
"""
Captures the README screenshots and walkthrough GIF.
Builds the React app, serves it on a loopback port, drives the
real flow in headless Chromium, and writes to docs/media/.

Run from the repo root (needs npm, ffmpeg, and internet for Leaflet and map tiles):
    uv run --with playwright playwright install chromium   # first time only
    uv run scripts/capture_media.py

Fails on any page error or missing screen, so a UI change cannot leave
stale media behind silently.
"""

import functools
import shutil
import subprocess
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
OUT_DIR = ROOT / "docs" / "media"
TIMEOUT_MS = 60_000
GIF_WIDTH = 960

# Headless screenshots have no mouse pointer, so the GIF draws its own.
CURSOR_JS = """() => {
  const c = document.createElement('div');
  c.id = 'rec-cursor';
  c.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24"><path d="M4 2l16 10-7 1.6L9.4 21z" '
    + 'fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
  c.style.cssText = 'position:fixed;left:0;top:0;z-index:2147483647;pointer-events:none';
  document.body.appendChild(c);
}"""


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve(directory):
    handler = functools.partial(QuietHandler, directory=str(directory))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def url(server, path="/"):
    return f"http://127.0.0.1:{server.server_address[1]}{path}"


class Recorder:
    """Screenshots the page as GIF frames, each with its own display time,
    so slow waits can be time-lapsed and key screens held."""

    def __init__(self, page, frame_dir):
        self.page, self.dir = page, frame_dir
        self.frames = []  # (png path, seconds shown)
        self.x, self.y = 640, 560
        page.evaluate(CURSOR_JS)
        self._place(self.x, self.y)

    def _place(self, x, y):
        # The arrow's tip sits at (4, 2) inside its 24px box.
        self.page.evaluate(f"document.getElementById('rec-cursor').style.transform = 'translate({x - 4}px, {y - 2}px)'")

    def shot(self, ms):
        path = self.dir / f"{len(self.frames):04d}.png"
        self.page.screenshot(path=path)
        self.frames.append((path, ms / 1000))

    def still(self, name):
        cursor = "document.getElementById('rec-cursor').style.visibility"
        self.page.evaluate(f"{cursor} = 'hidden'")
        self.page.screenshot(path=OUT_DIR / name)
        self.page.evaluate(f"{cursor} = ''")

    def move_to(self, locator, steps=8):
        locator.wait_for(state="attached")  # map labels are zero-width markers
        box = locator.bounding_box()
        tx, ty = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        for i in range(1, steps + 1):
            t = i / steps
            t = t * t * (3 - 2 * t)  # ease in and out
            self._place(self.x + (tx - self.x) * t, self.y + (ty - self.y) * t)
            self.shot(35)
        self.x, self.y = tx, ty
        self.shot(150)

    def click(self, locator, hold_ms=500):
        # A mouse click at the cursor, so map labels (pointer-events: none)
        # hit the county polygon underneath like a real click would.
        self.move_to(locator)
        self.page.mouse.click(self.x, self.y)
        self.page.wait_for_timeout(250)
        self.shot(hold_ms)

    def scroll_into_top(self, locator, steps=12):
        """Smoothly scrolls the nearest scrollable ancestor until locator is near its top."""
        handle = locator.element_handle()
        for i in range(1, steps + 1):
            handle.evaluate("""(el, t) => {
              let p = el.parentElement;
              while (p && !(p.scrollHeight > p.clientHeight && getComputedStyle(p).overflowY !== 'visible')) p = p.parentElement;
              if (!p) throw new Error('no scrollable ancestor');
              if (p.dataset.recStart === undefined) {
                p.dataset.recStart = p.scrollTop;
                p.dataset.recEnd = p.scrollTop + el.getBoundingClientRect().top - p.getBoundingClientRect().top - 16;
              }
              const s = +p.dataset.recStart, e = +p.dataset.recEnd, k = t * t * (3 - 2 * t);
              p.scrollTop = s + (e - s) * k;
            }""", i / steps)
            self.shot(40)

    def write_gif(self, out):
        listing = self.dir / "frames.txt"
        lines = [f"file '{p.name}'\nduration {s:.3f}" for p, s in self.frames]
        # The concat demuxer ignores the last duration unless the file repeats.
        lines.append(f"file '{self.frames[-1][0].name}'")
        listing.write_text("\n".join(lines), encoding="utf-8")
        palette = (f"scale={GIF_WIDTH}:-1:flags=lanczos,split[a][b];"
                   "[a]palettegen=max_colors=128:stats_mode=diff[p];"
                   "[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                        "-i", str(listing), "-vf", palette, "-fps_mode", "vfr", str(out)], check=True)


def capture(app, frame_dir):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800}, device_scale_factor=2)
        page.set_default_timeout(TIMEOUT_MS)
        page.on("pageerror", lambda e: errors.append(str(e)))

        page.goto(url(app))
        open_app = page.get_by_role("button", name="Open the App").first
        open_app.wait_for()
        page.wait_for_timeout(1500)  # let the entry animations finish
        rec = Recorder(page, frame_dir)
        rec.still("landing.png")
        rec.shot(2500)

        rec.click(open_app, hold_ms=300)
        kern = page.locator(".leaflet-marker-pane div", has_text="Kern").last
        kern.wait_for(state="attached")
        page.wait_for_load_state("networkidle")  # map tiles
        rec.shot(2000)

        rec.click(kern, hold_ms=300)
        page.get_by_text("Kern County", exact=True).wait_for()
        page.wait_for_timeout(1200)  # sheet slide-in and map pan
        page.wait_for_load_state("networkidle")
        rec.still("county.png")
        rec.shot(3000)

        rec.scroll_into_top(page.get_by_text("Two-Phase Risk Index", exact=True).last)
        rec.shot(3000)

        rec.click(page.get_by_role("button", name="Clinics"), hold_ms=300)
        page.get_by_text("Nearby medical facilities", exact=False).wait_for()
        page.wait_for_timeout(800)
        rec.still("breakdown.png")
        rec.shot(3000)
        browser.close()

    assert not errors, f"page errors during capture: {errors}"
    rec.write_gif(OUT_DIR / "walkthrough.gif")


if __name__ == "__main__":
    for tool in ("ffmpeg", "npm"):
        if not shutil.which(tool):
            raise SystemExit(f"{tool} is not on PATH.")
    subprocess.run([shutil.which("npm"), "run", "build"], cwd=FRONTEND, check=True, stdout=subprocess.DEVNULL)
    app = serve(FRONTEND / "build")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            capture(app, Path(tmp))
    finally:
        app.shutdown()
    for f in sorted(OUT_DIR.iterdir()):
        print(f"{f.relative_to(ROOT)}  {f.stat().st_size // 1024} KB")
