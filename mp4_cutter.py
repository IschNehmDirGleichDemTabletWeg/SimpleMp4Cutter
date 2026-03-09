import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import os
import re
import json
import tempfile

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".mp4cutter_config.json")

def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_config():
    data = {
        "ffmpeg": var_ffmpeg.get().strip(),
        "src":    var_src.get().strip(),
        "dest":   var_dest.get().strip(),
        "start":  var_start.get().strip(),
        "end":    var_end.get().strip(),
        "join1":  var_join1.get().strip(),
        "join2":  var_join2.get().strip(),
    }
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

# ── Farben & Fonts ──────────────────────────────────────────────
BG       = "#1a1a2e"
PANEL    = "#16213e"
ACCENT   = "#e94560"
ACCENT2  = "#0f3460"
TEXT     = "#eaeaea"
MUTED    = "#7a7a9a"
ENTRY_BG = "#0d0d1f"
FONT_LBL = ("Courier New", 10)
FONT_BTN = ("Courier New", 10, "bold")
FONT_IN  = ("Courier New", 11)
FONT_RB  = ("Courier New", 11, "bold")

# ── ffmpeg Hilfsfunktionen ───────────────────────────────────────
def find_ffmpeg():
    import shutil
    manual = var_ffmpeg.get().strip()
    if manual and os.path.isfile(manual):
        return manual
    path = shutil.which("ffmpeg")
    if path:
        return path
    for c in [r"C:\ffmpeg\bin\ffmpeg.exe",
              r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
              r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe"]:
        if os.path.isfile(c):
            return c
    return None

def find_ffprobe():
    ffmpeg_path = find_ffmpeg()
    if ffmpeg_path:
        probe = os.path.join(os.path.dirname(ffmpeg_path), "ffprobe.exe")
        if os.path.isfile(probe):
            return probe
    import shutil
    return shutil.which("ffprobe") or "ffprobe"

def next_part_path(dest_folder, base_name):
    stem, ext = os.path.splitext(base_name)
    stem = re.sub(r"_part\d+$", "", stem)
    n = 1
    while True:
        candidate = os.path.join(dest_folder, f"{stem}_part{n:02d}{ext}")
        if not os.path.exists(candidate):
            return candidate
        n += 1

def parse_time(s: str) -> str:
    s = s.strip()
    if re.match(r"^\d{1,2}:\d{2}:\d{2}(\.\d+)?$", s):
        return s
    if re.match(r"^\d{1,2}:\d{2}(\.\d+)?$", s):
        return "00:" + s
    try:
        sec = float(s)
        h = int(sec // 3600); m = int((sec % 3600) // 60); ms = sec % 60
        return f"{h:02d}:{m:02d}:{ms:06.3f}"
    except ValueError:
        return s

# ── CUT Logik ───────────────────────────────────────────────────
def run_cut():
    src = var_src.get().strip(); dest = var_dest.get().strip()
    t_start = var_start.get().strip(); t_end = var_end.get().strip()
    if not src or not os.path.isfile(src):
        messagebox.showerror("Fehler", "Bitte eine gültige Quelldatei wählen."); return
    if not dest or not os.path.isdir(dest):
        messagebox.showerror("Fehler", "Bitte einen gültigen Zielordner wählen."); return
    if not t_start:
        messagebox.showerror("Fehler", "Startzeit fehlt."); return
    if not t_end:
        messagebox.showerror("Fehler", "Endzeit fehlt."); return
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        messagebox.showerror("ffmpeg nicht gefunden",
            "Bitte ffmpeg.exe manuell auswählen.\nDownload: https://ffmpeg.org/download.html"); return
    out_path = next_part_path(dest, os.path.basename(src))
    cmd = [ffmpeg, "-ss", parse_time(t_start), "-i", src,
           "-to", parse_time(t_end), "-c", "copy", out_path]
    status_var.set("⏳  Schnitt läuft …"); save_config(); root.update()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            status_var.set(f"✅  Gespeichert: {os.path.basename(out_path)}")
            messagebox.showinfo("Fertig!", f"Datei gespeichert als:\n{out_path}")
        else:
            status_var.set("❌  Fehler beim Schnitt")
            messagebox.showerror("ffmpeg Fehler", result.stderr[-800:] or "Unbekannter Fehler")
    except Exception as e:
        status_var.set("❌  Exception"); messagebox.showerror("Fehler", str(e))

# ── JOIN Logik ──────────────────────────────────────────────────
def run_join():
    f1 = var_join1.get().strip(); f2 = var_join2.get().strip()
    if not f1 or not os.path.isfile(f1):
        messagebox.showerror("Fehler", "Datei 1 ist ungültig."); return
    if not f2 or not os.path.isfile(f2):
        messagebox.showerror("Fehler", "Datei 2 ist ungültig."); return
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        messagebox.showerror("ffmpeg nicht gefunden",
            "Bitte ffmpeg.exe manuell auswählen.\nDownload: https://ffmpeg.org/download.html"); return

    # Ausgabedatei: gleicher Ordner wie Datei 1, _joined
    stem, ext = os.path.splitext(os.path.basename(f1))
    stem = re.sub(r"_part\d+$", "", stem)
    out_dir = os.path.dirname(f1)
    n = 1
    while True:
        out_path = os.path.join(out_dir, f"{stem}_joined{n:02d}{ext}")
        if not os.path.exists(out_path):
            break
        n += 1

    # Temporäre Liste
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt",
                                     delete=False, encoding="utf-8") as tf:
        tf.write(f"file '{f1}'\n")
        tf.write(f"file '{f2}'\n")
        list_file = tf.name

    if var_reencode.get():
        crf = int(var_crf.get())
        cmd = [ffmpeg, "-f", "concat", "-safe", "0", "-i", list_file,
               "-c:v", "libx264", "-crf", str(crf), "-preset", "slow",
               "-c:a", "aac", "-b:a", "192k", out_path]
        status_var.set(f"⏳  Join mit Re-Encoding (CRF {crf}) läuft … das dauert etwas")
    else:
        cmd = [ffmpeg, "-f", "concat", "-safe", "0",
               "-i", list_file, "-c", "copy", out_path]
        status_var.set("⏳  Join läuft …")
    save_config(); root.update()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        os.unlink(list_file)
        if result.returncode == 0:
            status_var.set(f"✅  Gespeichert: {os.path.basename(out_path)}")
            messagebox.showinfo("Fertig!", f"Datei gespeichert als:\n{out_path}")
        else:
            status_var.set("❌  Fehler beim Join")
            messagebox.showerror("ffmpeg Fehler", result.stderr[-800:] or "Unbekannter Fehler")
    except Exception as e:
        os.unlink(list_file)
        status_var.set("❌  Exception"); messagebox.showerror("Fehler", str(e))

# ── Browse Funktionen ───────────────────────────────────────────
def toggle_crf():
    if crf_slider is None:
        return
    state = "normal" if var_reencode.get() else "disabled"
    crf_slider.config(state=state)

crf_slider = None  # wird später gesetzt

def browse_src():
    path = filedialog.askopenfilename(title="Videodatei wählen",
        filetypes=[("Video", "*.mp4 *.mkv *.mov *.avi *.webm"), ("Alle", "*.*")])
    if path:
        var_src.set(path)
        if not var_dest.get():
            var_dest.set(os.path.dirname(path))
        save_config(); status_var.set("")

def browse_dest():
    path = filedialog.askdirectory(title="Zielordner wählen")
    if path:
        var_dest.set(path); save_config()

def browse_ffmpeg():
    path = filedialog.askopenfilename(title="ffmpeg.exe wählen",
        filetypes=[("ffmpeg", "ffmpeg.exe"), ("Ausführbar", "*.exe"), ("Alle", "*.*")])
    if path:
        var_ffmpeg.set(path); save_config()
        status_var.set(f"✅  ffmpeg gesetzt: {path}")

def browse_join(var):
    path = filedialog.askopenfilename(title="Videodatei wählen",
        filetypes=[("Video", "*.mp4 *.mkv *.mov *.avi *.webm"), ("Alle", "*.*")])
    if path:
        var.set(path); save_config(); status_var.set("")

def set_start_zero():
    var_start.set("00:00:00.000")

def set_end_duration():
    src = var_src.get().strip()
    if not src or not os.path.isfile(src):
        messagebox.showerror("Fehler", "Bitte zuerst eine Quelldatei wählen."); return
    try:
        result = subprocess.run(
            [find_ffprobe(), "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", src], capture_output=True, text=True)
        duration = float(result.stdout.strip())
        h = int(duration // 3600); m = int((duration % 3600) // 60); ms = duration % 60
        var_end.set(f"{h:02d}:{m:02d}:{ms:06.3f}")
        status_var.set(f"⏱  Videolänge: {h:02d}:{m:02d}:{ms:06.3f}")
    except Exception as e:
        messagebox.showerror("Fehler", f"Konnte Videolänge nicht auslesen:\n{e}")

# ── Widget Helfer ───────────────────────────────────────────────
def make_label(parent, text):
    return tk.Label(parent, text=text, bg=PANEL, fg=MUTED, font=FONT_LBL, anchor="w")

def make_entry(parent, textvariable, width=52):
    return tk.Entry(parent, textvariable=textvariable, width=width,
                    bg=ENTRY_BG, fg=TEXT, insertbackground=ACCENT, font=FONT_IN,
                    relief="flat", highlightthickness=1,
                    highlightcolor=ACCENT, highlightbackground=ACCENT2)

def make_btn(parent, text, cmd, color=ACCENT):
    return tk.Button(parent, text=text, command=cmd, bg=color, fg=TEXT,
                     font=FONT_BTN, relief="flat", cursor="hand2", padx=10, pady=4,
                     activebackground="#c73652", activeforeground=TEXT)

# ── Mode Switch ─────────────────────────────────────────────────
def switch_mode(*_):
    if var_mode.get() == "cut":
        frame_join.pack_forget()
        frame_cut.pack(fill="both", padx=16, pady=(0, 4))
        btn_action.config(text="  ✂  SCHNEIDEN & SPEICHERN  ", command=run_cut)
    else:
        frame_cut.pack_forget()
        frame_join.pack(fill="both", padx=16, pady=(0, 4))
        btn_action.config(text="  ⛓  ZUSAMMENFÜGEN  ", command=run_join)
    root.update_idletasks()

# ────────────────────────────────────────────────────────────────
# HAUPTFENSTER
# ────────────────────────────────────────────────────────────────
root = tk.Tk()
root.title("MP4 Cutter & Joiner")
root.configure(bg=BG)
root.resizable(False, False)

var_src    = tk.StringVar()
var_dest   = tk.StringVar()
var_start  = tk.StringVar()
var_end    = tk.StringVar()
var_ffmpeg = tk.StringVar()
var_join1  = tk.StringVar()
var_join2  = tk.StringVar()
var_mode   = tk.StringVar(value="cut")
var_reencode = tk.BooleanVar(value=False)
var_crf    = tk.IntVar(value=18)
status_var = tk.StringVar(value="")

# Config laden
cfg = load_config()
if cfg.get("ffmpeg") and os.path.isfile(cfg["ffmpeg"]):   var_ffmpeg.set(cfg["ffmpeg"])
if cfg.get("src")    and os.path.isfile(cfg["src"]):      var_src.set(cfg["src"])
if cfg.get("dest")   and os.path.isdir(cfg["dest"]):      var_dest.set(cfg["dest"])
if cfg.get("start"):  var_start.set(cfg["start"])
if cfg.get("end"):    var_end.set(cfg["end"])
if cfg.get("join1")  and os.path.isfile(cfg["join1"]):    var_join1.set(cfg["join1"])
if cfg.get("join2")  and os.path.isfile(cfg["join2"]):    var_join2.set(cfg["join2"])

var_start.trace_add("write", lambda *_: save_config())
var_end.trace_add("write",   lambda *_: save_config())

# ── Header ──────────────────────────────────────────────────────
tk.Frame(root, bg=ACCENT, height=4).pack(fill="x")

title_frame = tk.Frame(root, bg=BG)
title_frame.pack(fill="x", padx=20, pady=(12, 4))
tk.Label(title_frame, text="✂  MP4 CUTTER & JOINER", bg=BG, fg=ACCENT,
         font=("Courier New", 16, "bold")).pack(side="left")
tk.Label(title_frame, text="powered by ffmpeg", bg=BG, fg=MUTED,
         font=("Courier New", 9)).pack(side="left", padx=(10,0), pady=(4,0))

# ── Mode Radio Buttons ───────────────────────────────────────────
mode_frame = tk.Frame(root, bg=BG)
mode_frame.pack(fill="x", padx=20, pady=(0, 8))

for val, label in [("cut", "✂  Cut Movie"), ("join", "⛓  Join Movie")]:
    tk.Radiobutton(mode_frame, text=label, variable=var_mode, value=val,
                   command=switch_mode, bg=BG, fg=TEXT, selectcolor=ACCENT2,
                   activebackground=BG, activeforeground=ACCENT,
                   font=FONT_RB, relief="flat", cursor="hand2",
                   indicatoron=True).pack(side="left", padx=(0, 20))

# ── ffmpeg Panel (immer sichtbar) ────────────────────────────────
ffmpeg_panel = tk.Frame(root, bg=PANEL, padx=18, pady=10)
ffmpeg_panel.pack(fill="x", padx=16, pady=(0, 4))
make_label(ffmpeg_panel, "FFMPEG.EXE  (leer = auto-detect)").grid(
    row=0, column=0, columnspan=3, sticky="w", pady=(0,2))
make_entry(ffmpeg_panel, var_ffmpeg).grid(row=1, column=0, columnspan=2, sticky="ew")
make_btn(ffmpeg_panel, "⚙ Wählen", browse_ffmpeg, ACCENT2).grid(
    row=1, column=2, padx=(8,0))
ffmpeg_panel.columnconfigure(0, weight=1)

# ════════════════════════════════════════════════════════════════
# CUT PANEL
# ════════════════════════════════════════════════════════════════
frame_cut = tk.Frame(root, bg=PANEL, padx=18, pady=14)

# Quelldatei
make_label(frame_cut, "QUELLDATEI").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0,2))
make_entry(frame_cut, var_src).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0,8))
make_btn(frame_cut, "📂 Wählen", browse_src, ACCENT2).grid(row=1, column=2, padx=(8,0), pady=(0,8))

