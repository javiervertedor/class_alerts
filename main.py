import json
import time
import wave
import datetime
import tkinter as tk
import winsound
import os
import sys
import psutil
import threading
from threading import Thread
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Base directory of the running script. When Windows starts apps at login the
# current working directory may be different, so always resolve files relative
# to the script location.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def resolve_path(p):
    """Return an absolute path for p. If p is already absolute return it as-is,
    otherwise join it with BASE_DIR.
    """
    if not p:
        return p
    if os.path.isabs(p):
        return p
    return os.path.join(BASE_DIR, p)

class SingleInstance:
    """Ensure only one instance of the program is running."""
    def __init__(self):
        self.lockfile = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'class_alerts.lock'))
        
    def check(self):
        try:
            if os.path.exists(self.lockfile):
                # Check if process is actually running
                with open(self.lockfile, 'r') as f:
                    pid = int(f.read().strip())
                try:
                    # Check if the process is still running
                    if psutil.Process(pid).is_running():
                        return False
                except psutil.NoSuchProcess:
                    pass  # Process not found, we can proceed
            
            # Write current process ID to lockfile
            with open(self.lockfile, 'w') as f:
                f.write(str(os.getpid()))
            return True
            
        except Exception as e:
            print(f"Error checking single instance: {e}")
            return True
            
    def cleanup(self):
        try:
            if os.path.exists(self.lockfile):
                os.remove(self.lockfile)
        except:
            pass

class ConfigWatcher:
    """Watch for changes in the config file and reload when necessary."""
    def __init__(self):
        # Use absolute path to the config file (script directory). This fixes
        # the issue when Windows starts the app and the current working
        # directory is not the script folder.
        self.config_path = resolve_path("config.json")
        try:
            self.last_modified = os.path.getmtime(self.config_path)
        except Exception:
            self.last_modified = 0
        self.load_config()
        
    def load_config(self):
        global SOUNDS, BANNER, MESSAGE, SCHEDULE
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            SOUNDS = config["sounds"]
            BANNER = config["banner"]
            MESSAGE = config["message_settings"]
            SCHEDULE = config["schedule"]
            print("Configuration loaded successfully")
        except Exception as e:
            print(f"Error loading configuration: {e}")
            # Ensure sensible defaults so other parts of the program can run
            SOUNDS = {
                "start": "sounds/start.wav",
                "start_repetition": 1,
                "before_end": "sounds/warning.wav",
                "before_end_repetition": 1,
                "end": "sounds/end.wav",
                "end_repetition": 1,
            }
            BANNER = {"frame_thickness": 4}
            MESSAGE = {
                "font_family": "Segoe UI",
                "font_size": 42,
                "font_weight": "bold",
                "color_start": "#FFFFFF",
                "color_before_end": "#FFFFFF",
                "color_end": "#FFFFFF",
                "banner_start": "#2196F3",
                "banner_before_end": "#00BCD4",
                "banner_end": "#9C27B0",
            }
            SCHEDULE = {}
            
    def check_config(self):
        try:
            current_mtime = os.path.getmtime(self.config_path)
            if current_mtime > self.last_modified:
                print("Config file changed, reloading...")
                self.load_config()
                self.last_modified = current_mtime
        except Exception as e:
            print(f"Error checking config: {e}")

# Initialize configuration
# Provide safe defaults so the module-level names exist even if config fails to
# load (prevents NameError when the watcher cannot read the file at startup).
SOUNDS = {}
BANNER = {"frame_thickness": 4}
MESSAGE = {
    "font_family": "Segoe UI",
    "font_size": 42,
    "font_weight": "bold",
    "color_start": "#FFFFFF",
    "color_before_end": "#FFFFFF",
    "color_end": "#FFFFFF",
    "banner_start": "#2196F3",
    "banner_before_end": "#00BCD4",
    "banner_end": "#9C27B0",
}
SCHEDULE = {}

config_watcher = ConfigWatcher()

def get_wav_duration(wav_path):
    """Get the duration of a WAV file in seconds."""
    try:
        wav_path = resolve_path(wav_path)
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
            sp = resolve_path(sound_path)
            winsound.PlaySound(sp, winsound.SND_FILENAME)
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
        try:
            # Check for config changes
            config_watcher.check_config()
            
            now = datetime.datetime.now()
            weekday = now.strftime("%A")
        except Exception as e:
            print(f"Error in schedule check: {e}")
            time.sleep(60)  # Wait a minute before retrying
            continue

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

def main():
    # Check if another instance is running
    instance = SingleInstance()
    if not instance.check():
        print("Another instance is already running")
        sys.exit(1)

    try:
        # Reduce CPU priority
        p = psutil.Process(os.getpid())
        if os.name == 'nt':  # Windows
            p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        else:  # Unix-like
            p.nice(10)  # Lower priority (higher nice value)

        # Start the schedule checker
        check_schedule()
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    finally:
        instance.cleanup()

if __name__ == "__main__":
    main()
