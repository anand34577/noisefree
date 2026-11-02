# Changelog

All notable changes to this project are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [1.2.0] - 2026-11-02

### Added

- Clean up a recording: open a WAV, FLAC, OGG or MP3 file (or drop it on the window) and NoiseFree saves a noise-free copy with the same sample rate, channels and format, using your strength setting. Ctrl+O opens it.

## [1.1.0] - 2026-11-02

### Changed

- The window is about half as tall and fits on small and scaled screens. The power button now sits next to the status text, and the meters, strength slider and status box take less space.
- NoiseFree draws its own title bar with settings, minimise and close buttons, in the app's colours. On Windows 11 the window keeps rounded corners and a shadow.
- Dropdown lists open as a clean rounded list below the box, without the blurred shadow and fade.
- **Hear yourself** is remembered between runs instead of always starting off.

### Fixed

- The window always has a taskbar button while it's open, including after starting in the tray.
- After a restart, launch at sign-in reopens the window if it was open before, at the same position. Settings are saved before Windows shuts down, so a change made just before a restart isn't lost.

## [1.0.1] - 2026-11-02

First published release, with downloads for Windows, macOS and Linux. It
has every feature listed for 1.0.0 in
[CHANGELOG.md](https://github.com/anand34577/noisefree/blob/main/CHANGELOG.md),
plus one fix.

### Fixed

- The BlackHole installer download no longer fails with "HTTP Error 406". This broke the macOS build and would have broken the in-app download on macOS too.

## [1.0.0] - 2026-11-02

### Added

- Real-time noise removal with the DTLN model (ONNX), 32 ms latency at 16 kHz mono.
- Runs the model on the GPU through DirectML (Windows), CUDA (Linux, with `onnxruntime-gpu`) or Core ML (macOS), and falls back to the CPU when no GPU provider loads.
- Virtual microphone output: VB-CABLE on Windows, BlackHole on macOS, and a PulseAudio/PipeWire null sink that the app creates and removes on Linux.
- In-app driver install. On Windows it downloads the official VB-CABLE package and opens its own installer; on macOS it opens the bundled BlackHole installer.
- Main screen with an on/off switch, live level meters for the raw mic and the cleaned output, a strength slider, and "Hear yourself" monitoring.
- Settings for the processor, monitor device, theme (system, light or dark), launch at sign-in, and keep running in the tray.
- Automatic recovery when a microphone is unplugged and plugged back in.
- Single-file builds for Windows and Linux and an `.app` bundle for macOS, produced by `build.py` and the `Build` GitHub Actions workflow.
