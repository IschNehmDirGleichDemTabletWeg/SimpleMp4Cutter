import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import os
import re
import json

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".mp4cutter_config.json")

def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_config(data: dict):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass

# ── Farben & Fonts ──────────────────────────────────────────────
BG        = "#1a1a2e"
PANEL     = "#16213e"
ACCENT    = "#e94560"
ACCENT2   = "#0f3460"
TEXT      = "#eaeaea"
MUTED     = "#7a7a9a"
ENTRY_BG  = "#0d0d1f"
FONT_HEAD = ("Courier New", 15, "bold")
FONT_LBL  = ("Courier New", 10)
FONT_BTN  = ("Courier New", 10, "bold")
FONT_IN   = ("Courier New", 11)

def find_ffmpeg():
    """Prüfe erst manuellen Pfad, dann PATH, dann übliche Windows-Orte."""
    import shutil
    # 1. Manuell gesetzt?
    manual = var_ffmpeg.get().strip() if 'var_ffmpeg' in globals() else ""
    if manual and os.path.isfile(manual):
        return manual
    # 2. Im PATH?
    path = shutil.which("ffmpeg")
    if path:
        return path
    # 3. Übliche Windows-Pfade
    candidates = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None

def next_part_path(dest_folder, base_name):
    """Ermittle den nächsten freien _partXX Dateinamen."""
    stem, ext = os.path.splitext(base_name)
    # Entferne schon vorhandenes _partXX am Ende
    stem = re.sub(r"_part\d+$", "", stem)
    n = 1
    while True:
        candidate = os.path.join(dest_folder, f"{stem}_part{n:02d}{ext}")
        if not os.path.exists(candidate):
            return candidate
        n += 1

def parse_time(s: str) -> str:
    """
    Akzeptiert:
      HH:MM:SS.mmm  →  unverändert
      MM:SS.mmm     →  00:MM:SS.mmm
      SS.mmm        →  00:00:SS.mmm
      reine Sekunden (float)  →  00:00:SS.mmm
    """
    s = s.strip()
    if re.match(r"^\d{1,2}:\d{2}:\d{2}(\.\d+)?$", s):
        return s
    if re.match(r"^\d{1,2}:\d{2}(\.\d+)?$", s):
        return "00:" + s
    try:
        sec = float(s)
        h   = int(sec // 3600)
        m   = int((sec % 3600) // 60)
        ms  = sec % 60
        return f"{h:02d}:{m:02d}:{ms:06.3f}"
    except ValueError:
        return s

def run_cut():
    src    = var_src.get().strip()
    dest   = var_dest.get().strip()
    t_start = var_start.get().strip()
    t_end   = var_end.get().strip()

    # ── Validierung ──────────────────────────────────────────────
    if not src or not os.path.isfile(src):
        messagebox.showerror("Fehler", "Bitte eine gültige Quelldatei wählen.")
        return
    if not dest or not os.path.isdir(dest):
        messagebox.showerror("Fehler", "Bitte einen gültigen Zielordner wählen.")
        return
    if not t_start:
        messagebox.showerror("Fehler", "Startzeit fehlt.")
        return
    if not t_end:
        messagebox.showerror("Fehler", "Endzeit fehlt.")
        return

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        messagebox.showerror(
            "ffmpeg nicht gefunden",
            "ffmpeg wurde nicht gefunden.\n"
            "Bitte ffmpeg installieren und zum PATH hinzufügen.\n"
            "Download: https://ffmpeg.org/download.html"
        )
        return

    t_start_fmt = parse_time(t_start)
    t_end_fmt   = parse_time(t_end)

    out_path = next_part_path(dest, os.path.basename(src))

    cmd = [
        ffmpeg,
        "-i",  src,
        "-ss", t_start_fmt,
        "-to", t_end_fmt,
        "-c",  "copy",
        out_path
    ]

    status_var.set("⏳  Schnitt läuft …")
    root.update()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            status_var.set(f"✅  Gespeichert: {os.path.basename(out_path)}")
            messagebox.showinfo(
                "Fertig!",
                f"Datei gespeichert als:\n{out_path}"
            )
        else:
            status_var.set("❌  Fehler beim Schnitt")
            messagebox.showerror(
                "ffmpeg Fehler",
                result.stderr[-800:] if result.stderr else "Unbekannter Fehler"
            )
    except Exception as e:
        status_var.set("❌  Exception")
        messagebox.showerror("Fehler", str(e))

def browse_src():
    path = filedialog.askopenfilename(
        title="Videodatei wählen",
        filetypes=[("Video", "*.mp4 *.mkv *.mov *.avi *.webm"), ("Alle", "*.*")]
    )
    if path:
        var_src.set(path)
        if not var_dest.get():
            var_dest.set(os.path.dirname(path))
        status_var.set("")

def browse_dest():
    path = filedialog.askdirectory(title="Zielordner wählen")
    if path:
        var_dest.set(path)

    path = filedialog.askopenfilename(
        title="ffmpeg.exe wählen",
        filetypes=[("ffmpeg", "ffmpeg.exe"), ("Ausführbar", "*.exe"), ("Alle", "*.*")]
    )
    if path:
        var_ffmpeg.set(path)
        save_config({"ffmpeg": path})
        status_var.set(f"✅  ffmpeg gesetzt: {path}")

# ── Hilfsfunktionen für schöne Widgets ─────────────────────────
def make_label(parent, text):
    return tk.Label(parent, text=text, bg=PANEL, fg=MUTED,
                    font=FONT_LBL, anchor="w")

def make_entry(parent, textvariable, width=52):
    return tk.Entry(parent, textvariable=textvariable, width=width,
                    bg=ENTRY_BG, fg=TEXT, insertbackground=ACCENT,
                    font=FONT_IN, relief="flat",
                    highlightthickness=1, highlightcolor=ACCENT,
                    highlightbackground=ACCENT2)

def make_btn(parent, text, cmd, color=ACCENT):
    return tk.Button(parent, text=text, command=cmd,
                     bg=color, fg=TEXT, font=FONT_BTN,
                     relief="flat", cursor="hand2",
                     padx=10, pady=4,
                     activebackground="#c73652", activeforeground=TEXT)

# ── Hauptfenster ────────────────────────────────────────────────
root = tk.Tk()
root.title("MP4 Cutter")
root.configure(bg=BG)
root.resizable(False, False)

var_src   = tk.StringVar()
var_dest  = tk.StringVar()
var_start = tk.StringVar()
var_end   = tk.StringVar()
var_ffmpeg = tk.StringVar()
status_var = tk.StringVar(value="")

# Gespeicherten ffmpeg-Pfad laden
cfg = load_config()
if cfg.get("ffmpeg") and os.path.isfile(cfg["ffmpeg"]):
    var_ffmpeg.set(cfg["ffmpeg"])


pad = dict(padx=18, pady=6)

# ── Header ──────────────────────────────────────────────────────
header = tk.Frame(root, bg=ACCENT, height=4)
header.pack(fill="x")

title_frame = tk.Frame(root, bg=BG)
title_frame.pack(fill="x", padx=20, pady=(14, 4))
tk.Label(title_frame, text="✂  MP4 CUTTER", bg=BG, fg=ACCENT,
         font=("Courier New", 18, "bold")).pack(side="left")
tk.Label(title_frame, text="powered by ffmpeg", bg=BG, fg=MUTED,
         font=("Courier New", 9)).pack(side="left", padx=(10, 0), pady=(6, 0))

# ── Panel ────────────────────────────────────────────────────────
panel = tk.Frame(root, bg=PANEL, padx=18, pady=14)
panel.pack(fill="both", padx=16, pady=(4, 8))

# Quelldatei
make_label(panel, "QUELLDATEI").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0,2))
make_entry(panel, var_src).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0,8))
make_btn(panel, "📂 Wählen", browse_src, ACCENT2).grid(row=1, column=2, padx=(8,0), pady=(0,8))

