"""
BeamNG Head Tracker Bridge v2
- Serves phone.html over HTTP (open in Chrome on phone)
- WebSocket server for gyro data
- Forwards to OpenTrack UDP on localhost:4242
"""

import asyncio
import websockets
import socket
import struct
import json
import threading
import time
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

WS_PORT        = 5556
HTTP_PORT      = 5557
OPENTRACK_PORT = 4242
OPENTRACK_HOST = "127.0.0.1"
YAW_SCALE      = 1.0
PITCH_SCALE    = 1.0
ROLL_SCALE     = 0.5
SMOOTHING      = 0.65
SEND_HZ        = 100

class Tracker:
    def __init__(self):
        self.sy = self.sp = self.sr = 0.0
        self.yaw_off = self.pitch_off = self.roll_off = 0.0
        self.clients = 0
        self.pkt = 0

    def process(self, raw_yaw, raw_pitch, raw_roll):
        y = ((raw_yaw   - self.yaw_off   + 180) % 360 - 180) * YAW_SCALE
        p = ((raw_pitch - self.pitch_off + 180) % 360 - 180) * PITCH_SCALE
        r = ((raw_roll  - self.roll_off  + 180) % 360 - 180) * ROLL_SCALE
        s = SMOOTHING
        self.sy = s*self.sy + (1-s)*y
        self.sp = s*self.sp + (1-s)*p
        self.sr = s*self.sr + (1-s)*r
        self.pkt += 1

    def recenter(self, raw_yaw, raw_pitch, raw_roll):
        self.yaw_off   = raw_yaw
        self.pitch_off = raw_pitch
        self.roll_off  = raw_roll
        self.sy = self.sp = self.sr = 0.0
        print("\n  [Recentered]")

    def opentrack_packet(self):
        return struct.pack('<6d', 0.0, 0.0, 0.0, self.sy, self.sp, self.sr)

tracker = Tracker()

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

LOCAL_IP = get_local_ip()

# ── Phone page HTML (embedded so bridge.py is self-contained) ─────────────────
def make_phone_html(ip, ws_port):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>BeamNG Head Tracker</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0d0d0d;color:#e0e0e0;font-family:system-ui,sans-serif;
  min-height:100vh;display:flex;flex-direction:column;align-items:center;
  padding:20px;gap:14px}}