# Zielordner
make_label(frame_cut, "ZIELORDNER").grid(row=2, column=0, columnspan=3, sticky="w", pady=(0,2))
make_entry(frame_cut, var_dest).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0,8))
make_btn(frame_cut, "📁 Wählen", browse_dest, ACCENT2).grid(row=3, column=2, padx=(8,0), pady=(0,8))

# Separator
tk.Frame(frame_cut, bg=ACCENT2, height=1).grid(row=4, column=0, columnspan=3, sticky="ew", pady=8)

# Zeitfelder
time_frame = tk.Frame(frame_cut, bg=PANEL)
time_frame.grid(row=5, column=0, columnspan=3, sticky="ew")
tk.Frame(time_frame, bg=PANEL).pack(side="left", expand=True, fill="x")

left = tk.Frame(time_frame, bg=PANEL)
left.pack(side="left", padx=(0, 12))
make_label(left, "STARTZEIT").pack(anchor="w")
tk.Label(left, text="HH:MM:SS.mmm  oder  Sekunden", bg=PANEL, fg=MUTED,
         font=("Courier New", 7)).pack(anchor="w")
make_entry(left, var_start, width=22).pack(anchor="w", pady=(2,0))
make_btn(left, "◀ Start", set_start_zero, ACCENT2).pack(anchor="w", pady=(4,0))

