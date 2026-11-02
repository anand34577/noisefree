# Building and releasing

## Run from source

You need Python 3.10 or newer. Check with:

```bash
python --version
```

It should print `Python 3.10.x` or higher.

### 1. Get the code

```bash
git clone https://github.com/anand34577/noisefree.git
cd noisefree
```

### 2. Create a virtual environment

A virtual environment is a private folder of Python packages for this project, so nothing gets installed system-wide.

```bash
python -m venv .venv
```

Activate it. Windows (PowerShell):

```powershell
.venv\Scripts\activate
```

macOS or Linux:

```bash
source .venv/bin/activate
```

Your prompt should now start with `(.venv)`.

### 3. Install dependencies

Linux only, first:

```bash
sudo apt install libportaudio2
```

Then, on every OS:

```bash
pip install -r requirements.txt
```

This downloads about 150 MB (mostly Qt and ONNX Runtime) and takes a minute or two.

On Linux with an NVIDIA card, you can swap the CPU runtime for the CUDA one:

```bash
pip uninstall -y onnxruntime
pip install onnxruntime-gpu
```

### 4. Run

```bash
python main.py
```

The NoiseFree window opens. The model files are already in `models/`. If you deleted them, they're downloaded again on first run.

## Tests and lint

```bash
pip install ruff pytest
ruff check .
pytest -q
```

The tests check that the model suppresses steady noise by more than 15 dB, that the output FIFO behaves at its limits, and that the bypass signal is delayed by exactly the model's latency. They don't need a microphone. CI runs them on Windows, macOS and Linux for every push to `main` and every pull request.

## Build the standalone app

```bash
pip install -r requirements-build.txt
python build.py
```

| OS | Output | Notes |
|---|---|---|
| Windows | `dist/NoiseFree.exe` | Single file, about 77 MB. Takes 2 to 3 minutes. |
| macOS | `dist/NoiseFree.app` | App bundle. `build.py` downloads the BlackHole installer into `vendor/` and bundles it, adds the microphone permission text, and re-signs the bundle ad hoc. |
| Linux | `dist/NoiseFree` | Single file. Bundles `libportaudio.so.2` from the build machine. |

PyInstaller can only build for the OS it runs on. Use the GitHub workflow for the other two.

## Release

1. Update the version in `pyproject.toml` and `noisefree/resources.py`.
2. Add a section to `CHANGELOG.md` and a line to the wiki's [Changelog](Changelog).
3. Commit, then tag and push:

   ```bash
   git tag v1.0.1
   git push origin v1.0.1
   ```

4. The **Build** workflow runs on the tag, builds on all three systems, and creates a GitHub release with `NoiseFree.exe`, `NoiseFree-macOS.zip` and `NoiseFree-Linux-x64.tar.gz` attached. The release notes come from that version's section in `CHANGELOG.md`.

## Refreshing the README images

The screenshots are real captures of the app with a fixed set of devices, rendered from HTML layouts:

```bash
python assets/src/capture_app.py
```

Then render each layout in `assets/src/*.html` to the PNG of the same name in `assets/`, at 1600×400 for the banner, 1280×640 for the social preview and 1440×900 for screenshots.

## Code signing

Builds aren't signed yet, so Windows SmartScreen and macOS Gatekeeper warn on first launch. Signing needs a Windows code-signing certificate and an Apple Developer ID; once those exist, add the signing steps to `.github/workflows/build.yml`.
