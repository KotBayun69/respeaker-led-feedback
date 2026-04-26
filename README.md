# Home Assistant LED Feedback for ReSpeaker 2-Mic HAT v2

This project adds LED feedback to a Raspberry Pi Home Assistant Assist satellite with ReSpeaker 2-Mic HAT v2.

---


The 3 onboard LEDs reflect the Assist state:

| State        | LED Behavior            |
|-------------|------------------------|
| idle        | Off                    |
| listening   | Blue chase             |
| processing  | Blue pulse             |
| responding  | Reverse blue chase     |
| connected   | Short green chase      |
| error       | Red breathing          |

---

## Requirements

- Raspberry Pi with ReSpeaker 2-Mic HAT v2
- Home Assistant Assist satellite already working
- SPI enabled
- Python 3

---

## 1. Enable SPI

Run:

```bash
sudo raspi-config
```

Then navigate to:

Interface Options → SPI → Enable

Reboot:

```bash
sudo reboot
```

Verify:

```
ls /dev/spidev*
```

## 2. Install dependencies

```
sudo apt update
sudo apt install -y git python3-websockets python3-spidev
```

## 3. Clone required repositories

```
cd ~
git clone https://github.com/respeaker/mic_hat.git
git clone https://github.com/KotBayun69/respeaker-led-feedback.git
cd respeaker-led-feedback
```

## 4. Configure environment

```
cp .env.example .env
```
Replace all `<YOUR_...>` with actuals values.

## 5. Install systemd service

```
sudo cp ha-led-watcher.service /etc/systemd/system/
sudo nano /etc/systemd/system/ha-led-watcher.service
```

Replace `<YOUR_USER>` with your actual user name.
Enable and start it:

```
sudo systemctl --enable --now ha-led-watcher.service
```

Check the status:

```
systemctl status ha-led-watcher.service
```

View logs:

```
sudo journalctl -u ha-led-watcher -f
```

## 6. Test

```
sudo systemctl restart ha-led-watcher
```

Expected:

- Green animation on startup
- LEDs off when idle
- LEDs react to wake word and response states

## 7. Enjoy
