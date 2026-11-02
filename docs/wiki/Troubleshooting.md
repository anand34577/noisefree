# Troubleshooting

Find the message you're seeing, or the symptom closest to it.

## Opening the app

### "Windows protected your PC"

The build isn't code-signed yet. Click **More info**, then **Run anyway**. Windows remembers this for that file.

### "NoiseFree can't be opened because Apple cannot check it for malicious software"

Right-click `NoiseFree.app` in Finder, choose **Open**, then **Open** in the dialog. If there's no Open button, go to **System Settings** → **Privacy & Security**, scroll down, and click **Open Anyway** next to the NoiseFree message.

### Nothing happens when I open it a second time

That's intentional. Only one copy runs at a time, and opening it again brings the existing window forward. If the window doesn't appear, look for the NoiseFree icon in the system tray and click it.

### `qt.qpa.plugin: Could not load the Qt platform plugin "xcb"` (Linux)

Qt needs one extra system library:

```bash
sudo apt install libxcb-cursor0
```

### `OSError: PortAudio library not found` (Linux, running from source)

```bash
sudo apt install libportaudio2
```

The standalone Linux build includes PortAudio, so this only happens when running from source.

## Virtual microphone

### The box stays yellow after installing VB-CABLE

Windows only loads the new driver after a restart. Restart, open NoiseFree, and the box turns green.

If it's still yellow after restarting, check the driver is there: open **Settings** → **System** → **Sound** → **All sound devices**. You should see **CABLE Input** under Output devices. If it's missing, run the installer again from NoiseFree's Settings (**Reinstall VB-CABLE**) and make sure you clicked **Install Driver** in the VB-Audio window, not just closed it.

### "Installation didn't finish": "The installer was cancelled or could not start."

You clicked **No** on the Windows admin prompt, or your account isn't allowed to install drivers. Click **Try again** and choose **Yes**. On a work computer you may need IT to install VB-CABLE for you.

### "Couldn't create the virtual microphone" (Linux)

NoiseFree couldn't find `pactl`. Install it:

```bash
sudo apt install pulseaudio-utils
```

PipeWire systems need `pipewire-pulse` running too. It is by default on Ubuntu 22.10+ and Fedora 34+.

### My meeting app doesn't list CABLE Output / BlackHole / NoiseFree Microphone

- Restart the meeting app. Teams and Zoom only scan devices when they start.
- On Linux, the mic only exists while NoiseFree is running. Open NoiseFree first, then the meeting app.

## Microphone

### The "Your microphone" meter doesn't move

1. Check the right mic is selected in the **Microphone** list.
2. Check your OS lets apps use the mic:
   - Windows: **Settings** → **Privacy & security** → **Microphone**. Turn on **Microphone access** and **Let desktop apps access your microphone**.
   - macOS: **System Settings** → **Privacy & Security** → **Microphone**. Turn on **NoiseFree**.
3. Check the mic isn't muted with a hardware switch on the headset.

### "Couldn't open the microphone"

The text under it is PortAudio's error. The common ones:

| Error text contains | Cause | Fix |
|---|---|---|
| `Device unavailable` | Another app has exclusive control of the mic | In Windows Sound settings → the mic → **Advanced**, untick **Allow applications to take exclusive control** |
| `Invalid device` | The mic was removed between listing and opening | Click **Try again** |
| `Unanticipated host error` | Usually the OS privacy block | See the meter section above |

### "Microphone disconnected"

The mic was unplugged or went to sleep (common with Bluetooth headsets). NoiseFree checks every 2.5 seconds and reconnects when the same mic is back. To switch to a different mic, open the **Microphone** list and pick one.

## Sound quality

### People say I sound robotic or underwater

- Lower **Strength** to 70–85%.
- Turn off the meeting app's own noise suppression (see [Getting started](Getting-Started#4-turn-off-the-meeting-apps-own-noise-suppression)). Two filters stacked cause this more often than anything else.

### My audio crackles or drops out

The computer isn't keeping up. Try:

- Settings → **Run the AI model on** → switch between GPU and CPU. One of them is usually smoother on a given machine.
- Close heavy apps (games, video export).
- On a laptop, plug in the charger. Power-saving modes slow the CPU.

### I hear an echo with "Hear yourself"

You're listening through speakers, and the mic picks them up. Use headphones, or turn **Hear yourself** off.

### Some noise still gets through

DTLN handles steady noise (fans, air conditioning, hum, traffic) best. Sudden sounds like a door slam or a dog bark are reduced but not always removed completely.

### "The selected processor wasn't available, so NoiseFree is using the CPU."

The GPU runtime failed to load, usually because of an old graphics driver. Noise removal still works on the CPU. To get the GPU back, update your graphics driver and restart NoiseFree.
