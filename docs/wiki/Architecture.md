# Architecture

NoiseFree is about 2,000 lines of Python. The UI is Qt (PySide6), audio I/O goes through PortAudio (`sounddevice`), resampling uses libsoxr, and the model runs in ONNX Runtime.

## Audio path

```
                     audio thread (mic callback)
┌──────────┐   soxr    ┌──────────────┐   ┌──────────┐   soxr   ┌──────┐   ┌────────────┐
│ mic      │──────────▶│ 16 kHz queue │──▶│ DTLN x2  │─────────▶│ FIFO │──▶│ virtual    │
│ 48 kHz   │           │ 128-sample   │   │ + blend  │          └──────┘   │ cable out  │
└──────────┘           │ blocks       │   └──────────┘   soxr   ┌──────┐   └────────────┘
                       └──────────────┘        └───────────────▶│ FIFO │──▶ headphones
                                                                └──────┘    (Hear yourself)
```

1. **Input.** The mic stream opens at the device's own rate (usually 48 kHz). Asking PortAudio for 16 kHz directly works on some host APIs and fails on others (WASAPI), so the app always resamples itself.
2. **Blocking.** Resampled audio collects in a buffer and is cut into 128-sample (8 ms) blocks, which is DTLN's hop size.
3. **Model.** `Denoiser.process()` runs the two DTLN stages. Stage 1 predicts a magnitude mask on a 512-point FFT; stage 2 refines the result in a learned time-domain basis. Each stage carries LSTM state between calls.
4. **Blend.** The raw signal is delayed by 384 samples (the model's window minus one hop) so it lines up with the model output, then mixed by the **Strength** setting. The same delayed signal is used when removal is off, so switching on and off doesn't make the audio jump.
5. **Outputs.** Each output (virtual cable, monitor) has its own soxr resampler and a FIFO, and the output device's callback pulls from it. The FIFO waits for 30 ms of audio before it starts playing and trims back to that if more than 150 ms pile up. That cushion soaks up the drift between two devices that each run on their own clock.

All model work happens on the mic's audio thread. It takes about 0.4 ms per 8 ms block on a CPU.

## Code map

| File | Responsibility |
|---|---|
| `main.py` | Entry point used by `python main.py` and PyInstaller |
| `noisefree/app.py` | `QApplication` setup, single-instance check over a `QLocalServer` |
| `noisefree/resources.py` | Paths that work from source and from a PyInstaller bundle; version |
| `noisefree/denoiser.py` | Model download fallback, provider selection, DTLN inference |
| `noisefree/engine.py` | `Engine` (streams, blocking, blend), `Fifo`, `Output` |
| `noisefree/devices.py` | Device lists per OS, cable detection, Linux null sink, driver installers, launch at login |
| `noisefree/ui/theme.py` | Light and dark design tokens, the generated Qt stylesheet, title bar colour |
| `noisefree/ui/icons.py` | Stroke icons drawn from SVG paths; the app icon |
| `noisefree/ui/widgets.py` | `PowerButton`, `Toggle`, `LevelMeter`, `Banner`, `Row`, focus-visible filter |
| `noisefree/ui/window.py` | Home and Settings pages, tray, all state-to-UI logic |

## Threads

- **UI thread.** Qt event loop. A 33 ms timer reads the engine's level values and error flag.
- **Audio threads.** One per PortAudio stream. The mic callback does the processing; output callbacks only pull from their FIFO.
- **Workers.** Short-lived Python threads load the model and download drivers, then report back through Qt signals on a `Bridge` object, so UI updates always happen on the UI thread.

The engine swaps a new `Denoiser` in with a single attribute assignment, which is atomic in CPython. Changing the processor in Settings therefore never stops the audio.

## Per-OS details

**Windows.** Devices come from the WASAPI host API, which gives full device names (MME truncates them to 31 characters) and lower latency. The cable is any output whose name contains "CABLE Input".

**macOS.** Core Audio. The cable is any device whose name contains "BlackHole". The build adds `NSMicrophoneUsageDescription` to `Info.plist`, without which macOS silently gives the app a muted mic.

**Linux.** PortAudio can only reach PulseAudio or PipeWire through one generic `pulse` ALSA device. To target a specific source or sink, `devices.open_stream` sets `PULSE_SOURCE` or `PULSE_SINK` in the environment just before opening the stream. The virtual mic is a `module-null-sink` plus a `module-remap-source` on its monitor, loaded with `pactl` at start and unloaded on quit.

## Design system

Colours, radii and motion timing are tokens in `ui/theme.py`. The stylesheet is generated from the active token set, and custom-painted widgets read the same tokens through the `Themed` mixin. To add a colour, add it to both `LIGHT` and `DARK` and reference it by key.

Focus rings only appear for keyboard focus: an app-wide event filter sets a `kbfocus` property on focus-in when the reason was Tab, and the stylesheet styles `[kbfocus="true"]` instead of `:focus`.
