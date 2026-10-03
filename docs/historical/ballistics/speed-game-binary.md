# The Pocketsocket Binary Space-Ship Speed Game 🚀

> **Game rules:** bullets are projectiles, Pocketsocket manages the alert message, and the glowing force field is imaginary. We are measuring the software race and having fun with the result.

## Meet the ship

The compiled `pocketsocket-cli` is the lean server in this story. It owns the WebSocket socket, starts without importing Python, and waits for mission control to send the incoming-threat message.

Python can still be on the bridge:

```text
Python sensor / mission control ──WebSocket──> standalone Pocketsocket binary ──> force field
```

That is the deployment shape this article is about. The binary runs the server; Python can provide the client, orchestration, or application logic.

## The launch statistic

The standalone benchmark launches the compiled binary with `--run` and reads its reported TTL:

| Measurement | Recorded result |
|-------------|-----------------|
| Runs | 50 |
| Average TTL | **0.8042 ms** |
| Median TTL | 0.7961 ms |
| Fastest TTL | 0.4885 ms |
| Slowest TTL | 1.2644 ms |

That is the ship's launch countdown: from binary process start to its reported ready point.

## Round One: Fire the trigger and launch the ship 🔫

The trigger fires. The projectile starts moving. The compiled server begins its launch sequence.

| Projectile | Velocity | Time across 10 feet |
|------------|----------|---------------------|
| 300 Blackout | 1,020 ft/s | 9.80 ms |
| Average rifle round | 2,777 ft/s | 3.60 ms |
| 50 BMG | 2,815 ft/s | 3.55 ms |
| 204 Ruger | 4,450 ft/s | 2.25 ms |

The binary's `0.8042 ms` average TTL beats every travel time on the board. The force field is online while the fastest projectile is still completing its opening credits.

```
TIME (ms)     0.0       0.5       1.0       1.5       2.0       2.5
              |---------|---------|---------|---------|---------|
BINARY        ████████  🛡️ FIELD ONLINE (0.8042ms)
204 RUGER     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━▶💥  (2.25ms)
50 BMG        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━▶💥

MISSION CONTROL: "Shields up!"
POCKETSOCKET:   "Already done."
```

**Round One result:** the Pocketsocket binary wins the startup race by a comfortable margin.

## Round Two: How much projectile fits inside one launch? 📏

At `0.8042 ms`, how far does each projectile travel?

\[
 d = v t
\]

| Projectile | Distance during 0.8042 ms | Space-ship comparison |
|------------|---------------------------|-----------------------|
| 300 Blackout | **9.85 inches** | Dinner plate |
| Average rifle round | **26.8 inches** | Shorter than a baseball bat |
| 50 BMG | **27.2 inches** | About 2.3 feet |
| 204 Ruger | **42.9 inches** | Nearly a yardstick |

The binary launches before the fastest projectile has traveled four feet. Somewhere on the bridge, an ensign is already polishing the force-field controls.

## Round Three: The field is already online 🛡️

Now we give the ship the sensible advantage: the server is deployed and already running.

1. The standalone binary owns the server socket.
2. Python mission control connects as a WebSocket client.
3. Python sends `INCOMING_PROJECTILE`.
4. The binary handles the message and reports field status.

The binary's startup time is now behind us. The race is message handling.

The repository's throughput example records a **0.022 ms local echo round trip**. In that interval:

- the fastest listed projectile travels about **29.8 mm** (1.17 inches);
- light travels about **6.6 km in vacuum**; and
- the ship can complete roughly **102 echo round trips** before the fastest projectile crosses ten feet.

```
Python client:    "INCOMING_PROJECTILE"
Binary server:    "FORCE FIELD: ONLINE"
Elapsed:          0.022 ms
Projectile:       "I have traveled 29.8 mm and remain extremely dramatic."
```

## Round Four: Give mission control a head start 🐍

A Python client launched at the trigger has its own startup path. A pre-running Python client does not. So we run two variants:

### Variant A: Mission control already running

```text
Python client [READY] ──message──> Binary server [READY] ──> Field [ONLINE]
```

This is the clean deployable setup: Python handles sensors and application logic, while the compiled binary remains a small, ready WebSocket server.

### Variant B: Mission control launches with the trigger

```text
Trigger fires -> Python client starts -> WebSocket connects -> binary receives alert
```

Now the client startup and connection path join the stopwatch. The binary is still fast; mission control has simply decided to sprint down the corridor carrying the alert clipboard.

## Round Five: The force-field distance championship 🏆

For the binary's internal TTL game, the fastest projectile covers `42.9 inches` during the measured startup interval:

```
STANDALONE BINARY
You ●────────────────────────▶ FORCE FIELD
  0.8042ms: ONLINE

204 RUGER
You ●────────────────────────────────────────────────────────▶ FORCE FIELD
  2.25ms: ARRIVES AT 10 FEET
```

The binary is online first. The scoreboard flashes **SHIELDS UP**. The crew celebrates by pressing the same button twice.

## Round Six: How many launches before impact? 🔢

During the fastest projectile's `2.25 ms` ten-foot journey:

| Event | Count |
|-------|-------|
| Binary internal TTL intervals | **2.8** |
| Local `0.022 ms` echo round trips | **102** |
| 3 GHz CPU cycles | **6.75 million** |
| 144 Hz display frames | **0.32** |
| Human blink cycles | **0.015** |

The binary could finish nearly three launch intervals before the fastest projectile completes its approach. Mission control has enough time for one terse status update and a tasteful sound effect.

## The ship's technical advantage 🔧

- **Native compilation:** Nim becomes a compact machine-code executable.
- **Small server path:** no Python interpreter or wrapper import is required for binary startup.
- **Focused initialization:** the socket and server lifecycle come online quickly.
- **Flexible bridge:** Python can remain useful on the client or orchestration side.

The result is a neat split: the binary keeps the server lean, while Python remains available wherever Python is most useful.

## Final scoreboard 🥇

| Event | Winner |
|-------|--------|
| Fastest standalone launch | **Pocketsocket binary** |
| Most theatrical force-field activation | **Pocketsocket binary** |
| Most convenient mission-control scripting | **Python client** |
| Most important status message | **SHIELDS UP** |

The standalone binary recorded a **0.8042 ms average internal TTL**, and the local message example recorded a **0.022 ms echo round trip**. In the software race, Pocketsocket gets the field online before the projectile reaches the mark.

## Try the launch yourself 🧪

```bash
nimble buildCliCI -d:release -d:lto -d:strip
python3 benchmarks/benchmark.py --cli dist/pocketsocket-cli-linux_amd64 -n 50
python3 benchmarks/benchmark_throughput.py
```

Use the platform-specific binary name produced by the build task when it differs from the Linux x86_64 example.

**Mission complete:** compiled binary online, Python bridge available, force field glowing, projectile defeated in the software scoreboard. 🚀
