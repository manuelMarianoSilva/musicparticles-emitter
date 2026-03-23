Check the repo for the [Receiver App](https://github.com/manuelMarianoSilva/musicparticles-receiver) in order to get the complete experience.

# ✦ ParticleSystem — The Sender

> *Your fingers are the instrument. The screen is the stage.*

ParticleSystem turns your Android phone into a glowing, physics-driven particle canvas — and secretly, a musical instrument broadcasting its soul over WiFi.

Touch the screen and watch bursts of light erupt under your fingertips. Drag slowly and leave a luminous trail that drifts and swirls with Perlin turbulence. Hold your finger down and feel the screen pulse with escalating bursts that grow more furious the longer you hold. Every particle fades with gravity, colored by the speed and direction of your touch, each one alive for just a moment before dissolving into the dark.

Meanwhile, invisible to the eye, every touch is being broadcast as a precise JSON telemetry stream over your local WiFi — position, velocity, pressure, hold duration, trail length — all flying across the network in real time to anyone listening on port 9876.

It's a particle toy. It's a musical controller. It's both, simultaneously, without trying to be either.

---

## Requirements

- Android 8.0 (API 26) or higher
- WiFi network (for broadcast — particles work fine without it)
- A device with OpenGL ES 2.0 support (virtually everything made after 2012)

---

## Getting Started

### 1. Clone and open
```bash
git clone https://github.com/yourname/particle-system.git
```
Open the project in Android Studio (Ladybug or later recommended).

### 2. Build and install
Connect your Android device via USB with USB Debugging enabled, then hit **Run** in Android Studio. The app installs and launches directly.

### 3. Play
The screen is yours. Touch it.

---

## How to Use

### Basic gestures

| Gesture | What happens |
|---|---|
| **Tap** | Radial burst of particles scaled by pressure |
| **Drag** | Continuous trail — faster movement spawns more particles |
| **Hold** | Repeating burst pulses that grow larger over time |
| **Multi-touch** | Each finger is an independent emitter |
| **Release** | Final dissipation burst |

### Note grid overlay
The screen is divided into instrument zones — a subtle grid overlaid on the particles shows which note or drum hit corresponds to each area of the screen. The grid matches exactly what the receiver app will play when it receives your touch data.

By default the grid is set to **guitar mode** (4 rows × 2 columns, low notes at the bottom, high notes at the top). Change the instrument in `MainActivity.kt`:

```kotlin
private val SHOW_NOTE_GRID    = true        // show or hide the grid
private val SENDER_INSTRUMENT = "guitar"    // "guitar", "bass", "drums", "sync"
```

### Available instrument layouts

| Mode | Grid | Layout |
|---|---|---|
| `guitar` | 4 rows × 2 cols | E2–D5, low→high bottom→top |
| `bass` | 2 rows × 2 cols | E1–G2, low→high bottom→top |
| `drums` | Irregular zones | Kick, Snare, Hi-Hat, Toms, Crash, Ride |
| `sync` | 3 rows × 12 cols | Full chromatic C2–B4 |

---

## Network Broadcasting

Every touch event is broadcast as a UDP JSON packet to `255.255.255.255:9876` on your local WiFi network. The sender automatically discovers any receiver running on the same network and switches to direct unicast once paired.

**Packet format:**
```json
{
  "type": "TOUCH_MOVE",
  "did": "device-uuid",
  "sid": "session-uuid",
  "pid": 0,
  "x": 0.54,
  "y": 0.32,
  "pr": 0.81,
  "holdMs": 420,
  "vx": 0.003,
  "vy": -0.001,
  "trail": 17,
  "ts": 1700000000000
}
```

Coordinates are normalized to `[0.0, 1.0]` relative to the sender's screen dimensions, so the receiver can scale them to any screen size.

### Python listener (quick test)
Run this on any machine on the same WiFi to verify the broadcast is working:

```python
import socket, json

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(("", 9876))

while True:
    data, addr = sock.recvfrom(4096)
    e = json.loads(data.decode())
    print(f"[{e['type']:12}] ({e['x']:.2f},{e['y']:.2f}) hold={e['holdMs']}ms trail={e['trail']}")
```

---

## Configuration

### Particle tuning
All particle physics live in `ParticleEmitter.kt`. The values that matter most:

```kotlin
// Lifetime — how long particles survive (seconds)
rng.nextFloat() * 3f + 2f       // onTouchDown: 2–5s

// Gravity — set to 0f for zero gravity (current default)
const val GRAVITY = 0f

// Particle count per emission
val count = (20 + pressure * 30).toInt()   // onTouchDown
```

### Device identity
On first launch the app generates a persistent UUID stored in `SharedPreferences`. This ID is stamped on every broadcast packet so the receiver can identify which device sent what. To find your device ID, check Logcat filtered by `DeviceID`.

---

## Architecture

```
Touch Screen
    │
    ▼
TouchInputManager       — velocity, pressure, session tracking
    │
    ├──► BroadcastServer ──► UDP unicast ──► Receiver app
    │
    └──► ParticleEmitter ──► ParticleSystem ──► OpenGL ES 2.0
```

The rendering stack uses a single VBO uploaded once per frame — all particles in one draw call, point sprites with additive blending (`GL_SRC_ALPHA + GL_ONE`) for that plasma glow look.

---

## Pairing with the Receiver

1. Make sure both devices are on the **same WiFi network**
2. Launch the **receiver app** first
3. Launch the **sender app** — it will automatically discover and pair with the receiver
4. The receiver HUD will switch from `SEARCHING` to `● LIVE` once paired

Pairing uses UDP multicast on group `239.255.0.1:9877` — no manual IP entry required.
