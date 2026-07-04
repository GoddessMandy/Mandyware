"""
Desktop Companion - a small productivity/habit-building buddy.

Windows only (uses ctypes calls to Windows APIs for wallpaper swapping).
No external dependencies - just the Python standard library.

Run with:  python desktop_companion.py
Package to .exe (optional, on Windows) with:
    pip install pyinstaller
    pyinstaller --onefile --windowed --name "DesktopCompanion" desktop_companion.py
"""

import ctypes
import json
import os
import random
import sys
import time
import atexit
import tkinter as tk
from tkinter import ttk
from datetime import date, datetime

# --------------------------------------------------------------------------
# Storage
# --------------------------------------------------------------------------

APP_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "DesktopCompanion")
os.makedirs(APP_DIR, exist_ok=True)
SETTINGS_PATH = os.path.join(APP_DIR, "settings.json")
HISTORY_PATH = os.path.join(APP_DIR, "history.json")

DEFAULT_SETTINGS = {
    "intensity": 2,          # 1 = passive, 2 = moderate, 3 = active
    "theme": "calm",
    "wallpaper_swap_enabled": True,
    "wallpaper_choice": None,  # path to a wallpaper the user wants used while app runs
}

THEMES = {
    "calm":    {"bg": "#eef3f7", "fg": "#22303c", "accent": "#4f8fd1", "accent_fg": "#ffffff"},
    "forest":  {"bg": "#eef5ee", "fg": "#20361f", "accent": "#4c8c4a", "accent_fg": "#ffffff"},
    "sunset":  {"bg": "#fdf1e6", "fg": "#3a2418", "accent": "#e08a3c", "accent_fg": "#ffffff"},
    "midnight":{"bg": "#1e2129", "fg": "#e7e9ee", "accent": "#7a86ff", "accent_fg": "#ffffff"},
}

AFFIRMATIONS = [
    "Tomorrow is a fresh start.",
    "One off day doesn't erase your progress.",
    "You're allowed to reset and try again.",
    "Small consistent effort beats occasional perfection.",
    "You showed up here - that already counts for something.",
    "Progress isn't a straight line.",
    "Be as kind to yourself as you'd be to a friend.",
    "You're building something real, one day at a time.",
    "Rest and reset. Then go again.",
    "Noticing it is the first step to changing it.",
]

ENCOURAGEMENTS_GOOD = [
    "Nice work today. Keep the streak going!",
    "That's the way. Small wins add up.",
    "Proud of you for that one.",
    "Great, that's exactly the kind of day to repeat.",
]

TRIVIA = [
    ("Which habit-forming loop has 3 parts: cue, routine, reward?", ["The Habit Loop", "The Feedback Cycle", "The Motivation Triangle", "The Focus Chain"], 0),
    ("Roughly how long do studies suggest it can take to form a new habit?", ["3 days", "2-8 months (varies)", "exactly 21 days", "1 year minimum"], 1),
    ("Which of these best improves memory consolidation after studying?", ["Sleep", "Skipping meals", "Multitasking", "Loud music"], 0),
    ("The 'Pomodoro Technique' typically uses work intervals of about:", ["5 minutes", "25 minutes", "90 minutes", "3 hours"], 1),
    ("Which is a well-supported way to reduce procrastination?", ["Breaking tasks into small steps", "Waiting for motivation", "Multitasking more", "Setting vague goals"], 0),
    ("Regular moderate exercise is most consistently linked to improvements in:", ["Mood and focus", "Eyesight", "Typing speed", "Memory loss"], 0),
]

BREATHING_PHASES = [("Breathe in...", 4), ("Hold...", 4), ("Breathe out...", 6), ("Hold...", 2)]


def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            return dict(default)
    return dict(default)


def save_json(path, data):
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


class HistoryStore:
    def __init__(self):
        self.data = load_json(HISTORY_PATH, {"days": {}, "streak": 0, "best_streak": 0})

    def record_day(self, mood, had_bad_day):
        today = date.today().isoformat()
        self.data["days"][today] = {
            "mood": mood,
            "bad_day": had_bad_day,
            "time": datetime.now().strftime("%H:%M"),
        }
        if had_bad_day:
            self.data["streak"] = 0
        else:
            self.data["streak"] = self.data.get("streak", 0) + 1
            self.data["best_streak"] = max(self.data.get("best_streak", 0), self.data["streak"])
        save_json(HISTORY_PATH, self.data)

    @property
    def streak(self):
        return self.data.get("streak", 0)

    @property
    def best_streak(self):
        return self.data.get("best_streak", 0)

    def reset(self):
        self.data = {"days": {}, "streak": 0, "best_streak": 0}
        save_json(HISTORY_PATH, self.data)


