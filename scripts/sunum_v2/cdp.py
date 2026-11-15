"""Küçük CDP istemcisi (yalnız standart kütüphane): yerel Edge'i headless açar, sayfayı sürer, ekran görüntüsü alır."""
import base64, json, os, socket, struct, subprocess, tempfile, time, urllib.request
from pathlib import Path

EDGE = next(p for p in [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"] if Path(p).exists())


class WS:
    def __init__(self, url):
        assert url.startswith("ws://")
        hostport, path = url[5:].split("/", 1)
        host, port = hostport.split(":")
        self.s = socket.create_connection((host, int(port)))
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall((f"GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                        f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        resp = b""
        while b"\r\n\r\n" not in resp:
            resp += self.s.recv(4096)
        assert b" 101 " in resp.split(b"\r\n")[0], resp[:200]
        self.buf = resp.split(b"\r\n\r\n", 1)[1]

    def send(self, text):
        data = text.encode()
        hdr = bytes([0x81])
        n = len(data)
        if n < 126:
            hdr += bytes([0x80 | n])
        elif n < 65536:
            hdr += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            hdr += bytes([0x80 | 127]) + struct.pack(">Q", n)
        mask = os.urandom(4)
        self.s.sendall(hdr + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def _read(self, n):
        while len(self.buf) < n:
            chunk = self.s.recv(1 << 20)
            if not chunk:
                raise ConnectionError("ws kapandı")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def recv(self):
        msg = b""
        while True:
            b0, b1 = self._read(2)
            n = b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            payload = self._read(n)
            op = b0 & 0x0F
            if op == 8:
                raise ConnectionError("ws close")
            if op in (9, 10):
                continue
            msg += payload
            if b0 & 0x80:
                return msg.decode()


class Browser:
    def __init__(self, w=1920, h=1080, port=9333, headless=True):
        self.prof = tempfile.mkdtemp()
        args = [EDGE, f"--remote-debugging-port={port}", f"--user-data-dir={self.prof}", "--no-first-run",
                f"--window-size={w},{h}", "--hide-scrollbars", "--force-device-scale-factor=1", "--ignore-gpu-blocklist",
                "--enable-unsafe-swiftshader", "about:blank"]
        if headless:
            args.insert(1, "--headless=new")
        self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json"))
                page = next(t for t in tabs if t["type"] == "page")
                break
            except Exception:
                time.sleep(0.2)
        self.ws = WS(page["webSocketDebuggerUrl"])
        self.i = 0
        self.events = []
        self.cmd("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=1, mobile=False)
        self.cmd("Page.enable")
        self.cmd("Runtime.enable")

    def cmd(self, method, **params):
        self.i += 1
        my = self.i
        self.ws.send(json.dumps({"id": my, "method": method, "params": params}))
        while True:
            m = json.loads(self.ws.recv())
            if m.get("id") == my:
                if "error" in m:
                    raise RuntimeError(f"{method}: {m['error']}")
                return m.get("result", {})
            self.events.append(m)

    def js(self, expr, await_promise=False):
        r = self.cmd("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=await_promise)
        if "exceptionDetails" in r:
            raise RuntimeError(json.dumps(r["exceptionDetails"])[:500])
        return r.get("result", {}).get("value")

    def wait(self, expr, timeout=60, step=0.25):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self.js(expr):
                return True
            time.sleep(step)
        raise TimeoutError(expr)

    def shot(self, fmt="jpeg", q=92):
        d = self.cmd("Page.captureScreenshot", format=fmt, quality=q) if fmt == "jpeg" else self.cmd("Page.captureScreenshot", format=fmt)
        return base64.b64decode(d["data"])

    def click(self, x, y, double=False):
        for t in ("mouseMoved", "mousePressed", "mouseReleased"):
            self.cmd("Input.dispatchMouseEvent", type=t, x=x, y=y, button="left" if t != "mouseMoved" else "none", clickCount=1)
        if double:
            for t in ("mousePressed", "mouseReleased"):
                self.cmd("Input.dispatchMouseEvent", type=t, x=x, y=y, button="left", clickCount=2)

    def move(self, x, y):
        self.cmd("Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y)

    def type(self, text):
        self.cmd("Input.insertText", text=text)

    def close(self):
        try:
            self.cmd("Browser.close")
        except Exception:
            pass
        self.proc.wait(timeout=10)