tk.Label(time_frame, text="→", bg=PANEL, fg=ACCENT,
         font=("Courier New", 20, "bold")).pack(side="left", pady=(14,0))

right = tk.Frame(time_frame, bg=PANEL)
right.pack(side="left", padx=(12, 0))
make_label(right, "ENDZEIT").pack(anchor="w")
tk.Label(right, text="HH:MM:SS.mmm  oder  Sekunden", bg=PANEL, fg=MUTED,
         font=("Courier New", 7)).pack(anchor="w")
make_entry(right, var_end, width=22).pack(anchor="w", pady=(2,0))
make_btn(right, "⏱ Ende", set_end_duration, ACCENT2).pack(anchor="w", pady=(4,0))
tk.Frame(time_frame, bg=PANEL).pack(side="left", expand=True, fill="x")

tk.Label(frame_cut, text='Beispiele:  "00:01:23.500"  |  "83.5"  |  "1:23.5"',
         bg=PANEL, fg=MUTED, font=("Courier New", 8)).grid(
    row=6, column=0, columnspan=3, pady=(6,0))

frame_cut.columnconfigure(0, weight=1)

# ════════════════════════════════════════════════════════════════
# JOIN PANEL
# ════════════════════════════════════════════════════════════════
frame_join = tk.Frame(root, bg=PANEL, padx=18, pady=14)

