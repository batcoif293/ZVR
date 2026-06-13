"""
BeamNG Head Tracker Bridge
--------------------------
1. Runs a WebSocket server (phone connects here from Chrome)
2. Receives gyro data from the phone web app
3. Forwards it as OpenTrack UDP packets to BeamNG/OpenTrack on localhost

Requirements: pip install websockets
Usage:        python bridge.py
"""

import asyncio
import websockets
import socket
import struct
import json
import threading
import time
import sys

# ── Config ────────────────────────────────────────────────────────────────────
WS_PORT        = 5556       # WebSocket port - phone connects here
OPENTRACK_PORT = 4242       # OpenTrack/BeamNG freetrack UDP port (localhost)
OPENTRACK_HOST = "127.0.0.1"

YAW_SCALE   = 1.0           # Tweak if rotation feels too fast/slow
PITCH_SCALE = 1.0
ROLL_SCALE  = 0.5

SMOOTHING   = 0.65          # 0 = raw, 0.9 = very smooth (adds lag)
SEND_HZ     = 100           # How often to send to OpenTrack
# ──────────────────────────────────────────────────────────────────────────────

class Tracker:
    def __init__(self):
        self.yaw = self.pitch = self.roll = 0.0
        self.sy  = self.sp   = self.sr   = 0.0   # smoothed
        self.yaw_off = self.pitch_off = self.roll_off = 0.0
        self.clients = 0
        self.pkt = 0

    def process(self, raw_yaw, raw_pitch, raw_roll):
        y = (raw_yaw   - self.yaw_off)
        p = (raw_pitch - self.pitch_off)
        r = (raw_roll  - self.roll_off)

        # Wrap to [-180, 180]
        y = (y + 180) % 360 - 180
        p = (p + 180) % 360 - 180
        r = (r + 180) % 360 - 180

        y *= YAW_SCALE
        p *= PITCH_SCALE
        r *= ROLL_SCALE

        s = SMOOTHING
        self.sy = s * self.sy + (1-s) * y
        self.sp = s * self.sp + (1-s) * p
        self.sr = s * self.sr + (1-s) * r
        self.pkt += 1

    def recenter(self, raw_yaw, raw_pitch, raw_roll):
        self.yaw_off   = raw_yaw
        self.pitch_off = raw_pitch
        self.roll_off  = raw_roll
        self.sy = self.sp = self.sr = 0.0
        print(f"\n  [Recentered]")

    def opentrack_packet(self):
        # 6 little-endian doubles: x, y, z (mm), yaw, pitch, roll (degrees)
        return struct.pack('<6d', 0.0, 0.0, 0.0, self.sy, self.sp, self.sr)

tracker = Tracker()


async def handle_phone(ws):
    """Handle one phone WebSocket connection."""
    tracker.clients += 1
    addr = ws.remote_address
    print(f"\n  ✓ Phone connected: {addr[0]}")
    print("  Move your head - press Recenter in the app when ready\n")

    try:
        async for msg in ws:
            try:
                data = json.loads(msg)
                t = data.get('type')
                if t == 'gyro':
                    tracker.process(
                        data.get('yaw',   0.0),
                        data.get('pitch', 0.0),
                        data.get('roll',  0.0)
                    )
                elif t == 'recenter':
                    tracker.recenter(
                        data.get('yaw',   0.0),
                        data.get('pitch', 0.0),
                        data.get('roll',  0.0)
                    )
            except (json.JSONDecodeError, KeyError):
                pass
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        tracker.clients -= 1
        print(f"\n  Phone disconnected: {addr[0]}")


def send_loop(sock):
    """Background thread: sends OpenTrack UDP at SEND_HZ."""
    interval = 1.0 / SEND_HZ
    while True:
        if tracker.clients > 0:
            try:
                sock.sendto(tracker.opentrack_packet(), (OPENTRACK_HOST, OPENTRACK_PORT))
            except Exception:
                pass
        time.sleep(interval)


def status_loop():
    """Print live status every 3 seconds."""
    while True:
        time.sleep(3)
        if tracker.clients > 0:
            print(f"  yaw={tracker.sy:+6.1f}°  pitch={tracker.sp:+6.1f}°  "
                  f"roll={tracker.sr:+6.1f}°  | pkts={tracker.pkt}")


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


async def main():
    ip = get_local_ip()

    print("=" * 58)
    print("  BeamNG Head Tracker Bridge")
    print("=" * 58)
    print(f"\n  Step 1: Open phone.html in Chrome on your S23+")
    print(f"  Step 2: Enter this address in the app:")
    print(f"\n            {ip}:{WS_PORT}\n")
    print(f"  Step 3: In BeamNG, set Input > Head Tracking to OpenTrack")
    print(f"          (Options > Input > Head Tracking > OpenTrack)")
    print(f"\n  Sending to OpenTrack on localhost:{OPENTRACK_PORT}")
    print(f"  Ctrl+C to quit")
    print("-" * 58)

    # UDP socket for OpenTrack output
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Background threads
    threading.Thread(target=send_loop,   args=(udp_sock,), daemon=True).start()
    threading.Thread(target=status_loop, daemon=True).start()

    # WebSocket server - listens on all interfaces so phone can reach it
    async with websockets.serve(handle_phone, "0.0.0.0", WS_PORT):
        print(f"\n  Waiting for phone connection on port {WS_PORT}...\n")
        await asyncio.Future()  # run forever


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n  Goodbye!")
        sys.exit(0)
