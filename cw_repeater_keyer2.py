import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import sounddevice as sd
import serial
import serial.tools.list_ports
import math

# Global state
audio_stream = None
audio_device_index = None
sample_rate = 48000.0
tone_freq = 700.0

# Audio control
tone_on = False          # What the audio callback uses
tone_request = False     # What the keyer engine wants
ptt_active = False
bypass_ptt = False       # When True, ignore PTT and just follow keyer
output_gain = 0.01       # Master output level (0.0 to about 0.3 is sensible)

# Sine generator phase in radians
tone_phase = 0.0

# Straight key state
key_down = False

# Iambic keyer state
wpm = 20.0
dit_len = 1.2 / wpm      # seconds
keyer_mode = "Straight"  # "Straight" or "Iambic"
paddle_dit = False
paddle_dah = False
keyer_state = "IDLE"     # "IDLE", "DIT", "DAH", "GAP"
last_element = "DAH"     # For alternating when both paddles are held

root_app = None  # Tk root for timers and UI sync

ser = None  # serial.Serial instance for PTT, or None


def update_tone_output():
    """Combine keyer request with PTT and bypass to decide if audio should sound."""
    global tone_on, bypass_ptt, ptt_active, tone_request
    if bypass_ptt:
        tone_on = tone_request
    else:
        tone_on = tone_request and ptt_active


def list_audio_devices():
    devices = sd.query_devices()
    outputs = []
    for idx, dev in enumerate(devices):
        if dev["max_output_channels"] > 0:
            label = f"{idx}: {dev['name']}"
            outputs.append((label, idx))
    return outputs


def list_serial_ports():
    ports = serial.tools.list_ports.comports()
    return [p.device for p in ports]


def audio_callback(outdata, frames, time_info, status):
    """Generate a clean continuous sine tone when tone_on is True."""
    global tone_on, tone_freq, sample_rate, tone_phase, output_gain

    if status:
        pass

    out = np.zeros((frames, 1), dtype=np.float32)

    if tone_on:
        phase_increment = 2.0 * math.pi * tone_freq / sample_rate
        n = np.arange(frames, dtype=np.float32)
        phase_array = tone_phase + phase_increment * n
        wave = np.sin(phase_array).astype(np.float32)
        out[:, 0] = output_gain * wave
        tone_phase = (phase_array[-1] + phase_increment) % (2.0 * math.pi)

    outdata[:] = out


def start_audio_stream():
    global audio_stream, audio_device_index
    if audio_stream is not None:
        return

    if audio_device_index is None:
        messagebox.showerror("Audio error", "No audio device selected")
        return

    try:
        audio_stream = sd.OutputStream(
            device=audio_device_index,
            channels=1,
            samplerate=int(sample_rate),
            dtype="float32",
            callback=audio_callback,
            blocksize=256,
            latency="low",
        )
        audio_stream.start()
    except Exception as e:
        messagebox.showerror("Audio error", f"Could not open audio device:\n{e}")
        audio_stream = None


def stop_audio_stream():
    global audio_stream
    if audio_stream is not None:
        audio_stream.stop()
        audio_stream.close()
        audio_stream = None


def open_serial(port_name):
    global ser
    if not port_name:
        return
    try:
        ser = serial.Serial(port_name, baudrate=9600, timeout=1)
        ser.rts = False
    except Exception as e:
        messagebox.showerror("Serial error", f"Could not open serial port:\n{e}")
        ser = None


def close_serial():
    global ser
    if ser is not None:
        try:
            ser.rts = False
            ser.close()
        except Exception:
            pass
        ser = None


def set_ptt(active):
    global ptt_active
    ptt_active = active

    if ser is not None:
        try:
            ser.rts = active
        except Exception:
            pass

    update_tone_output()


def toggle_ptt():
    """Toggle PTT on or off and sync the UI."""
    global root_app

    if bypass_ptt:
        # In bypass mode PTT is meaningless
        if root_app is not None:
            messagebox.showinfo("PTT disabled", "PTT is disabled in practice mode.\nUncheck bypass to key the radio.")
        return

    if ser is None:
        if root_app is not None:
            messagebox.showerror("PTT error", "No serial port open. Click Apply after selecting a PTT port.")
        return

    set_ptt(not ptt_active)

    if root_app is not None:
        if ptt_active:
            root_app.status_var.set("Transmitting CW")
            root_app.ptt_button.config(relief=tk.SUNKEN)
        else:
            root_app.status_var.set("Idle")
            root_app.ptt_button.config(relief=tk.RAISED)