make_label(frame_join, "DATEI 1").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0,2))
make_entry(frame_join, var_join1).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0,8))
make_btn(frame_join, "📂 Wählen", lambda: browse_join(var_join1), ACCENT2).grid(
    row=1, column=2, padx=(8,0), pady=(0,8))

make_label(frame_join, "DATEI 2").grid(row=2, column=0, columnspan=3, sticky="w", pady=(0,2))
make_entry(frame_join, var_join2).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0,8))
make_btn(frame_join, "📂 Wählen", lambda: browse_join(var_join2), ACCENT2).grid(
    row=3, column=2, padx=(8,0), pady=(0,8))

tk.Label(frame_join, text="Ausgabe wird automatisch als  _joined01.mp4  neben Datei 1 gespeichert.",
         bg=PANEL, fg=MUTED, font=("Courier New", 8)).grid(
    row=4, column=0, columnspan=3, pady=(8,0))

# Separator
tk.Frame(frame_join, bg=ACCENT2, height=1).grid(row=5, column=0, columnspan=3, sticky="ew", pady=10)

# Re-Encode Checkbox
cb_frame = tk.Frame(frame_join, bg=PANEL)
cb_frame.grid(row=6, column=0, columnspan=3, sticky="w")
tk.Checkbutton(cb_frame, text="Re-Encoding  (saubere Naht, aber langsamer)",
               variable=var_reencode, bg=PANEL, fg=TEXT, selectcolor=ACCENT2,
               activebackground=PANEL, activeforeground=ACCENT,
               font=("Courier New", 9, "bold"), cursor="hand2",
               command=toggle_crf).pack(side="left")