h1{{font-size:1.3rem;font-weight:700;color:#4fc3f7;text-align:center;margin-top:8px}}
.sub{{font-size:.75rem;color:#888;text-align:center;margin-top:-6px}}
.card{{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:14px;
  padding:16px;width:100%;max-width:400px}}
.card h2{{font-size:.7rem;text-transform:uppercase;letter-spacing:.1em;
  color:#666;margin-bottom:10px}}
.status-row{{display:flex;align-items:center;gap:8px;margin-top:10px}}
.dot{{width:10px;height:10px;border-radius:50%;background:#444;
  transition:background .3s;flex-shrink:0}}
.dot.ok{{background:#66bb6a;box-shadow:0 0 6px #66bb6a}}
.dot.warn{{background:#ffa726;box-shadow:0 0 6px #ffa726}}
.dot.err{{background:#ef5350;box-shadow:0 0 6px #ef5350}}
#status-text{{font-size:.85rem}}
.angles{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:4px}}
.abox{{background:#111;border-radius:8px;padding:10px 6px;text-align:center}}
.alabel{{font-size:.65rem;text-transform:uppercase;letter-spacing:.08em;color:#666;margin-bottom:4px}}
.aval{{font-size:1.1rem;font-weight:700;color:#4fc3f7;font-variant-numeric:tabular-nums}}
.viz{{width:100%;height:110px;background:#111;border-radius:10px;overflow:hidden;margin-top:8px}}
canvas{{width:100%;height:100%}}
button{{border:none;border-radius:8px;cursor:pointer;font-size:.95rem;
  font-weight:600;padding:12px 16px;transition:opacity .15s,transform .1s;width:100%}}
button:active{{transform:scale(.97)}}
.btn-go{{background:#4fc3f7;color:#000;margin-top:4px}}
.btn-rc{{background:#2a2a2a;color:#e0e0e0;border:1px solid #444;margin-top:8px}}
.srow{{display:flex;align-items:center;gap:10px;margin-top:12px}}
.srow label{{font-size:.8rem;color:#888;white-space:nowrap}}
input[type=range]{{flex:1;accent-color:#4fc3f7}}
#sv{{font-size:.8rem;color:#4fc3f7;min-width:28px;text-align:right}}
.note{{font-size:.72rem;color:#555;text-align:center;padding:0 8px}}
</style>
</head>
<body>
<h1>🎮 BeamNG Head Tracker</h1>
<p class="sub">Samsung S23+ gyroscope → PC</p>

<div class="card">
  <h2>Connection</h2>
  <!-- IP is pre-filled — no typing needed -->
  <p style="font-size:.8rem;color:#888;margin-bottom:10px">
    Connecting to: <strong style="color:#4fc3f7">{ip}:{ws_port}</strong>
  </p>
  <button class="btn-go" id="btn" onclick="start()">Start Tracking</button>
  <div class="status-row">
    <div class="dot" id="dot"></div>
    <span id="status-text">Tap Start to begin</span>
  </div>
</div>

<div class="card">
  <h2>Live Orientation</h2>
  <div class="angles">
    <div class="abox"><div class="alabel">Yaw</div><div class="aval" id="vy">0.0°</div></div>
    <div class="abox"><div class="alabel">Pitch</div><div class="aval" id="vp">0.0°</div></div>
    <div class="abox"><div class="alabel">Roll</div><div class="aval" id="vr">0.0°</div></div>
  </div>
  <div class="viz"><canvas id="c"></canvas></div>
</div>

<div class="card">
  <h2>Controls</h2>
  <button class="btn-rc" onclick="recenter()">⟳ Recenter View</button>
  <div class="srow">
    <label>Sensitivity</label>
    <input type="range" id="sens" min="0.3" max="3" step="0.1" value="1"
           oninput="sens=+this.value;document.getElementById('sv').textContent=sens.toFixed(1)+'×'">
    <span id="sv">1.0×</span>
  </div>
</div>

<p class="note">Keep this page open while playing. Both devices must be on the same Wi-Fi.</p>

<script>
const WS_URL = "ws://{ip}:{ws_port}";
let ws=null, yaw=0, pitch=0, roll=0, sens=1.0, pkt=0, interval=null;

const canvas=document.getElementById('c');
const ctx=canvas.getContext('2d');
function resize(){{canvas.width=canvas.offsetWidth;canvas.height=canvas.offsetHeight}}
resize(); window.addEventListener('resize',resize);

function draw(){{
  const w=canvas.width,h=canvas.height,cx=w/2,cy=h/2;
  ctx.clearRect(0,0,w,h);
  const rr=roll*Math.PI/180, po=pitch*(h/90)*.5;
  ctx.save(); ctx.translate(cx,cy+po); ctx.rotate(rr);
  ctx.fillStyle='#1a3a5c'; ctx.fillRect(-w,-h,w*2,h);
  ctx.fillStyle='#2d1a0a'; ctx.fillRect(-w,0,w*2,h);
  ctx.strokeStyle='#4fc3f7'; ctx.lineWidth=2;
  ctx.beginPath(); ctx.moveTo(-w,0); ctx.lineTo(w,0); ctx.stroke();
  ctx.restore();
  ctx.strokeStyle='rgba(255,255,255,.6)'; ctx.lineWidth=1.5;
  ctx.beginPath();
  ctx.moveTo(cx-14,cy); ctx.lineTo(cx+14,cy);
  ctx.moveTo(cx,cy-14); ctx.lineTo(cx,cy+14);
  ctx.stroke();
  const yf=((yaw%360)+360)%360/360;
  ctx.fillStyle='#4fc3f7';
  ctx.beginPath(); ctx.arc(cx+(yf-.5)*w*.8,8,4,0,Math.PI*2); ctx.fill();
}}

function onOrient(e){{
  if(e.alpha===null)return;
  yaw  =-e.alpha*sens;
  pitch=-e.beta *sens;
  roll = e.gamma*sens;
  document.getElementById('vy').textContent=yaw.toFixed(1)+'°';
  document.getElementById('vp').textContent=pitch.toFixed(1)+'°';
  document.getElementById('vr').textContent=roll.toFixed(1)+'°';
  draw();
}}

function setStatus(level,msg){{
  document.getElementById('dot').className='dot '+level;
  document.getElementById('status-text').textContent=msg;
}}

function requestGyro(){{
  if(typeof DeviceOrientationEvent!=='undefined'&&
     typeof DeviceOrientationEvent.requestPermission==='function'){{
    DeviceOrientationEvent.requestPermission().then(s=>{{
      if(s==='granted'){{window.addEventListener('deviceorientation',onOrient,true);}}
      else setStatus('err','Gyro permission denied');
    }});
  }}else{{
    window.addEventListener('deviceorientationabsolute',onOrient,true);
    window.addEventListener('deviceorientation',onOrient,true);
  }}
}}

function start(){{
  requestGyro();
  setStatus('warn','Connecting...');
  document.getElementById('btn').disabled=true;
  document.getElementById('btn').textContent='Connecting...';

  ws=new WebSocket(WS_URL);
  ws.onopen=()=>{{
    setStatus('ok','Connected — move your head!');
    document.getElementById('btn').textContent='Connected ✓';
    interval=setInterval(()=>{{
      if(ws.readyState===1){{
        ws.send(JSON.stringify({{type:'gyro',yaw,pitch,roll}}));
        pkt++;
      }}
    }},16);
  }};
  ws.onclose=ws.onerror=()=>{{
    setStatus('err','Disconnected — reload page to retry');
    clearInterval(interval);
    document.getElementById('btn').disabled=false;
    document.getElementById('btn').textContent='Retry';
  }};
}}

function recenter(){{
  if(ws&&ws.readyState===1)
    ws.send(JSON.stringify({{type:'recenter',yaw,pitch,roll}}));
}}

(function loop(){{draw();requestAnimationFrame(loop)}})();
</script>
</body>
</html>"""

# ── HTTP server — serves the phone page ───────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        html = make_phone_html(LOCAL_IP, WS_PORT).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    def log_message(self, *args):
        pass  # silence HTTP logs

def run_http():
    server = HTTPServer(('0.0.0.0', HTTP_PORT), Handler)
    server.serve_forever()

# ── WebSocket handler ─────────────────────────────────────────────────────────
async def handle_phone(ws):
    tracker.clients += 1
    addr = ws.remote_address
    print(f"\n  ✓ Phone connected: {addr[0]}")
    print("  Move your head — tap Recenter in the app when ready\n")
    try:
        async for msg in ws:
            try:
                data = json.loads(msg)
                t = data.get('type')
                if t == 'gyro':
                    tracker.process(data.get('yaw',0), data.get('pitch',0), data.get('roll',0))
                elif t == 'recenter':
                    tracker.recenter(data.get('yaw',0), data.get('pitch',0), data.get('roll',0))
            except (json.JSONDecodeError, KeyError):
                pass
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        tracker.clients -= 1
        print(f"\n  Phone disconnected: {addr[0]}")

# ── Background threads ────────────────────────────────────────────────────────
def send_loop(sock):
    interval = 1.0 / SEND_HZ
    while True:
        if tracker.clients > 0:
            try:
                sock.sendto(tracker.opentrack_packet(), (OPENTRACK_HOST, OPENTRACK_PORT))
            except Exception:
                pass
        time.sleep(interval)

def status_loop():
    while True:
        time.sleep(4)
        if tracker.clients > 0:
            print(f"  yaw={tracker.sy:+6.1f}°  pitch={tracker.sp:+6.1f}°  "
                  f"roll={tracker.sr:+6.1f}°  pkts={tracker.pkt}")

# ── Main ──────────────────────────────────────────────────────────────────────
async def main():
    print("=" * 58)
    print("  BeamNG Head Tracker Bridge v2")
    print("=" * 58)
    print(f"\n  On your S23+, open Chrome and go to:")
    print(f"\n      http://{LOCAL_IP}:{HTTP_PORT}\n")
    print(f"  Then tap 'Start Tracking' — no typing needed!")
    print(f"\n  Sending to OpenTrack on localhost:{OPENTRACK_PORT}")
    print(f"  Ctrl+C to quit")
    print("-" * 58)

    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    threading.Thread(target=run_http,   daemon=True).start()
    threading.Thread(target=send_loop,  args=(udp_sock,), daemon=True).start()
    threading.Thread(target=status_loop,daemon=True).start()

    async with websockets.serve(handle_phone, "0.0.0.0", WS_PORT):
        print(f"\n  HTTP server running on port {HTTP_PORT}")
        print(f"  WebSocket server running on port {WS_PORT}")
        print(f"  Waiting for phone...\n")
        await asyncio.Future()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n  Goodbye!")
        sys.exit(0)
