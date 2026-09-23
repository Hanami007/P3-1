"""Reads card taps from an RC522 RFID/NFC module wired to the Raspberry
Pi's GPIO/SPI pins, and reports each tap to the kiosk backend so it can
auto-login the person -- reuses exactly the same presence-polling flow the
camera's face recognition already uses, so the frontend needs no changes.

An RC522 is *not* a USB keyboard-wedge reader: it can't type into the
browser's hidden input on its own, which is why this needs its own
always-on process alongside `uvicorn`, rather than just plugging in.

Wiring (RC522 -> Raspberry Pi GPIO, 3.3V ONLY -- 5V will damage the module):
    SDA  -> GPIO8  (CE0, pin 24)
    SCK  -> GPIO11 (pin 23)
    MOSI -> GPIO10 (pin 19)
    MISO -> GPIO9  (pin 21)
    IRQ  -> not connected
    GND  -> GND (pin 6)
    RST  -> GPIO25 (pin 22)
    3.3V -> 3.3V (pin 1)

Setup on the Pi:
    sudo raspi-config           # Interface Options -> SPI -> Enable
    pip install mfrc522 RPi.GPIO spidev requests

Run (as its own process, e.g. a systemd service, separate from uvicorn):
    python rfid_reader_daemon.py
"""

import time

import requests
from mfrc522 import SimpleMFRC522

BACKEND_URL = "http://localhost:8000/api/presence/rfid-tap"
DEBOUNCE_SECONDS = 2.0

reader = SimpleMFRC522()


def main():
    print("RFID reader daemon started. Waiting for card taps... (Ctrl+C to stop)")
    last_uid = None
    last_tap_at = 0.0
    try:
        while True:
            uid, _text = reader.read()  # blocks until a card is in range
            card_uid = str(uid)
            now = time.monotonic()

            # A card held near the reader gets re-read continuously; only
            # report it once per debounce window unless a different card
            # replaces it.
            if card_uid == last_uid and now - last_tap_at < DEBOUNCE_SECONDS:
                continue
            last_uid = card_uid
            last_tap_at = now

            print(f"Card tapped: {card_uid}")
            try:
                requests.post(BACKEND_URL, json={"card_uid": card_uid}, timeout=5)
            except requests.RequestException as exc:
                print(f"Failed to report tap to backend: {exc}")
    except KeyboardInterrupt:
        pass
    finally:
        import RPi.GPIO as GPIO

        GPIO.cleanup()


if __name__ == "__main__":
    main()
