import json
import time
import wave
import datetime
import tkinter as tk
import winsound
from threading import Thread

# --- Cargar configuración desde JSON ---
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

SOUNDS = config["sounds"]
BANNER = config["banner"]
MESSAGE = config["message_settings"]
SCHEDULE = config["schedule"]

def get_wav_duration(wav_path):
    """Get the duration of a WAV file in seconds."""
    try:
        with wave.open(wav_path, 'rb') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            duration = frames / float(rate)
            return duration
    except:
        return 2  # Default duration if cannot read file

def play_sound(sound_path, repetitions=1):
    """Reproduce un sonido varias veces sin bloquear el programa."""
    def _play():
        for _ in range(repetitions):
            # Play sound synchronously to ensure one completes before the next starts
            winsound.PlaySound(sound_path, winsound.SND_FILENAME)
    Thread(target=_play, daemon=True).start()

def show_message(text, banner_color, text_color, sound_path=None, repetitions=1):
    """Muestra un marco translúcido con texto en la parte superior."""
    frame_thickness = BANNER["frame_thickness"]
    
    # Calculate banner duration based on actual sound duration and repetitions
    if sound_path:
        sound_duration = get_wav_duration(sound_path)
        duration = max(5, sound_duration * repetitions + 1)  # Add 1 second buffer
    else:
        duration = 5  # Default duration if no sound
    transparency = 0.7

    root = tk.Tk()
    root.attributes("-topmost", True)
    root.overrideredirect(True)
    root.attributes("-alpha", transparency)

    width, height = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"{width}x{height}+0+0")

    # Bordes del marco
    edges = {
        "top":    (0, 0, width, frame_thickness),
        "bottom": (0, height - frame_thickness, width, frame_thickness),
        "left":   (0, 0, frame_thickness, height),
        "right":  (width - frame_thickness, 0, frame_thickness, height)
    }

    for _, (x, y, w, h) in edges.items():
        edge = tk.Frame(root, bg=banner_color)
        edge.place(x=x, y=y, width=w, height=h)

    # Texto flotante
    label = tk.Label(
        root,
        text=text,
        font=(MESSAGE["font_family"], MESSAGE["font_size"], MESSAGE["font_weight"]),
        fg=text_color,
        bg=banner_color
    )
    label.place(x=width // 2, y=frame_thickness * 2, anchor="n")

    # Cerrar automáticamente
    root.after(int(duration * 1000), root.destroy)
    root.mainloop()

def check_schedule():
    """Verifica continuamente el horario y lanza alertas."""
    triggered = set()
    while True:
        now = datetime.datetime.now()
        weekday = now.strftime("%A")

        if weekday in SCHEDULE:
            for event in SCHEDULE[weekday]:
                name = event["name"]
                start_time = datetime.datetime.strptime(event["start"], "%H:%M").time()
                end_time = datetime.datetime.strptime(event["end"], "%H:%M").time()
                alerts = event["alerts"]

                # --- START alert ---
                key = f"{weekday}-{name}-start"
                if alerts.get("start") and key not in triggered and now.time().strftime("%H:%M") == start_time.strftime("%H:%M"):
                    triggered.add(key)
                    play_sound(SOUNDS["start"], SOUNDS.get("start_repetition", 1))
                    show_message(f"🔔 {name} starts now!", MESSAGE["banner_start"], MESSAGE["color_start"], 
                               SOUNDS["start"], SOUNDS.get("start_repetition", 1))

                # --- BEFORE END alert ---
                if alerts.get("before_end"):
                    minutes_before = alerts["before_end"]
                    before_end_time = (datetime.datetime.combine(datetime.date.today(), end_time)
                                       - datetime.timedelta(minutes=minutes_before)).time()
                    key = f"{weekday}-{name}-before_end"
                    if key not in triggered and now.time().strftime("%H:%M") == before_end_time.strftime("%H:%M"):
                        triggered.add(key)
                        play_sound(SOUNDS["before_end"], SOUNDS.get("before_end_repetition", 1))
                        show_message(f"⚠️ {name} ends in {minutes_before} min", MESSAGE["banner_before_end"], MESSAGE["color_before_end"],
                                   SOUNDS["before_end"], SOUNDS.get("before_end_repetition", 1))

                # --- END alert ---
                key = f"{weekday}-{name}-end"
                if alerts.get("end") and key not in triggered and now.time().strftime("%H:%M") == end_time.strftime("%H:%M"):
                    triggered.add(key)
                    play_sound(SOUNDS["end"], SOUNDS.get("end_repetition", 1))
                    show_message(f"🏁 {name} has ended", MESSAGE["banner_end"], MESSAGE["color_end"],
                               SOUNDS["end"], SOUNDS.get("end_repetition", 1))

        time.sleep(20)

if __name__ == "__main__":
    check_schedule()
