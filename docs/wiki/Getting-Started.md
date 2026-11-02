# Getting started

This walks you through your first call. It assumes you've finished [Installation](Installation) and NoiseFree shows the green **Ready for your calls** box.

### 1. Pick your microphone

Open the **Microphone** list and choose the mic you actually talk into: your headset, USB mic or the laptop's built-in array.

Say something. The grey **Your microphone** meter should move. If it stays flat, the wrong mic is selected, or your OS is blocking access (see [Troubleshooting](Troubleshooting#the-your-microphone-meter-doesnt-move)).

### 2. Check that noise is being removed

Stay quiet for a few seconds. The grey meter still shows some level from the room, while the teal **What others hear** meter should drop close to empty. When you talk, both meters move.

To hear it for yourself, plug in headphones and turn on **Hear yourself**. You'll hear exactly what other people will hear, about 60 ms behind your voice.

### 3. Point your meeting app at NoiseFree

Open the audio settings in your meeting app and set the microphone to the name in NoiseFree's green box. Click **Copy name** if you want to paste it into a search field.

| App | Where the setting is |
|---|---|
| Microsoft Teams | Profile picture → **Settings** → **Devices** → **Microphone** |
| Zoom | **Settings** → **Audio** → **Microphone** |
| Discord | **User Settings** → **Voice & Video** → **Input Device** |
| Google Meet | During a call: **⋮** → **Settings** → **Audio** → **Microphone** |
| OBS Studio | **Settings** → **Audio** → **Mic/Auxiliary Audio** |

Pick:

- **CABLE Output** on Windows
- **BlackHole 2ch** on macOS
- **NoiseFree Microphone** on Linux

### 4. Turn off the meeting app's own noise suppression

Teams, Zoom and Discord all have their own noise filters. Running two at once can make your voice sound watery. Set theirs to **Off** or **Low**:

- Teams: **Devices** → **Noise suppression** → **Off**
- Zoom: **Audio** → **Background noise suppression** → **Low**
- Discord: **Voice & Video** → **Noise Suppression** → **None**

### 5. Make a test call

Zoom has a test at **Settings** → **Audio** → **Test Mic**; Teams has **Make a test call** under **Devices**. Speak with your noise source on (a fan, typing) and listen to the playback.

## What's next

- Leave NoiseFree running. Closing the window keeps it in the system tray, so your calls keep working.
- Turn on **Open when I sign in** in [Settings](Configuration) so you never have to think about it.
- If your voice sounds thin or muffled, lower **Strength**. See [Using NoiseFree](Usage#strength).
