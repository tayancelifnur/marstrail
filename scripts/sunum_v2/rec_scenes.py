"""
Sunum videosu v2 için uygulamadan iki kısa sahne kaydeder (headless Edge + CDP, 1920×1080).

  A) Rota çiz: haritaya 5 nokta → Bitir → "Çizilen rota" kartı (engeller, zorluk, test edilmemiş rota uyarısı, yükseklik profili)
  B) Canlı yürüyüşte not pini: Planla → Yürüyüşü başlat (×300) → not yaz → 📍 Pin → "Pin bırakıldı" bildirimi

Çalıştır (PowerShell/cmd; Git Bash'te headless Edge sorun çıkarabilir):
    venv\\Scripts\\python scripts\\sunum_v2\\rec_scenes.py
Çıktı: docs/sunum/img/v2_rec/{A,B}/*.jpg + frames.json (zaman damgaları ve işaretler; git'e girmez)

Neden ekran kaydı programla: Elle kayıtta tıklama yerleri ve süreler her seferinde değişir. Burada kamera, tıklanan
coğrafi noktalar ve bekleme süreleri sabit; sahne aynı biçimde yeniden üretilebilir. Ek paket gerekmez (cdp.py).
"""
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cdp import Browser  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "sunum" / "img" / "v2_rec"
BASE, DELTA, TF = (77.45089, 18.44463), (77.40519, 18.44941), (77.40776, 18.45263)
# Üs → delta önü yönünde, kum alanının kuzeyinden geçen bir çizim (5 nokta, derece)
ROUTE = [(77.4478, 18.4432), (77.4370, 18.4405), (77.4255, 18.4452), (77.4140, 18.4470), (77.4075, 18.4515)]


class Rec:
    def __init__(self, b, name):
        self.b, self.dir = b, OUT / name
        self.dir.mkdir(parents=True, exist_ok=True)
        for f in self.dir.glob("*.jpg"):
            f.unlink()
        self.t0, self.frames, self.marks = time.time(), [], {}

    def hold(self, sec):
        end = time.time() + sec
        while time.time() < end:
            p = self.dir / f"{len(self.frames):04d}.jpg"
            p.write_bytes(self.b.shot(q=93))
            self.frames.append([round(time.time() - self.t0, 3), p.name])

    def mark(self, name):
        self.marks[name] = round(time.time() - self.t0, 3)

    def save(self):
        (self.dir / "frames.json").write_text(json.dumps({"frames": self.frames, "marks": self.marks,
                                                          "end": round(time.time() - self.t0, 3)}))
        print(self.dir.name, len(self.frames), "kare", round(time.time() - self.t0, 1), "sn", self.marks)


def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", "8811", "--directory", str(ROOT / "web")],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    b = Browser()
    try:
        b.cmd("Page.navigate", url="http://127.0.0.1:8811/index.html")
        b.wait("document.readyState === 'complete' && window.MarsTrail && MarsTrail.plan !== undefined", timeout=60)
        time.sleep(4)
        b.js("document.getElementById('jezeroBtn').click()")
        time.sleep(4)
        # Kamera: plan görünümüyle aynı (app.js flyToPlan: rota sınır küresi, uzaklık r·4,2, en az 3 km, eğim −50°)
        pts = ",".join(f"Cesium.Cartesian3.fromDegrees({lo},{la},0,MarsTrail.MARS)" for lo, la in (BASE, DELTA, TF))
        b.js(f"""(() => {{ MarsTrail.setAutoRotate(false); const s = Cesium.BoundingSphere.fromPoints([{pts}]);
              MarsTrail.viewer.camera.flyToBoundingSphere(s, {{offset: new Cesium.HeadingPitchRange(0, Cesium.Math.toRadians(-50),
              Math.max(3000, s.radius * 4.2)), duration: 0}}); }})()""")
        b.wait("MarsTrail.viewer.scene.globe.tilesLoaded", timeout=40)
        time.sleep(3)
        xy = [b.js(f"""(() => {{ const s = MarsTrail.viewer.scene, c = Cesium.Cartographic.fromDegrees({lo}, {la});
               const p = Cesium.Cartesian3.fromDegrees({lo}, {la}, s.globe.getHeight(c) || 0, MarsTrail.MARS);
               const f = Cesium.SceneTransforms.worldToWindowCoordinates || Cesium.SceneTransforms.wgs84ToWindowCoordinates;
               const w = f(s, p); return [w.x, w.y]; }})()""") for lo, la in ROUTE]

        A = Rec(b, "A")
        A.hold(0.5)
        b.js("document.getElementById('routeBtn').click()")
        A.hold(0.5)
        for x, y in xy:
            b.click(x, y)
            A.hold(0.42)
        A.mark("bitir")
        b.js("document.getElementById('routeFabDone').click()")
        A.hold(3.0)
        A.save()

        b.js("document.getElementById('routeClearBtn').click()")
        time.sleep(0.5)
        b.js("MarsTrail.hideDetail && MarsTrail.hideDetail()")
        b.js("document.getElementById('planBtn').click()")
        time.sleep(3)
        b.wait("MarsTrail.viewer.scene.globe.tilesLoaded", timeout=40)
        time.sleep(1)
        b.js("const s = document.getElementById('walkSpeed'); s.value = '300'; s.dispatchEvent(new Event('change'))")
        b.js("document.getElementById('walkBtn').click()")
        time.sleep(0.6)
        B = Rec(b, "B")
        B.hold(0.8)
        b.js("document.getElementById('walkNote').focus()")
        for part in ("Kum dalgası · ", "foto çekildi"):
            b.type(part)
            B.hold(0.35)
        B.mark("pin")
        b.js("document.getElementById('walkNoteBtn').click()")
        B.hold(2.6)
        B.save()
    finally:
        b.close()
        srv.terminate()


if __name__ == "__main__":
    main()
