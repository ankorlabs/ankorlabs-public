#!/usr/bin/env python3
"""Make a Turf Pong video as an MP4 file (1080x1920, 30 fps, with sound).

Needs only Python 3 and Google Chrome (or Microsoft Edge / Chromium). Nothing to pip install.

    python3 make_video.py                          # today's game, 2 teams -> turf-pong-YYYY-MM-DD.mp4
    python3 make_video.py --teams 3 --out day.mp4
    python3 make_video.py --seed 2026-11-12        # the same seed always gives the same game

The last line printed is JSON, for example:
    {"ok": true, "file": "/abs/path/turf-pong-2026-11-12.mp4", "winner": "Sky", "seconds": 61.4,
     "teams": [{"name": "Butter", "share": 14}, {"name": "Sky", "share": 86}], "hasSound": true, ...}
On failure: {"ok": false, "error": "..."} and a non-zero exit code.
"""
import argparse, base64, datetime, json, os, re, shutil, socket, struct, subprocess, sys, tempfile, time
import urllib.parse, urllib.request

PAGE = "https://ankorlabs.com/turf-pong.html"
CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge",
]


def fail(msg, code=1):
    print(json.dumps({"ok": False, "error": msg}))
    sys.exit(code)


def find_chrome(explicit):
    for c in ([explicit] if explicit else []) + CHROME_CANDIDATES:
        path = c if os.path.isabs(c) else shutil.which(c)
        if path and os.path.exists(path):
            return path
    fail("Chrome not found. Install Google Chrome or pass --chrome PATH.")


class DevTools:
    """Tiny WebSocket client for Chrome's DevTools protocol (standard library only)."""

    def __init__(self, ws_url):
        u = urllib.parse.urlparse(ws_url)
        self.sock = socket.create_connection((u.hostname, u.port), timeout=60)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f"GET {u.path} HTTP/1.1\r\nHost: {u.hostname}:{u.port}\r\nUpgrade: websocket\r\n"
                           f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("DevTools handshake failed")
            head += chunk
        if b" 101 " not in head.split(b"\r\n", 1)[0]:
            raise ConnectionError("DevTools refused the connection")
        self.buf = bytearray(head.split(b"\r\n\r\n", 1)[1])
        self.next_id = 0

    def _read(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(1 << 20)
            if not chunk:
                raise ConnectionError("Chrome closed the connection")
            self.buf += chunk
        out = bytes(self.buf[:n]); del self.buf[:n]
        return out

    def _send(self, obj):
        data = json.dumps(obj).encode()
        n, mask = len(data), os.urandom(4)
        hdr = bytearray([0x81])
        if n < 126: hdr.append(0x80 | n)
        elif n < 65536: hdr += bytes([0x80 | 126]) + struct.pack(">H", n)
        else: hdr += bytes([0x80 | 127]) + struct.pack(">Q", n)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        self.sock.sendall(bytes(hdr) + mask + masked)

    def _recv(self):
        msg = b""
        while True:
            b1, b2 = self._read(2)
            op, n = b1 & 0x0F, b2 & 0x7F
            if n == 126: n = struct.unpack(">H", self._read(2))[0]
            elif n == 127: n = struct.unpack(">Q", self._read(8))[0]
            if b2 & 0x80: self._read(4)
            payload = self._read(n)
            if op == 8: raise ConnectionError("Chrome closed the connection")
            if op in (9, 10): continue
            msg += payload
            if b1 & 0x80: return json.loads(msg)

    def evaluate(self, expression):
        self.next_id += 1
        my_id = self.next_id
        self._send({"id": my_id, "method": "Runtime.evaluate", "params": {"expression": expression, "returnByValue": True}})
        while True:
            m = self._recv()
            if m.get("id") == my_id:
                return m.get("result", {}).get("result", {}).get("value")


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    return port


def main():
    ap = argparse.ArgumentParser(description="Make a Turf Pong MP4 (1080x1920, with sound).")
    ap.add_argument("--teams", type=int, default=2, choices=[2, 3, 4])
    ap.add_argument("--speed", type=int, default=1, choices=[1, 2, 4], help="game speed (1 = about a minute)")
    ap.add_argument("--seed", default=datetime.date.today().isoformat(), help="same seed = same game (default: today's date)")
    ap.add_argument("--no-powerups", action="store_true")
    ap.add_argument("--out", help="output .mp4 path (default: turf-pong-<seed>.mp4 in the current folder)")
    ap.add_argument("--chrome", help="path to Chrome/Edge/Chromium if it isn't found automatically")
    ap.add_argument("--page", default=PAGE)
    ap.add_argument("--timeout", type=int, default=900, help="seconds to wait before giving up (default 900)")
    a = ap.parse_args()

    q = {"agent": "1", "download": "0", "teams": a.teams, "speed": a.speed, "seed": a.seed}
    if a.no_powerups:
        q["powerups"] = "0"
    url = a.page + "?" + urllib.parse.urlencode(q)
    out = os.path.abspath(a.out or re.sub(r"[^\w.-]+", "-", f"turf-pong-{a.seed}") + ".mp4")

    chrome, port = find_chrome(a.chrome), free_port()
    profile = tempfile.mkdtemp(prefix="turf-pong-chrome-")
    proc = subprocess.Popen([chrome, "--headless=new", f"--remote-debugging-port={port}", f"--user-data-dir={profile}",
                             "--no-first-run", "--no-default-browser-check", "--autoplay-policy=no-user-gesture-required",
                             "--window-size=1080,1920", url],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        ws_url, deadline = None, time.time() + 30
        while not ws_url and time.time() < deadline:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2) as r:
                    pages = [t for t in json.load(r) if t.get("type") == "page" and "turf-pong" in t.get("url", "")]
                ws_url = pages[0]["webSocketDebuggerUrl"] if pages else None
            except Exception:
                pass
            if not ws_url:
                time.sleep(0.5)
        if not ws_url:
            fail("Chrome didn't start in time.")
        dt = DevTools(ws_url)
        deadline = time.time() + a.timeout
        status = ""
        while time.time() < deadline:
            title = dt.evaluate("document.title") or ""
            if title in ("TURF-PONG-DONE", "TURF-PONG-FAILED"):
                break
            new = dt.evaluate("(document.getElementById('recMsg')||{}).textContent") or ""
            if new != status:
                status = new
                print(status, file=sys.stderr, flush=True)
            time.sleep(2)
        else:
            fail(f"Timed out after {a.timeout}s ({status})")
        raw = dt.evaluate("(document.getElementById('agent-result')||{}).textContent")
        if not raw:
            fail("The page finished without a result.")
        result = json.loads(raw)
        if not result.get("ok"):
            print(json.dumps(result)); sys.exit(1)
        with open(out, "wb") as f:
            f.write(base64.b64decode(result.pop("mp4Base64")))
        result.pop("filename", None)
        result["file"] = out
        print(json.dumps(result))
    finally:
        proc.terminate()
        try: proc.wait(timeout=10)
        except Exception: proc.kill()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    main()
