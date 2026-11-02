# FAQ

### Does my audio get sent anywhere?

No. The model runs on your computer and the app makes no network connections, except one: when you click **Install VB-CABLE**, it downloads the driver from vb-audio.com.

### Do I need an NVIDIA graphics card?

No. NoiseFree runs on any GPU that DirectML (Windows) or Core ML (macOS) supports, and on the CPU when there's no GPU. Most CPUs from the last ten years run it comfortably.

### How much delay does it add?

The model itself adds 32 ms. Buffering between devices adds about another 30 ms. On a call, that's well below what people notice.

### Why is the audio 16 kHz mono?

That's what the model was trained on, and it's the same quality most calling apps send anyway. It's not suitable for recording music or a podcast.

### Can I use it with OBS, a browser, or a game?

Yes. Any app that lets you choose a microphone can use the virtual one: OBS, Chrome or Firefox (for Google Meet, Jitsi and others), Discord, Steam voice chat, and so on.

### What happens to the virtual mic when I quit NoiseFree?

On Windows and macOS the virtual mic still exists, but it's silent until NoiseFree runs again. On Linux it disappears. If you don't want to think about it, turn on **Open when I sign in**.

### Can I remove VB-CABLE or BlackHole later?

Yes.

- **VB-CABLE:** download the package from [vb-audio.com/Cable](https://vb-audio.com/Cable/), run `VBCABLE_Setup_x64.exe` as administrator, click **Remove Driver**, and restart.
- **BlackHole:** follow the [uninstall steps in the BlackHole README](https://github.com/ExistentialAudio/BlackHole#uninstallation-instructions).

### Why doesn't NoiseFree include its own driver on Windows?

A virtual microphone on Windows has to be a kernel driver signed by Microsoft, which is a separate project in itself. VB-CABLE already does it well, and its licence lets us download and launch the official installer, but not embed it.

### How do I uninstall NoiseFree?

1. Turn off **Open when I sign in** in Settings.
2. Quit from the tray icon.
3. Delete `NoiseFree.exe`, `NoiseFree.app` or the `NoiseFree` file.

To also clear your saved settings, see [Settings](Configuration#where-settings-are-saved).
