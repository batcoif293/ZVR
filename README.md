# ZVR
Free software for mobile phone to PC for 3DOF VR - NO ADMIN REQUIRED

# BeamNG Head Tracker — Setup Guide

Turn your Samsung S23+ gyroscope into a head tracker for BeamNG.drive.
No admin rights needed. No installs on the school laptop (just Python).

---

## What you need

- Python 3.8+ on the laptop (just to run the script — no install)
- `websockets` Python library (one command to install, no admin)
- Your S23+ on the same Wi-Fi as the laptop
- OpenTrack (free, portable version — no installer needed)

---

## Step 1 — Install the websockets library (no admin)

Open Command Prompt on the laptop and run:

```
pip install websockets --user
```

if this dosent work, try adding:

Option 1 — use py instead of pip:
py -m pip install websockets --user

Option 2 — use the full Python launcher:
python -m pip install websockets --user

Option 3 — use python3:
python3 -m pip install websockets --user

Try each one until one works. if you get an error like:
Python was not found; run without arguments to install from the Microsoft Store, or disable this shortcut from Settings > Apps > Advanced app settings > App execution aliases.
THEN:
goto microsoft store and download python 1.12 (1.12 specificly)

this was my result:
```
C:\Users\28ijw>python -m pip install websockets --user
Collecting websockets
  Downloading websockets-16.0-cp312-cp312-win_amd64.whl.metadata (7.0 kB)
Downloading websockets-16.0-cp312-cp312-win_amd64.whl (178 kB)
Installing collected packages: websockets
  WARNING: The script websockets.exe is installed in 'C:\Users\28ijw\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\LocalCache\local-packages\Python312\Scripts' which is not on PATH.
  Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
Successfully installed websockets-16.0

[notice] A new release of pip is available: 25.0.1 -> 26.1.2
[notice] To update, run: C:\Users\28ijw\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\python.exe -m pip install --upgrade pip
```

The `--user` flag installs it to your own profile folder — no admin needed.

---

## Step 2 — Download OpenTrack (portable, no installer)

1. Go to: https://github.com/opentrack/opentrack/releases/latest
2. Download the file ending in `-win-portable.7z`  (NOT the installer)
3. Extract it anywhere — your Desktop, Downloads folder, wherever
4. Run `opentrack.exe` from the extracted folder

**In OpenTrack:**
- Input  → `UDP over network` → click the hammer icon → Port: `4242` (this is is not on by default)
- Output → `freetrack 2.0 Enhanced` → click the hammer icon → set to `Both` (this is on by default, but check anyways)
- Filter → `Accela` (smooths out jitter) (this is on by default, but check anyways)
- Click **Start** (the gray buttton next to stop, in the bottom right corner of the screen. they are under "tracking")

---

## Step 3 — Run the bridge script

Double-click `bridge.py`, or open Command Prompt and run:

```
python bridge.py
```

You'll see something like:

```
  Your PC's IP address: 192.168.1.45
  Enter this in the phone web app: 192.168.1.45:5556
```

**Write down that IP address.**

---

## Step 4 — Open the phone web app

1. Transfer `phone.html` to your S23+ (email it to yourself, or put it
   in Google Drive and download it, or connect via USB)
2. Open it in **Chrome** (not Samsung Internet — Chrome only, for gyro access)
3. In the IP field, type your PC's IP address shown in Step 3, e.g.:
   `192.168.1.45:5556`
4. Tap **Connect**
5. Chrome will ask for motion sensor permission — tap **Allow**

You should see the horizon visualizer start moving when you tilt your phone.

---

## Step 5 — Enable head tracking in BeamNG

1. Launch BeamNG normally (no Vulkan mode needed — this is NOT VR mode)
2. Go to: **Options → Input → Head Tracking**
3. Enable it and select **OpenTrack** (or freetrack) as the source
4. Go into a car in cockpit view (press `C`)
5. Look straight ahead, then tap **Recenter** in the phone app

Your head movements should now control the in-game camera!

---

## Tips

- **Recenter** whenever the view drifts — tap Recenter in the phone app
- If movement feels **too sensitive**: lower the Sensitivity slider in the app
- If it feels **too laggy**: open bridge.py in Notepad, change `SMOOTHING = 0.65`
  to something lower like `0.4`, save and rerun
- For best results, hold your phone in a phone VR shell mount so your
  head movements directly move the phone
- The phone screen doesn't need to stay on the whole time if you use a
  mount — but keep Chrome open and running in the foreground

---

## Troubleshooting

| Problem | Fix |
|---|---|
| "Could not reach PC" | Check both devices are on same Wi-Fi |
| Camera doesn't move | Make sure OpenTrack is running AND connected (green dot) |
| Camera drifts | Tap Recenter; gyros drift over time, this is normal |
| Very jittery | Increase SMOOTHING in bridge.py (e.g. 0.8) |
| Phone app won't load gyro | Must use Chrome, not Samsung Internet |
| bridge.py won't start | Run `pip install websockets --user` first |

---

## Files

- `bridge.py`   — Run this on your laptop
- `phone.html`  — Open this in Chrome on your S23+
- `README.md`   — This file