# Zielordner
make_label(panel, "ZIELORDNER").grid(row=2, column=0, columnspan=3, sticky="w", pady=(0,2))
make_entry(panel, var_dest).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0,8))
make_btn(panel, "📁 Wählen", browse_dest, ACCENT2).grid(row=3, column=2, padx=(8,0), pady=(0,8))

# ffmpeg Pfad
make_label(panel, "FFMPEG.EXE  (leer = auto-detect)").grid(row=4, column=0, columnspan=3, sticky="w", pady=(0,2))
make_entry(panel, var_ffmpeg).grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0,8))
make_btn(panel, "⚙ Wählen", browse_ffmpeg, ACCENT2).grid(row=5, column=2, padx=(8,0), pady=(0,8))

# Separator
sep = tk.Frame(panel, bg=ACCENT2, height=1)
sep.grid(row=6, column=0, columnspan=3, sticky="ew", pady=8)

# Zeitfelder
time_frame = tk.Frame(panel, bg=PANEL)
time_frame.grid(row=7, column=0, columnspan=3, sticky="ew")

# Start
tk.Frame(time_frame, bg=PANEL).pack(side="left", expand=True, fill="x")
left = tk.Frame(time_frame, bg=PANEL)
left.pack(side="left", padx=(0, 12))
make_label(left, "STARTZEIT").pack(anchor="w")
tk.Label(left, text="HH:MM:SS.mmm  oder  Sekunden", bg=PANEL, fg=MUTED,
         font=("Courier New", 7)).pack(anchor="w")
make_entry(left, var_start, width=22).pack(anchor="w", pady=(2,0))

# Pfeil
tk.Label(time_frame, text="→", bg=PANEL, fg=ACCENT,
         font=("Courier New", 20, "bold")).pack(side="left", pady=(14,0))

# Ende
right = tk.Frame(time_frame, bg=PANEL)
right.pack(side="left", padx=(12, 0))
make_label(right, "ENDZEIT").pack(anchor="w")
tk.Label(right, text="HH:MM:SS.mmm  oder  Sekunden", bg=PANEL, fg=MUTED,
         font=("Courier New", 7)).pack(anchor="w")
make_entry(right, var_end, width=22).pack(anchor="w", pady=(2,0))
tk.Frame(time_frame, bg=PANEL).pack(side="left", expand=True, fill="x")

# Beispiel-Hinweis
tk.Label(panel, text='Beispiele:  "00:01:23.500"  |  "83.5"  |  "1:23.5"',
         bg=PANEL, fg=MUTED, font=("Courier New", 8)).grid(
    row=8, column=0, columnspan=3, pady=(6,0))

# ── Cut Button ──────────────────────────────────────────────────
btn_frame = tk.Frame(root, bg=BG)
btn_frame.pack(pady=(0, 6))
make_btn(btn_frame, "  ✂  SCHNEIDEN & SPEICHERN  ", run_cut).pack(ipadx=20, ipady=6)

# ── Statuszeile ─────────────────────────────────────────────────
status_bar = tk.Frame(root, bg=ACCENT2, height=28)
status_bar.pack(fill="x", side="bottom")
tk.Label(status_bar, textvariable=status_var, bg=ACCENT2, fg=TEXT,
         font=("Courier New", 9), anchor="w").pack(side="left", padx=12, pady=4)

root.mainloop()
