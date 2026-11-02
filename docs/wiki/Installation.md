# Installation

NoiseFree has two parts:

- **The app**, a single download that already contains everything it needs: Python, the AI model and the audio libraries.
- **A virtual audio cable**, a small driver that creates the extra microphone your meeting apps will pick. On Linux, NoiseFree creates this itself.

## What you need

| | Windows | macOS | Linux |
|---|---|---|---|
| OS version | Windows 10 or 11, 64-bit | macOS 12 or newer | Any desktop with PulseAudio or PipeWire (Ubuntu 22.04+, Fedora 36+, etc.) |
| Admin rights | Once, to install VB-CABLE | Once, to install BlackHole | Not needed |
| GPU | Optional | Optional | Optional |

## Windows

### 1. Download the app

Download `NoiseFree.exe` from the [latest release](https://github.com/anand34577/noisefree/releases/latest) and put it anywhere you like, for example your Desktop or `C:\Program Files\NoiseFree`.

### 2. Open it

Double-click `NoiseFree.exe`. The first launch takes a few seconds while it unpacks.

If Windows shows **"Windows protected your PC"**, click **More info**, then **Run anyway**. This appears because the app isn't code-signed yet.

You should see the NoiseFree window with a yellow box that says **One more step: add the virtual microphone**.

### 3. Install VB-CABLE

1. Click **Install VB-CABLE** in the yellow box. A progress bar shows the download (about 1.3 MB from vb-audio.com).
2. Windows asks whether to let *VBCABLE_Setup_x64.exe* make changes. Click **Yes**.
3. In the VB-Audio window, click **Install Driver**, then **OK** when it says the installation is complete.
4. Restart your computer.

After the restart, open NoiseFree again. The box turns green and says **Ready for your calls**.

## macOS

### 1. Download the app

Download `NoiseFree-macOS.zip` from the [latest release](https://github.com/anand34577/noisefree/releases/latest), unzip it, and drag `NoiseFree.app` into your Applications folder.

### 2. Open it

The first time, right-click (or Control-click) `NoiseFree.app` and choose **Open**, then **Open** again in the dialog. macOS blocks a normal double-click on apps that aren't notarised; this only happens once.

When macOS asks whether NoiseFree may use the microphone, click **Allow**.

### 3. Install BlackHole

1. Click **Install BlackHole** in the yellow box. The macOS Installer opens with the BlackHole package, which is bundled inside the app.
2. Click through the installer and enter your Mac password when asked.
3. Back in NoiseFree, click **Check again**. The box turns green.

## Linux

### 1. Download the app

Download `NoiseFree-Linux-x64.tar.gz` from the [latest release](https://github.com/anand34577/noisefree/releases/latest) and unpack it:

```bash
tar xzf NoiseFree-Linux-x64.tar.gz
```

### 2. Open it

```bash
./NoiseFree
```

The window opens with a green **Ready for your calls** box. NoiseFree has created a virtual microphone called **NoiseFree Microphone**, and it removes it again when you quit.

If you see a red box saying **Couldn't create the virtual microphone**, install the PulseAudio tools:

```bash
sudo apt install pulseaudio-utils
```

On Fedora, the package is `pulseaudio-utils` too; on Arch, it's `libpulse`.

## Running from source instead

If you'd rather run the Python code directly, see [Building and releasing](Building-and-Releasing#run-from-source).

Next: [Getting started](Getting-Started).
