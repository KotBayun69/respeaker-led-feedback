#!/usr/bin/env python3
import asyncio
import json
import os
import signal
import ssl
import sys

import websockets

MIC_HAT_PATH = os.environ["MIC_HAT_PATH"]
sys.path.insert(0, MIC_HAT_PATH)

from apa102 import APA102

HA_WS_URL = os.environ["HA_WS_URL"]
HA_TOKEN = os.environ["HA_TOKEN"]
SATELLITE_ENTITY_ID = os.environ["SATELLITE_ENTITY_ID"]

NUM_LEDS = 3

BLUE = (0, 0, 80)
GREEN = (0, 80, 20)
RED = (80, 0, 0)

state = "idle"

leds = APA102(num_led=NUM_LEDS, bus=0, device=1)


def show(pixels):
    for i, (r, g, b) in enumerate(pixels):
        leds.set_pixel(i, r, g, b)
    leds.show()


def clear():
    leds.clear_strip()
    leds.show()


def scale(color, factor):
    return tuple(int(x * factor) for x in color)


def chase_frames(color):
    return [
        [color, scale(color, 0.35), (0, 0, 0)],
        [(0, 0, 0), color, scale(color, 0.35)],
        [scale(color, 0.35), (0, 0, 0), color],
    ]


def pulse_frames(color):
    return [
        [scale(color, 0.15)] * NUM_LEDS,
        [scale(color, 0.35)] * NUM_LEDS,
        [scale(color, 0.70)] * NUM_LEDS,
        [color] * NUM_LEDS,
        [scale(color, 0.70)] * NUM_LEDS,
        [scale(color, 0.35)] * NUM_LEDS,
    ]


LISTENING = chase_frames(BLUE)
RESPONDING = list(reversed(chase_frames(BLUE)))
PROCESSING = pulse_frames(BLUE)
CONNECTED = chase_frames(GREEN)
ERROR = pulse_frames(RED)


async def animation_loop():
    idx = 0
    last = None

    while True:
        global state

        if state != last:
            idx = 0
            last = state
            if state == "idle":
                clear()

        if state == "idle":
            await asyncio.sleep(1.0)

        elif state == "connected":
            show(CONNECTED[idx % len(CONNECTED)])
            idx += 1
            await asyncio.sleep(0.12)

        elif state == "listening":
            show(LISTENING[idx % len(LISTENING)])
            idx += 1
            await asyncio.sleep(0.12)

        elif state == "processing":
            show(PROCESSING[idx % len(PROCESSING)])
            idx += 1
            await asyncio.sleep(0.10)

        elif state == "responding":
            show(RESPONDING[idx % len(RESPONDING)])
            idx += 1
            await asyncio.sleep(0.12)

        elif state == "error":
            show(ERROR[idx % len(ERROR)])
            idx += 1
            await asyncio.sleep(0.20)

        else:
            clear()
            await asyncio.sleep(1.0)


async def ha_loop():
    global state

    ssl_ctx = ssl.create_default_context() if HA_WS_URL.startswith("wss://") else None

    while True:
        try:
            async with websockets.connect(
                HA_WS_URL,
                ssl=ssl_ctx,
                ping_interval=20,
                ping_timeout=20,
            ) as ws:
                await ws.recv()

                await ws.send(json.dumps({
                    "type": "auth",
                    "access_token": HA_TOKEN,
                }))

                auth = json.loads(await ws.recv())
                if auth.get("type") != "auth_ok":
                    raise RuntimeError(auth)

                await ws.send(json.dumps({
                    "id": 1,
                    "type": "subscribe_trigger",
                    "trigger": {
                        "platform": "state",
                        "entity_id": SATELLITE_ENTITY_ID,
                    },
                }))

                sub = json.loads(await ws.recv())
                if not sub.get("success", False):
                    raise RuntimeError(sub)

                state = "connected"
                await asyncio.sleep(2.0)
                state = "idle"

                async for raw in ws:
                    msg = json.loads(raw)
                    if msg.get("type") != "event":
                        continue

                    trigger = msg["event"]["variables"]["trigger"]
                    new_state = trigger["to_state"]["state"]

                    if new_state in ("idle", "listening", "processing", "responding"):
                        state = new_state
                    else:
                        state = "idle"

        except asyncio.CancelledError:
            raise
        except Exception:
            state = "error"
            await asyncio.sleep(5)


async def main():
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    tasks = [
        asyncio.create_task(animation_loop()),
        asyncio.create_task(ha_loop()),
    ]

    await stop.wait()

    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)
    clear()
    leds.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