# IAMBIC KEYER ENGINE
def start_next_element():
    """Start the next dit or dah based on paddle state and iambic rules."""
    global keyer_state, last_element, root_app
    global paddle_dit, paddle_dah, dit_len, keyer_mode

    if keyer_mode != "Iambic":
        return

    if root_app is None:
        return

    if not (paddle_dit or paddle_dah):
        keyer_state = "IDLE"
        return

    if paddle_dit and not paddle_dah:
        kind = "DIT"
    elif paddle_dah and not paddle_dit:
        kind = "DAH"
    else:
        if last_element == "DIT":
            kind = "DAH"
        else:
            kind = "DIT"

    last_element = kind
    keyer_state = kind

    length_sec = dit_len * (3 if kind == "DAH" else 1)
    ms = int(length_sec * 1000)

    set_tone_request(True)
    root_app.after(ms, end_element)


def end_element():
    """End the current element and start the intra-element gap."""
    global keyer_state, root_app

    if root_app is None:
        return

    keyer_state = "GAP"
    set_tone_request(False)

    gap_ms = int(dit_len * 1000)
    root_app.after(gap_ms, gap_done)


def gap_done():
    """After the gap, decide if another element should start."""
    global keyer_state
    keyer_state = "IDLE"
    start_next_element()


def set_tone_request(active):
    """Set the underlying keyer tone request and update audio gate."""
    global tone_request
    tone_request = active
    update_tone_output()


def on_key_press(event):
    """Handle key presses from vBand adapter or keyboard."""
    global key_down, paddle_dit, paddle_dah, keyer_mode

    is_dit_key = event.keysym in ("bracketleft", "Control_L")
    is_dah_key = event.keysym in ("bracketright", "Control_R")

    if not (is_dit_key or is_dah_key):
        return

    if keyer_mode == "Straight":
        key_down = True
        set_tone_request(True)
    else:
        if is_dit_key:
            paddle_dit = True
        if is_dah_key:
            paddle_dah = True
        if keyer_state == "IDLE":
            start_next_element()


def on_key_release(event):
    """Handle key releases from vBand adapter or keyboard."""
    global key_down, paddle_dit, paddle_dah, keyer_mode

    is_dit_key = event.keysym in ("bracketleft", "Control_L")
    is_dah_key = event.keysym in ("bracketright", "Control_R")

    if not (is_dit_key or is_dah_key):
        return

    if keyer_mode == "Straight":
        key_down = False
        set_tone_request(False)
    else:
        if is_dit_key:
            paddle_dit = False
        if is_dah_key:
            paddle_dah = False


def on_space_press(event):
    """Space bar toggles PTT."""
    toggle_ptt()
    return "break"


class CWKeyerApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("CW Repeater Keyer")
        self.geometry("620x360")

        self.audio_devices = list_audio_devices()
        self.audio_map = {label: idx for (label, idx) in self.audio_devices}

        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(2, weight=0)

        # Row 0: audio output
        ttk.Label(main_frame, text="Audio output device:").grid(
            row=0, column=0, sticky="w"
        )
        self.audio_combo = ttk.Combobox(
            main_frame,
            width=40,
            state="readonly",
            values=[a[0] for a in self.audio_devices],
        )
        self.audio_combo.grid(row=0, column=1, columnspan=2, sticky="ew", padx=5)

        # Row 1: PTT serial + bypass
        ttk.Label(main_frame, text="PTT serial port:").grid(row=1, column=0, sticky="w")
        ports = list_serial_ports()
        self.serial_combo = ttk.Combobox(
            main_frame, width=25, state="readonly", values=ports
        )
        self.serial_combo.grid(row=1, column=1, sticky="w", padx=5)

        self.bypass_var = tk.BooleanVar(value=False)
        self.bypass_check = ttk.Checkbutton(
            main_frame,
            text="Bypass PTT (speaker practice)",
            variable=self.bypass_var,
            command=self.on_bypass_toggle,
        )
        self.bypass_check.grid(row=1, column=2, sticky="w", padx=5)

        # Row 2: Keyer mode
        ttk.Label(main_frame, text="Keyer mode:").grid(row=2, column=0, sticky="w")
        self.mode_var = tk.StringVar(value="Straight")
        self.mode_combo = ttk.Combobox(
            main_frame,
            width=20,
            state="readonly",
            values=["Straight", "Iambic"],
            textvariable=self.mode_var,
        )
        self.mode_combo.grid(row=2, column=1, sticky="w", padx=5)

        # Row 3: Speed
        ttk.Label(main_frame, text="Speed (WPM):").grid(row=3, column=0, sticky="w")
        self.wpm_var = tk.StringVar(value="20")
        self.wpm_entry = ttk.Entry(main_frame, textvariable=self.wpm_var, width=10)
        self.wpm_entry.grid(row=3, column=1, sticky="w", padx=5)

        # Row 4: Tone frequency
        ttk.Label(main_frame, text="Tone frequency (Hz):").grid(
            row=4, column=0, sticky="w"
        )
        self.freq_var = tk.StringVar(value=str(int(tone_freq)))
        self.freq_entry = ttk.Entry(main_frame, textvariable=self.freq_var, width=10)
        self.freq_entry.grid(row=4, column=1, sticky="w", padx=5)

        # Row 5: Output level
        ttk.Label(main_frame, text="Output level (0.000 - 0.200):").grid(
            row=5, column=0, sticky="w"
        )
        self.level_var = tk.StringVar(value=str(output_gain))
        self.level_entry = ttk.Entry(main_frame, textvariable=self.level_var, width=10)
        self.level_entry.grid(row=5, column=1, sticky="w", padx=5)

        # Row 6: Apply button
        self.apply_button = ttk.Button(
            main_frame, text="Apply settings", command=self.apply_settings
        )
        self.apply_button.grid(row=6, column=0, columnspan=3, sticky="we", pady=(8, 4))

        # Row 7: Status
        self.status_var = tk.StringVar(value="Idle")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var)
        self.status_label.grid(row=7, column=0, columnspan=3, sticky="w", pady=(8, 4))

        # Row 8: PTT button
        self.ptt_button = tk.Button(
            main_frame,
            text="PTT (toggle)",
            bg="red",
            fg="white",
            activebackground="darkred",
            width=20,
        )
        self.ptt_button.grid(row=8, column=0, columnspan=3, pady=10)
        self.ptt_button.bind("<Button-1>", self.on_ptt_click)

        # Menu
        menubar = tk.Menu(self)
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(
            label="Key info",
            command=lambda: messagebox.showinfo(
                "Key info",
                "vBand adapter sends paddle events as keyboard keys.\n"
                "This app listens for [ and ] (or Ctrl keys) as dits and dahs.\n"
                "Apply settings, then:\n"
                "• Use PTT + radio mode for repeater.\n"
                "• Use bypass mode to practice on speakers.",
            ),
        )
        menubar.add_cascade(label="Help", menu=helpmenu)
        self.config(menu=menubar)

        # Key bindings
        self.bind_all("<KeyPress>", self._dispatch_key_press)
        self.bind_all("<KeyRelease>", self._dispatch_key_release)
        self.bind_all("<KeyPress-space>", on_space_press)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _dispatch_key_press(self, event):
        on_key_press(event)

    def _dispatch_key_release(self, event):
        on_key_release(event)

    def on_ptt_click(self, event):
        toggle_ptt()

    def on_bypass_toggle(self):
        global bypass_ptt

        bypass_ptt = self.bypass_var.get()

        # When toggling modes, ensure PTT is off
        set_ptt(False)
        self.ptt_button.config(relief=tk.RAISED)

        if bypass_ptt:
            self.status_var.set("Practice mode - speakers")
        else:
            self.status_var.set("Idle")

        update_tone_output()

    def apply_settings(self):
        global audio_device_index, tone_freq
        global keyer_mode, wpm, dit_len, sample_rate, output_gain

        # Always stop stream before reconfig
        stop_audio_stream()

        # Tone frequency
        try:
            f = float(self.freq_var.get())
            if f <= 0:
                raise ValueError
            tone_freq = f
        except ValueError:
            messagebox.showerror("Frequency error", "Tone frequency must be a positive number")
            self.freq_var.set(str(int(tone_freq)))

        # WPM
        try:
            new_wpm = float(self.wpm_var.get())
            if new_wpm <= 0:
                raise ValueError
            wpm = new_wpm
            dit_len_val = 1.2 / wpm
        except ValueError:
            messagebox.showerror("WPM error", "Speed must be a positive number")
            self.wpm_var.set(str(int(wpm)))
            dit_len_val = 1.2 / wpm

        dit_len = dit_len_val

        # Output level
        try:
            lvl = float(self.level_var.get())
            if lvl < 0.0 or lvl > 0.2:
                raise ValueError
            output_gain = lvl
        except ValueError:
            messagebox.showerror("Level error", "Output level should be between 0.0 and 0.2")
            self.level_var.set(str(output_gain))

        # Keyer mode
        mode = self.mode_var.get()
        if mode not in ("Straight", "Iambic"):
            mode = "Straight"
            self.mode_var.set(mode)
        keyer_mode = mode

        # Audio device
        label = self.audio_combo.get()
        if label:
            audio_device_index = self.audio_map.get(label)
        else:
            audio_device_index = None

        # Sample rate from device
        if audio_device_index is not None:
            try:
                dev_info = sd.query_devices(audio_device_index)
                sr = dev_info.get("default_samplerate", None)
                if sr:
                    sample_rate = float(sr)
            except Exception:
                pass

        # Serial port (only if not in bypass mode)
        close_serial()
        if not self.bypass_var.get():
            port_name = self.serial_combo.get()
            if port_name:
                open_serial(port_name)

        # Start audio for either mode
        if audio_device_index is not None:
            start_audio_stream()

        self.status_var.set("Settings applied")

    def on_close(self):
        set_ptt(False)
        stop_audio_stream()
        close_serial()
        self.destroy()


def main():
    global root_app
    app = CWKeyerApp()
    root_app = app
    app.mainloop()


if __name__ == "__main__":
    main()