# CRF Slider Frame
crf_frame = tk.Frame(frame_join, bg=PANEL)
crf_frame.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(6,4))

tk.Label(crf_frame, text="QUALITÄT  CRF:", bg=PANEL, fg=MUTED,
         font=("Courier New", 9)).pack(side="left")
crf_slider = tk.Scale(crf_frame, from_=0, to=51, orient="horizontal",
                      variable=var_crf, length=200,
                      bg=PANEL, fg=TEXT, highlightthickness=0,
                      troughcolor=ACCENT2, activebackground=ACCENT,
                      font=("Courier New", 8), showvalue=True)
crf_slider.pack(side="left", padx=(8,8))
crf_slider.config(state="disabled")  # erstmal deaktiviert
tk.Label(crf_frame, text="0=perfekt  18=sehr gut  23=gut  51=schlecht",
         bg=PANEL, fg=MUTED, font=("Courier New", 7)).pack(side="left")

frame_join.columnconfigure(0, weight=1)

# ── Standardmäßig CUT anzeigen ───────────────────────────────────
frame_cut.pack(fill="both", padx=16, pady=(0, 4))

# ── Action Button ────────────────────────────────────────────────
btn_frame = tk.Frame(root, bg=BG)
btn_frame.pack(pady=(4, 6))
btn_action = make_btn(btn_frame, "  ✂  SCHNEIDEN & SPEICHERN  ", run_cut)
btn_action.pack(ipadx=20, ipady=6)

# ── Statuszeile ──────────────────────────────────────────────────
status_bar = tk.Frame(root, bg=ACCENT2, height=28)
status_bar.pack(fill="x", side="bottom")
tk.Label(status_bar, textvariable=status_var, bg=ACCENT2, fg=TEXT,
         font=("Courier New", 9), anchor="w").pack(side="left", padx=12, pady=4)

root.mainloop()