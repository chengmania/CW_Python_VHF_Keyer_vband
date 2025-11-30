# CW Repeater Keyer (Python + vBand)

This project lets you send manual or iambic CW over an FM rig or repeater using:

- A **Ham Radio Solutions vBand USB keyer** (keyboard style dongle)
- A **USB audio interface** into your radio
- A **serial PTT interface** (RTS line)
- A **Python keyer app** with straight and iambic modes

You can also use it in **speaker practice mode** with no radio at all.

---

## Features

- Straight key mode and simple iambic mode
- Adjustable WPM
- Adjustable tone frequency
- Adjustable output level (for fussy FM audio chains)
- PTT toggle using RTS on a serial port
- Bypass mode for practice on local speakers
- Uses the vBand USB keyer as a HID keyboard source

The current tested “clean sounding” setup for one FM rig used an output level of `0.009`.

---

## Requirements

Tested on Linux with:

- Python 3.10 or newer
- System audio using ALSA or PulseAudio

Dependencies (installed in the virtual environment):

- `sounddevice`
- `numpy`
- `pyserial`
- `tk`

On Debian or Ubuntu you will probably need:

```bash
sudo apt install python3-venv python3-tk python3-dev portaudio19-dev
````

Setting up a Python virtual environment
From the project root (where cw_repeater_keyer.py lives):

````bash
python3 -m venv .venv
source .venv/bin/activate
````
You should now see something like (.venv) at the start of your shell prompt.

Install the Python dependencies:

````bash
pip install --upgrade pip
pip install sounddevice numpy pyserial
````
To leave the virtual environment later:

````bash
deactivate
````
Each time you want to run the program in a new shell:

````bash

cd /path/to/this/project
source .venv/bin/activate
python cw_repeater_keyer.py
````
## vBand USB keyer setup
The Ham Radio Solutions vBand USB paddle interface appears as a USB keyboard.

By default it sends keystrokes such as [ and ] (and sometimes Control keys) when you press the paddles.

This app listens for:

-Dit paddle: [ or Left Control 
-Dah paddle: ] or Right Control

So the setup is usually:

1. Plug in the vBand USB keyer.
2. Make sure your window manager is not binding [ or ] or Control combinations to any global shortcuts.
3. Give focus to the CW Keyer window before sending with the paddles.

If paddles do nothing, try tapping [ and ] on your keyboard manually. If that works, the vBand dongle should work once focus is on the keyer window.

## Radio and audio wiring
You will need:

- A USB sound interface connected to the mic input or data port of your FM radio.
- A USB to serial adapter (or similar) wired so that the RTS line keys PTT.

Typical flow:

1. Computer audio out (USB soundcard)
→ audio in on radio (mic, data, or accessory port).
2 USB serial adapter RTS
→ PTT input on radio (follow the PTT wiring for your radio, usually open collector to ground).

Level setting:

- Keep the app output level low. Values around 0.005 to 0.02 tend to behave best.
- Then adjust your soundcard output level and radio mic gain for a clean sounding tone.

# Running the program
From an activated virtual environment:

````bash
python cw_repeater_keyer.py
````
You should see the CW Repeater Keyer window.

# Basic configuration
1. Audio output device
 - Choose the sound device that feeds your radio or speakers.
 - For local speakers this is usually something like sysdefault or pulse.
2. PTT serial port
 - Choose the serial device that controls PTT (/dev/ttyUSB0, /dev/ttyACM0, etc).
 - This is only used when bypass is off.
3. Bypass PTT (speaker practice)
 - Checked: Tone goes straight to speakers. No PTT. Serial port is ignored.
 - Unchecked: Tone only goes out when PTT is on and tone is active.
4. Keyer mode
 - Straight: Tone follows paddle timing directly.
 - Iambic: Simple iambic timing, WPM controlled by the app.
5. Speed (WPM)
 - Dit length is 1.2 / WPM seconds.
 - Dah is 3 dits. Element gaps are 1 dit.
6. Tone frequency (Hz)
  - Common values: 500, 600, 700, 800.
7. Output level (0.000 – 0.200)
 - Master amplitude of the sine wave.
 - For computer speakers: try 0.05 to 0.15.
 - For FM radio: start around 0.01, adjust down if audio still sounds squashed.

When settings look correct, click Apply settings.

## Using the app
### Radio mode (repeater use)
1. Uncheck Bypass PTT.
2. Select:
 - Audio device feeding the radio.
 - Serial port for PTT.
3. Set WPM, tone, and a conservative output level (for example 0.009).
4. Click Apply settings.
5. Click PTT (toggle) or press the space bar to key the radio:
 - PTT toggles on and off.
 - Status shows “Transmitting CW” while PTT is on.
6. Use your paddle on the vBand keyer to send CW.

# Practice mode (local speakers)
1. Select your speaker output device in the audio device list.
2. Check Bypass PTT (speaker practice).
3. Click Apply settings.
4. Key with the paddle. The tone should come out of your speakers with no PTT and no serial requirement.

# Key mapping summary
- Dit:
  - [ key
- Dah:
  - ] key

You can also use a regular keyboard for testing before plugging in the vBand dongle.

# Tips for clean audio on FM
FM rigs and repeaters often have aggressive audio processing. To reduce “wah wit wah” sounding CW on the air:
- Keep the output level in the app low (0.005 to 0.02).
- Turn off any speech processor or compressor in the radio.
- Use a moderate tone frequency (500 to 700 Hz).
- Do on air checks at different levels:
-- If audio gets cleaner as you lower the level, you were overdriving the radio.
-- Many rigs behave best with surprisingly low input from the soundcard.

One tested rig sounded cleanest around an app output level of 0.009.

## Troubleshooting
No tone at all
- Make sure the correct audio device is selected and you clicked Apply settings.
- Ensure the GUI window has focus, then tap [ and ] on the keyboard.
- In radio mode, make sure Bypass is unchecked and PTT is on.

No PTT
- Confirm the correct serial port.
- Click Apply settings after selecting the port.
- Verify that RTS on the adapter is actually wired to the PTT line.

Paddles not doing anything
- Confirm the app window has focus.
- Tap [ and ] on the physical keyboard. If those work, check what keys the vBand dongle is really sending.
- Check that your desktop environment is not intercepting those keys for hotkeys.

#License
MIT License

Copyright (c) 2025  Gregory P. Cheng KC3SMW

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to
deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/ or
sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
IN THE SOFTWARE.