# --------------------------------------------------------------------------
# Windows wallpaper handling
# --------------------------------------------------------------------------

SPI_SETDESKWALLPAPER = 20
SPI_GETDESKWALLPAPER = 0x0073
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDCHANGE = 0x02


class WallpaperManager:
    def __init__(self):
        self.original_path = None
        self.is_windows = sys.platform.startswith("win")
        if self.is_windows:
            try:
                buf = ctypes.create_unicode_buffer(260)
                ctypes.windll.user32.SystemParametersInfoW(SPI_GETDESKWALLPAPER, 260, buf, 0)
                self.original_path = buf.value
            except Exception:
                self.original_path = None

    def set_wallpaper(self, path):
        if not self.is_windows or not path or not os.path.exists(path):
            return False
        try:
            ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETDESKWALLPAPER, 0, path, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
            )
            return True
        except Exception:
            return False

    def revert(self):
        if self.is_windows and self.original_path:
            self.set_wallpaper(self.original_path)


# --------------------------------------------------------------------------
# Minigames
# --------------------------------------------------------------------------

class MemoryMatchGame(tk.Toplevel):
    def __init__(self, master, theme):
        super().__init__(master)
        self.title("Memory Match")
        self.theme = theme
        self.configure(bg=theme["bg"])
        self.resizable(False, False)
        symbols = ["★", "●", "▲", "■", "♥", "♦", "◆", "✚"]
        pairs = symbols * 2
        random.shuffle(pairs)
        self.cards = pairs
        self.buttons = []
        self.revealed = []
        self.matched = set()
        grid = tk.Frame(self, bg=theme["bg"])
        grid.pack(padx=10, pady=10)
        for i in range(16):
            b = tk.Button(
                grid, text="?", width=4, height=2, font=("Segoe UI", 14, "bold"),
                bg=theme["accent"], fg=theme["accent_fg"],
                command=lambda i=i: self.flip(i),
            )
            b.grid(row=i // 4, column=i % 4, padx=4, pady=4)
            self.buttons.append(b)
        self.status = tk.Label(self, text="Find the matching pairs!", bg=theme["bg"], fg=theme["fg"])
        self.status.pack(pady=(0, 10))

    def flip(self, i):
        if i in self.matched or i in [r[0] for r in self.revealed] or len(self.revealed) >= 2:
            return
        self.buttons[i].config(text=self.cards[i])
        self.revealed.append((i, self.cards[i]))
        if len(self.revealed) == 2:
            self.after(500, self.check_match)

    def check_match(self):
        (i1, c1), (i2, c2) = self.revealed
        if c1 == c2:
            self.matched.add(i1)
            self.matched.add(i2)
            self.status.config(text="Match!")
        else:
            self.buttons[i1].config(text="?")
            self.buttons[i2].config(text="?")
            self.status.config(text="Try again")
        self.revealed = []
        if len(self.matched) == len(self.cards):
            self.status.config(text="You cleared the board! 🎉")


class ReactionTimeGame(tk.Toplevel):
    def __init__(self, master, theme):
        super().__init__(master)
        self.title("Reaction Time")
        self.theme = theme
        self.configure(bg=theme["bg"])
        self.geometry("320x220")
        self.resizable(False, False)
        self.label = tk.Label(self, text="Wait for green, then click fast!", bg=theme["bg"], fg=theme["fg"], font=("Segoe UI", 11))
        self.label.pack(pady=15)
        self.box = tk.Button(self, text="Wait...", width=20, height=6, bg="#c0392b", fg="white", command=self.click)
        self.box.pack()
        self.start_time = None
        self.ready = False
        delay = random.randint(1500, 4000)
        self.after(delay, self.go_green)

    def go_green(self):
        self.box.config(bg="#27ae60", text="CLICK!")
        self.start_time = time.time()
        self.ready = True

    def click(self):
        if not self.ready:
            self.label.config(text="Too soon! Try again next time.")
            return
        elapsed = (time.time() - self.start_time) * 1000
        self.label.config(text=f"Reaction time: {elapsed:.0f} ms")
        self.box.config(text="Nice!", bg=self.theme["accent"], state="disabled")


class TriviaGame(tk.Toplevel):
    def __init__(self, master, theme):
        super().__init__(master)
        self.title("Quick Trivia")
        self.theme = theme
        self.configure(bg=theme["bg"])
        self.geometry("380x260")
        self.resizable(False, False)
        self.q, self.options, self.correct = random.choice(TRIVIA)
        tk.Label(self, text=self.q, bg=theme["bg"], fg=theme["fg"], font=("Segoe UI", 11, "bold"),
                 wraplength=340, justify="left").pack(pady=15, padx=15)
        self.result = tk.Label(self, text="", bg=theme["bg"], fg=theme["fg"])
        self.result.pack(pady=(0, 5))
        for idx, opt in enumerate(self.options):
            tk.Button(self, text=opt, width=30, bg=theme["accent"], fg=theme["accent_fg"],
                      command=lambda idx=idx: self.answer(idx)).pack(pady=3)

    def answer(self, idx):
        if idx == self.correct:
            self.result.config(text="Correct! ✅")
        else:
            self.result.config(text=f"Not quite - it was: {self.options[self.correct]}")


class BreathingGame(tk.Toplevel):
    def __init__(self, master, theme):
        super().__init__(master)
        self.title("Breathing Break")
        self.theme = theme
        self.configure(bg=theme["bg"])
        self.geometry("320x320")
        self.resizable(False, False)
        self.canvas = tk.Canvas(self, width=280, height=220, bg=theme["bg"], highlightthickness=0)
        self.canvas.pack(pady=10)
        self.text = tk.Label(self, text="Get ready...", bg=theme["bg"], fg=theme["fg"], font=("Segoe UI", 13))
        self.text.pack()
        self.circle = self.canvas.create_oval(90, 60, 190, 160, fill=theme["accent"], outline="")
        self.phase_idx = 0
        self.after(500, self.run_phase)

    def run_phase(self):
        if self.phase_idx >= len(BREATHING_PHASES) * 2:  # two full cycles
            self.text.config(text="Nice reset. 🌿")
            return
        label, secs = BREATHING_PHASES[self.phase_idx % len(BREATHING_PHASES)]
        self.text.config(text=label)
        grow = "in" in label.lower()
        shrink = "out" in label.lower()
        steps = 20
        for s in range(steps):
            delay = int((secs * 1000 / steps) * s)
            if grow:
                self.after(delay, lambda s=s: self._resize(90 - s * 2, 60 - s * 2, 190 + s * 2, 160 + s * 2))
            elif shrink:
                self.after(delay, lambda s=s: self._resize(90 + s * 2, 60 + s * 2, 190 - s * 2, 160 - s * 2))
        self.phase_idx += 1
        self.after(secs * 1000, self.run_phase)

    def _resize(self, x1, y1, x2, y2):
        try:
            self.canvas.coords(self.circle, x1, y1, x2, y2)
        except tk.TclError:
            pass


# --------------------------------------------------------------------------
# Lockout / reset screen (self-imposed, always has an emergency skip)
# --------------------------------------------------------------------------

class LockoutScreen(tk.Toplevel):
    def __init__(self, master, theme, seconds=20):
        super().__init__(master)
        self.theme = theme
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        try:
            self.attributes("-alpha", 0.97)
        except tk.TclError:
            pass
        w = self.winfo_screenwidth()
        h = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+0+0")
        self.configure(bg=theme["bg"])
        self.seconds_left = seconds

        self.msg_label = tk.Label(
            self, text=random.choice(AFFIRMATIONS), font=("Segoe UI", 22, "bold"),
            bg=theme["bg"], fg=theme["fg"], wraplength=w - 200,
        )
        self.msg_label.place(relx=0.5, rely=0.42, anchor="center")

        self.timer_label = tk.Label(
            self, text=str(self.seconds_left), font=("Segoe UI", 40, "bold"),
            bg=theme["bg"], fg=theme["accent"],
        )
        self.timer_label.place(relx=0.5, rely=0.58, anchor="center")

        tk.Label(
            self, text="Taking a short reset. Press ESC any time to skip.",
            font=("Segoe UI", 10), bg=theme["bg"], fg=theme["fg"],
        ).place(relx=0.5, rely=0.7, anchor="center")

        self.bind("<Escape>", lambda e: self.destroy())
        self.focus_force()
        self._tick()

    def _tick(self):
        if self.seconds_left <= 0:
            self.destroy()
            return
        self.timer_label.config(text=str(self.seconds_left))
        if self.seconds_left % 5 == 0:
            self.msg_label.config(text=random.choice(AFFIRMATIONS))
        self.seconds_left -= 1
        self.after(1000, self._tick)


# --------------------------------------------------------------------------
# Main companion app
# --------------------------------------------------------------------------

INTENSITY_LABELS = {1: "Passive", 2: "Moderate", 3: "Active"}
INTENSITY_INTERVAL_MS = {1: 90 * 60 * 1000, 2: 45 * 60 * 1000, 3: 20 * 60 * 1000}
INTENSITY_TONE = {
    1: "No pressure - check in whenever you like.",
    2: "Just a friendly nudge to check in.",
    3: "Hey! Let's check in now, don't put it off.",
}

MOODS = ["Productive", "Okay", "Tired", "Stressed", "Lazy"]


class CompanionApp:
    def __init__(self):
        self.settings = load_json(SETTINGS_PATH, DEFAULT_SETTINGS)
        for k, v in DEFAULT_SETTINGS.items():
            self.settings.setdefault(k, v)
        self.history = HistoryStore()
        self.wallpaper_mgr = WallpaperManager()

        self.root = tk.Tk()
        self.root.title("Companion")
        self.root.geometry("260x300+80+80")
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)
        self.build_ui()
        self.apply_theme()

        atexit.register(self.on_exit)
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)

        if self.settings["wallpaper_swap_enabled"] and self.settings.get("wallpaper_choice"):
            self.wallpaper_mgr.set_wallpaper(self.settings["wallpaper_choice"])

        self.schedule_next_checkin()

    # ---------------- UI ----------------

    def build_ui(self):
        self.face_label = tk.Label(self.root, text="🙂", font=("Segoe UI Emoji", 40))
        self.face_label.pack(pady=(15, 5))

        self.streak_label = tk.Label(self.root, text="", font=("Segoe UI", 10, "bold"))
        self.streak_label.pack()

        self.status_label = tk.Label(self.root, text="Hi! I'm here whenever you're ready.", wraplength=220, justify="center")
        self.status_label.pack(pady=8)

        self.checkin_btn = tk.Button(self.root, text="Check in", command=self.start_checkin)
        self.checkin_btn.pack(pady=4, fill="x", padx=20)

        self.settings_btn = tk.Button(self.root, text="Settings", command=self.open_settings)
        self.settings_btn.pack(pady=4, fill="x", padx=20)

        self.quit_btn = tk.Button(self.root, text="Quit", command=self.on_exit)
        self.quit_btn.pack(pady=(4, 10), fill="x", padx=20)

        self.update_streak_label()

    def apply_theme(self):
        theme = THEMES[self.settings["theme"]]
        self.root.configure(bg=theme["bg"])
        for w in [self.face_label, self.streak_label, self.status_label]:
            w.configure(bg=theme["bg"], fg=theme["fg"])
        for b in [self.checkin_btn, self.settings_btn, self.quit_btn]:
            b.configure(bg=theme["accent"], fg=theme["accent_fg"], activebackground=theme["accent"])

    def update_streak_label(self):
        self.streak_label.config(text=f"Streak: {self.history.streak} day(s)  |  Best: {self.history.best_streak}")

    @property
    def theme(self):
        return THEMES[self.settings["theme"]]

    # ------------- scheduling -------------

    def schedule_next_checkin(self):
        interval = INTENSITY_INTERVAL_MS[self.settings["intensity"]]
        self.root.after(interval, self.proactive_checkin)

    def proactive_checkin(self):
        self.status_label.config(text=INTENSITY_TONE[self.settings["intensity"]])
        self.face_label.config(text="🙂")
        self.schedule_next_checkin()

    # ------------- check-in flow -------------

    def start_checkin(self):
        win = tk.Toplevel(self.root)
        win.title("Check in")
        win.configure(bg=self.theme["bg"])
        win.resizable(False, False)
        win.attributes("-topmost", True)

        tk.Label(win, text="How are you feeling today?", font=("Segoe UI", 12, "bold"),
                 bg=self.theme["bg"], fg=self.theme["fg"]).pack(padx=20, pady=(15, 10))

        for mood in MOODS:
            tk.Button(win, text=mood, width=20, bg=self.theme["accent"], fg=self.theme["accent_fg"],
                      command=lambda m=mood: self.mood_selected(win, m)).pack(pady=3, padx=20)

    def mood_selected(self, win, mood):
        win.destroy()
        self.ask_bad_day(mood)

    def ask_bad_day(self, mood):
        win = tk.Toplevel(self.root)
        win.title("Check in")
        win.configure(bg=self.theme["bg"])
        win.resizable(False, False)
        win.attributes("-topmost", True)

        tk.Label(win, text="Did anything unproductive/off-track happen today?",
                 font=("Segoe UI", 11, "bold"), wraplength=280, justify="center",
                 bg=self.theme["bg"], fg=self.theme["fg"]).pack(padx=20, pady=(15, 10))

        row = tk.Frame(win, bg=self.theme["bg"])
        row.pack(pady=(0, 15))
        tk.Button(row, text="Yes", width=10, bg=self.theme["accent"], fg=self.theme["accent_fg"],
                  command=lambda: self.finish_checkin(win, mood, True)).pack(side="left", padx=5)
        tk.Button(row, text="No", width=10, bg=self.theme["accent"], fg=self.theme["accent_fg"],
                  command=lambda: self.finish_checkin(win, mood, False)).pack(side="left", padx=5)

    def finish_checkin(self, win, mood, had_bad_day):
        win.destroy()
        self.history.record_day(mood, had_bad_day)
        self.update_streak_label()

        if had_bad_day:
            self.face_label.config(text="😌")
            self.status_label.config(text="That's okay. Taking a short reset.")
            LockoutScreen(self.root, self.theme, seconds=20)
        else:
            self.face_label.config(text="😄")
            self.status_label.config(text=random.choice(ENCOURAGEMENTS_GOOD))
            self.offer_minigame()

    def offer_minigame(self):
        win = tk.Toplevel(self.root)
        win.title("Nice work!")
        win.configure(bg=self.theme["bg"])
        win.resizable(False, False)
        win.attributes("-topmost", True)
        tk.Label(win, text="Want to play a quick game as a reward?", font=("Segoe UI", 11, "bold"),
                 wraplength=260, justify="center", bg=self.theme["bg"], fg=self.theme["fg"]).pack(padx=20, pady=(15, 10))

        games = {
            "Memory Match": MemoryMatchGame,
            "Reaction Time": ReactionTimeGame,
            "Trivia": TriviaGame,
            "Breathing Break": BreathingGame,
        }
        for name, cls in games.items():
            tk.Button(win, text=name, width=22, bg=self.theme["accent"], fg=self.theme["accent_fg"],
                      command=lambda c=cls, w=win: (w.destroy(), c(self.root, self.theme))).pack(pady=3, padx=20)
        tk.Button(win, text="No thanks", width=22, command=win.destroy).pack(pady=(3, 15), padx=20)

    # ------------- settings -------------

    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.configure(bg=self.theme["bg"])
        win.resizable(False, False)
        win.attributes("-topmost", True)

        tk.Label(win, text="Encouragement intensity", font=("Segoe UI", 10, "bold"),
                 bg=self.theme["bg"], fg=self.theme["fg"]).pack(pady=(15, 2), padx=20)
        intensity_var = tk.IntVar(value=self.settings["intensity"])
        scale = tk.Scale(win, from_=1, to=3, orient="horizontal", variable=intensity_var,
                          showvalue=False, length=200, bg=self.theme["bg"], fg=self.theme["fg"],
                          troughcolor=self.theme["accent"], highlightthickness=0)
        scale.pack(padx=20)
        label = tk.Label(win, text=INTENSITY_LABELS[intensity_var.get()], bg=self.theme["bg"], fg=self.theme["fg"])
        label.pack()

        def on_scale(_):
            label.config(text=INTENSITY_LABELS[intensity_var.get()])
        scale.config(command=on_scale)

        tk.Label(win, text="Theme", font=("Segoe UI", 10, "bold"),
                 bg=self.theme["bg"], fg=self.theme["fg"]).pack(pady=(15, 2))
        theme_var = tk.StringVar(value=self.settings["theme"])
        theme_menu = ttk.Combobox(win, textvariable=theme_var, values=list(THEMES.keys()), state="readonly")
        theme_menu.pack(padx=20)

        wallpaper_var = tk.BooleanVar(value=self.settings["wallpaper_swap_enabled"])
        tk.Checkbutton(win, text="Enable wallpaper swap while running", variable=wallpaper_var,
                        bg=self.theme["bg"], fg=self.theme["fg"], selectcolor=self.theme["bg"]).pack(pady=(15, 5), padx=20)

        def save_and_close():
            self.settings["intensity"] = intensity_var.get()
            self.settings["theme"] = theme_var.get()
            self.settings["wallpaper_swap_enabled"] = wallpaper_var.get()
            save_json(SETTINGS_PATH, self.settings)
            self.apply_theme()
            win.destroy()

        tk.Button(win, text="Save", width=20, bg=self.theme["accent"], fg=self.theme["accent_fg"],
                  command=save_and_close).pack(pady=(10, 5), padx=20)

        tk.Button(win, text="Reset streak/history data", width=20,
                  command=lambda: (self.history.reset(), self.update_streak_label())).pack(pady=(0, 15), padx=20)

    # ------------- exit -------------

    def on_exit(self):
        try:
            self.wallpaper_mgr.revert()
        except Exception:
            pass
        save_json(SETTINGS_PATH, self.settings)
        try:
            self.root.destroy()
        except Exception:
            pass
        sys.exit(0)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = CompanionApp()
    app.run()
