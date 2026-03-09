APP_VERSION = "1.1"

import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import threading
import os
import re
import json
import tempfile
import time

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".mp4cutter_config.json")

# ── Config ──────────────────────────────────────────────────────
def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_config():
    data = {
        "ffmpeg":   var_ffmpeg.get().strip(),
        "src":      var_src.get().strip(),
        "dest":     var_dest.get().strip(),
        "start":    var_start.get().strip(),
        "end":      var_end.get().strip(),
        "join1":    var_join1.get().strip(),
        "join2":    var_join2.get().strip(),
        "encoder":  var_encoder.get().strip(),
        "reencode": var_reencode.get(),
        "crf":      var_crf.get(),
    }
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

# ── Colors & Fonts ──────────────────────────────────────────────
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
FONT_LOG = ("Courier New", 9)

# Encoder options: label → (video_codec, extra_args)
# libx264 : CRF = quality-based, file size follows quality
# h264_nvenc: -rc vbr + -cq {crf} + -b:v 0 = true VBR quality mode (no size bloat)
# h264_amf  : -rc cqp + -qp_i/p/b = constant QP, closest to CRF on AMD
# h264_qsv  : -global_quality + -look_ahead = ICQ mode, quality-based
ENCODERS = {
    "CPU — libx264  (compatible, slower)":    ("libx264",    ["-preset", "slow"]),
    "GPU — h264_nvenc  (NVIDIA, fast)":        ("h264_nvenc", ["-rc", "vbr", "-cq", "{crf}",
                                                               "-b:v", "0", "-maxrate",
                                                               "50M", "-bufsize", "100M",
                                                               "-preset", "p4"]),
    "GPU — h264_amf  (AMD, fast)":             ("h264_amf",   ["-rc", "cqp",
                                                               "-qp_i", "{crf}",
                                                               "-qp_p", "{crf}",
                                                               "-qp_b", "{crf}",
                                                               "-quality", "balanced"]),
    "GPU — h264_qsv  (Intel QuickSync, fast)": ("h264_qsv",   ["-global_quality", "{crf}",
                                                               "-look_ahead", "1"]),
}

# ── ffmpeg helpers ───────────────────────────────────────────────
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

def get_encoder_args(crf: int):
    """Return [video_codec_name, extra_args_list] for selected encoder."""
    label = var_encoder.get()
    codec, extra = ENCODERS.get(label, ("libx264", ["-preset", "slow"]))
    resolved = [a.replace("{crf}", str(crf)) for a in extra]
    return codec, resolved

# ── Progress Window ──────────────────────────────────────────────
def open_progress_window(title="Processing…"):
    """Opens a dark progress/log window. Returns (window, log_text_widget, time_label)."""
    win = tk.Toplevel(root)
    win.title(title)
    win.configure(bg=BG)
    win.resizable(True, False)
    win.geometry("620x280")
    try:
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if os.path.isfile(icon_path):
            win.iconbitmap(icon_path)
    except Exception:
        pass

    tk.Frame(win, bg=ACCENT, height=3).pack(fill="x")

    top = tk.Frame(win, bg=BG)
    top.pack(fill="x", padx=12, pady=(8,4))
    tk.Label(top, text=title, bg=BG, fg=ACCENT, font=FONT_BTN).pack(side="left")
    time_lbl = tk.Label(top, text="Elapsed: 0s", bg=BG, fg=MUTED, font=FONT_LOG)
    time_lbl.pack(side="right")

    log_frame = tk.Frame(win, bg=ENTRY_BG)
    log_frame.pack(fill="both", expand=True, padx=12, pady=(0,8))

    scrollbar = tk.Scrollbar(log_frame)
    scrollbar.pack(side="right", fill="y")

    log = tk.Text(log_frame, bg=ENTRY_BG, fg=TEXT, font=FONT_LOG,
                  relief="flat", wrap="word", state="disabled",
                  yscrollcommand=scrollbar.set, height=10)
    log.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=log.yview)

    return win, log, time_lbl

def log_append(log_widget, text):
    log_widget.config(state="normal")
    log_widget.insert("end", text)
    log_widget.see("end")
    log_widget.config(state="disabled")

def run_ffmpeg_with_progress(cmd, win, log_widget, time_lbl, on_done):
    """Run ffmpeg in a thread, stream stderr to log_widget, call on_done(success, msg)."""
    start = time.time()

    def tick():
        if win.winfo_exists():
            elapsed = int(time.time() - start)
            time_lbl.config(text=f"Elapsed: {elapsed}s")
            win.after(1000, tick)
    win.after(1000, tick)

    def worker():
        try:
            proc = subprocess.Popen(
                cmd,
                stderr=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            last_line = ""
            for line in proc.stderr:
                line = line.strip()
                if line:
                    last_line = line
                    # Show progress lines (frame=, time=, speed=) in place
                    if line.startswith("frame=") or "time=" in line:
                        root.after(0, lambda l=line: update_progress_line(log_widget, l))
                    else:
                        root.after(0, lambda l=line + "\n": log_append(log_widget, l))
            proc.wait()
            elapsed = int(time.time() - start)
            if proc.returncode == 0:
                root.after(0, lambda: on_done(True, elapsed))
            else:
                root.after(0, lambda: on_done(False, last_line))
        except Exception as e:
            root.after(0, lambda: on_done(False, str(e)))

    threading.Thread(target=worker, daemon=True).start()

def update_progress_line(log_widget, text):
    """Replace the last line if it's a progress line, otherwise append."""
    log_widget.config(state="normal")
    content = log_widget.get("1.0", "end-1c")
    lines = content.split("\n")
    if lines and (lines[-1].startswith("frame=") or "time=" in lines[-1]):
        log_widget.delete(f"{float(log_widget.index('end-1c').split('.')[0])-0:.1f}", "end-1c")
        log_widget.insert("end-1c", "\n" + text)
    else:
        log_widget.insert("end", "\n" + text)
    log_widget.see("end")
    log_widget.config(state="disabled")

# ── CUT ─────────────────────────────────────────────────────────
def run_cut():
    src = var_src.get().strip(); dest = var_dest.get().strip()
    t_start = var_start.get().strip(); t_end = var_end.get().strip()
    if not src or not os.path.isfile(src):
        messagebox.showerror("Error", "Please select a valid source file."); return
    if not dest or not os.path.isdir(dest):
        messagebox.showerror("Error", "Please select a valid output folder."); return
    if not t_start:
        messagebox.showerror("Error", "Start time is missing."); return
    if not t_end:
        messagebox.showerror("Error", "End time is missing."); return
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        messagebox.showerror("ffmpeg not found",
            "Please select ffmpeg.exe manually.\nDownload: https://ffmpeg.org/download.html"); return

    out_path = next_part_path(dest, os.path.basename(src))
    cmd = [ffmpeg, "-y", "-ss", parse_time(t_start), "-i", src,
           "-to", parse_time(t_end), "-c", "copy", "-progress", "pipe:2", out_path]

    save_config()
    win, log, time_lbl = open_progress_window("✂  Cutting…")
    log_append(log, f"Output: {out_path}\n\n")
    status_var.set("⏳  Cutting…")

    def on_done(success, info):
        if success:
            status_var.set(f"✅  Saved: {os.path.basename(out_path)}")
            log_append(log, f"\n✅  Done in {info}s  →  {os.path.basename(out_path)}\n")
        else:
            status_var.set("❌  Error during cut")
            log_append(log, f"\n❌  Error: {info}\n")

    run_ffmpeg_with_progress(cmd, win, log, time_lbl, on_done)

# ── JOIN ─────────────────────────────────────────────────────────
def run_join():
    f1 = var_join1.get().strip(); f2 = var_join2.get().strip()
    if not f1 or not os.path.isfile(f1):
        messagebox.showerror("Error", "File 1 is invalid."); return
    if not f2 or not os.path.isfile(f2):
        messagebox.showerror("Error", "File 2 is invalid."); return
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        messagebox.showerror("ffmpeg not found",
            "Please select ffmpeg.exe manually.\nDownload: https://ffmpeg.org/download.html"); return

    stem, ext = os.path.splitext(os.path.basename(f1))
    stem = re.sub(r"_part\d+$", "", stem)
    out_dir = os.path.dirname(f1)
    n = 1
    while True:
        out_path = os.path.join(out_dir, f"{stem}_joined{n:02d}{ext}")
        if not os.path.exists(out_path):
            break
        n += 1

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt",
                                     delete=False, encoding="utf-8") as tf:
        tf.write(f"file '{f1}'\n")
        tf.write(f"file '{f2}'\n")
        list_file = tf.name

    if var_reencode.get():
        crf = int(var_crf.get())
        codec, extra = get_encoder_args(crf)
        cmd = ([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", list_file,
                "-c:v", codec] + extra +
               ["-c:a", "aac", "-b:a", "192k", "-progress", "pipe:2", out_path])
        title = f"⛓  Joining with Re-Encode ({codec}, CRF {crf})…"
    else:
        cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0",
               "-i", list_file, "-c", "copy", "-progress", "pipe:2", out_path]
        title = "⛓  Joining (lossless copy)…"

    save_config()
    win, log, time_lbl = open_progress_window(title)
    log_append(log, f"Output: {out_path}\n\n")
    status_var.set("⏳  Joining…")

    def on_done(success, info):
        os.unlink(list_file)
        if success:
            status_var.set(f"✅  Saved: {os.path.basename(out_path)}")
            log_append(log, f"\n✅  Done in {info}s  →  {os.path.basename(out_path)}\n")
        else:
            status_var.set("❌  Error during join")
            log_append(log, f"\n❌  Error: {info}\n")

    run_ffmpeg_with_progress(cmd, win, log, time_lbl, on_done)

# ── Browse functions ─────────────────────────────────────────────
def toggle_crf(*_):
    if crf_slider is None:
        return
    state = "normal" if var_reencode.get() else "disabled"
    crf_slider.config(state=state)
    encoder_menu.config(state="normal" if var_reencode.get() else "disabled")

crf_slider   = None
encoder_menu = None

def browse_src():
    path = filedialog.askopenfilename(title="Select video file",
        filetypes=[("Video", "*.mp4 *.mkv *.mov *.avi *.webm"), ("All files", "*.*")])
    if path:
        var_src.set(path)
        if not var_dest.get():
            var_dest.set(os.path.dirname(path))
        save_config(); status_var.set("")

def browse_dest():
    path = filedialog.askdirectory(title="Select output folder")
    if path:
        var_dest.set(path); save_config()

def browse_ffmpeg():
    path = filedialog.askopenfilename(title="Select ffmpeg.exe",
        filetypes=[("ffmpeg", "ffmpeg.exe"), ("Executable", "*.exe"), ("All files", "*.*")])
    if path:
        var_ffmpeg.set(path); save_config()
        status_var.set(f"✅  ffmpeg set: {path}")

def browse_join(var):
    path = filedialog.askopenfilename(title="Select video file",
        filetypes=[("Video", "*.mp4 *.mkv *.mov *.avi *.webm"), ("All files", "*.*")])
    if path:
        var.set(path); save_config(); status_var.set("")

def set_start_zero():
    var_start.set("00:00:00.000")

def set_end_duration():
    src = var_src.get().strip()
    if not src or not os.path.isfile(src):
        messagebox.showerror("Error", "Please select a source file first."); return
    try:
        result = subprocess.run(
            [find_ffprobe(), "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", src], capture_output=True, text=True)
        duration = float(result.stdout.strip())
        h = int(duration // 3600); m = int((duration % 3600) // 60); ms = duration % 60
        var_end.set(f"{h:02d}:{m:02d}:{ms:06.3f}")
        status_var.set(f"⏱  Video duration: {h:02d}:{m:02d}:{ms:06.3f}")
    except Exception as e:
        messagebox.showerror("Error", f"Could not read video duration:\n{e}")

# ── Widget helpers ───────────────────────────────────────────────
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

# ── Mode switch ──────────────────────────────────────────────────
def switch_mode(*_):
    if var_mode.get() == "cut":
        frame_join.pack_forget()
        frame_cut.pack(fill="both", padx=16, pady=(0, 4))
        btn_action.config(text="  ✂  CUT & SAVE  ", command=run_cut)
    else:
        frame_cut.pack_forget()
        frame_join.pack(fill="both", padx=16, pady=(0, 4))
        btn_action.config(text="  ⛓  JOIN FILES  ", command=run_join)
    root.update_idletasks()

# ════════════════════════════════════════════════════════════════
# MAIN WINDOW
# ════════════════════════════════════════════════════════════════
root = tk.Tk()
root.title(f"MP4 Cutter & Joiner  v{APP_VERSION}")
root.configure(bg=BG)
root.resizable(False, False)

try:
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
    if os.path.isfile(icon_path):
        root.iconbitmap(icon_path)
except Exception:
    pass

var_src      = tk.StringVar()
var_dest     = tk.StringVar()
var_start    = tk.StringVar()
var_end      = tk.StringVar()
var_ffmpeg   = tk.StringVar()
var_join1    = tk.StringVar()
var_join2    = tk.StringVar()
var_mode     = tk.StringVar(value="cut")
var_reencode = tk.BooleanVar(value=False)
var_crf      = tk.IntVar(value=23)
var_encoder  = tk.StringVar(value=list(ENCODERS.keys())[0])
status_var   = tk.StringVar(value="")

# Load config
cfg = load_config()
if cfg.get("ffmpeg")  and os.path.isfile(cfg["ffmpeg"]):  var_ffmpeg.set(cfg["ffmpeg"])
if cfg.get("src")     and os.path.isfile(cfg["src"]):     var_src.set(cfg["src"])
if cfg.get("dest")    and os.path.isdir(cfg["dest"]):     var_dest.set(cfg["dest"])
if cfg.get("start"):   var_start.set(cfg["start"])
if cfg.get("end"):     var_end.set(cfg["end"])
if cfg.get("join1")   and os.path.isfile(cfg["join1"]):   var_join1.set(cfg["join1"])
if cfg.get("join2")   and os.path.isfile(cfg["join2"]):   var_join2.set(cfg["join2"])
if cfg.get("encoder") and cfg["encoder"] in ENCODERS:     var_encoder.set(cfg["encoder"])
if "reencode" in cfg:  var_reencode.set(cfg["reencode"])
if "crf"      in cfg:  var_crf.set(cfg["crf"])

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

# ── Mode selector ────────────────────────────────────────────────
mode_frame = tk.Frame(root, bg=BG)
mode_frame.pack(fill="x", padx=20, pady=(0, 8))
for val, label in [("cut", "✂  Cut Movie"), ("join", "⛓  Join Movie")]:
    tk.Radiobutton(mode_frame, text=label, variable=var_mode, value=val,
                   command=switch_mode, bg=BG, fg=TEXT, selectcolor=ACCENT2,
                   activebackground=BG, activeforeground=ACCENT,
                   font=FONT_RB, relief="flat", cursor="hand2").pack(side="left", padx=(0,20))

# ── ffmpeg panel (always visible) ───────────────────────────────
ffmpeg_panel = tk.Frame(root, bg=PANEL, padx=18, pady=10)
ffmpeg_panel.pack(fill="x", padx=16, pady=(0, 4))
make_label(ffmpeg_panel, "FFMPEG.EXE  (leave empty for auto-detect)").grid(
    row=0, column=0, columnspan=3, sticky="w", pady=(0,2))
make_entry(ffmpeg_panel, var_ffmpeg).grid(row=1, column=0, columnspan=2, sticky="ew")
make_btn(ffmpeg_panel, "⚙ Browse", browse_ffmpeg, ACCENT2).grid(row=1, column=2, padx=(8,0))
ffmpeg_panel.columnconfigure(0, weight=1)

# ════════════════════════════════════════════════════════════════
# CUT PANEL
# ════════════════════════════════════════════════════════════════
frame_cut = tk.Frame(root, bg=PANEL, padx=18, pady=14)

make_label(frame_cut, "SOURCE FILE").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0,2))
make_entry(frame_cut, var_src).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0,8))
make_btn(frame_cut, "📂 Browse", browse_src, ACCENT2).grid(row=1, column=2, padx=(8,0), pady=(0,8))

make_label(frame_cut, "OUTPUT FOLDER").grid(row=2, column=0, columnspan=3, sticky="w", pady=(0,2))
make_entry(frame_cut, var_dest).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0,8))
make_btn(frame_cut, "📁 Browse", browse_dest, ACCENT2).grid(row=3, column=2, padx=(8,0), pady=(0,8))

tk.Frame(frame_cut, bg=ACCENT2, height=1).grid(row=4, column=0, columnspan=3, sticky="ew", pady=8)

time_frame = tk.Frame(frame_cut, bg=PANEL)
time_frame.grid(row=5, column=0, columnspan=3, sticky="ew")
tk.Frame(time_frame, bg=PANEL).pack(side="left", expand=True, fill="x")

left = tk.Frame(time_frame, bg=PANEL)
left.pack(side="left", padx=(0,12))
make_label(left, "START TIME").pack(anchor="w")
tk.Label(left, text="HH:MM:SS.mmm  or  seconds", bg=PANEL, fg=MUTED,
         font=("Courier New", 7)).pack(anchor="w")
make_entry(left, var_start, width=22).pack(anchor="w", pady=(2,0))
make_btn(left, "◀ Set Start", set_start_zero, ACCENT2).pack(anchor="w", pady=(4,0))

tk.Label(time_frame, text="→", bg=PANEL, fg=ACCENT,
         font=("Courier New", 20, "bold")).pack(side="left", pady=(14,0))

right = tk.Frame(time_frame, bg=PANEL)
right.pack(side="left", padx=(12,0))
make_label(right, "END TIME").pack(anchor="w")
tk.Label(right, text="HH:MM:SS.mmm  or  seconds", bg=PANEL, fg=MUTED,
         font=("Courier New", 7)).pack(anchor="w")
make_entry(right, var_end, width=22).pack(anchor="w", pady=(2,0))
make_btn(right, "⏱ Set End", set_end_duration, ACCENT2).pack(anchor="w", pady=(4,0))
tk.Frame(time_frame, bg=PANEL).pack(side="left", expand=True, fill="x")

tk.Label(frame_cut, text='Examples:  "00:01:23.500"  |  "83.5"  |  "1:23.5"',
         bg=PANEL, fg=MUTED, font=("Courier New", 8)).grid(
    row=6, column=0, columnspan=3, pady=(6,0))
frame_cut.columnconfigure(0, weight=1)

# ════════════════════════════════════════════════════════════════
# JOIN PANEL
# ════════════════════════════════════════════════════════════════
frame_join = tk.Frame(root, bg=PANEL, padx=18, pady=14)

make_label(frame_join, "FILE 1").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0,2))
make_entry(frame_join, var_join1).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0,8))
make_btn(frame_join, "📂 Browse", lambda: browse_join(var_join1), ACCENT2).grid(
    row=1, column=2, padx=(8,0), pady=(0,8))

make_label(frame_join, "FILE 2").grid(row=2, column=0, columnspan=3, sticky="w", pady=(0,2))
make_entry(frame_join, var_join2).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0,8))
make_btn(frame_join, "📂 Browse", lambda: browse_join(var_join2), ACCENT2).grid(
    row=3, column=2, padx=(8,0), pady=(0,8))

tk.Label(frame_join, text="Output is saved as  _joined01.mp4  next to File 1.",
         bg=PANEL, fg=MUTED, font=("Courier New", 8)).grid(
    row=4, column=0, columnspan=3, pady=(8,0))

tk.Frame(frame_join, bg=ACCENT2, height=1).grid(row=5, column=0, columnspan=3, sticky="ew", pady=10)

# Re-encode checkbox
cb_frame = tk.Frame(frame_join, bg=PANEL)
cb_frame.grid(row=6, column=0, columnspan=3, sticky="w")
tk.Checkbutton(cb_frame, text="Re-Encode  (seamless join, slower — enables options below)",
               variable=var_reencode, bg=PANEL, fg=TEXT, selectcolor=ACCENT2,
               activebackground=PANEL, activeforeground=ACCENT,
               font=("Courier New", 9, "bold"), cursor="hand2",
               command=toggle_crf).pack(side="left")

# Encoder dropdown
enc_frame = tk.Frame(frame_join, bg=PANEL)
enc_frame.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(8,2))
tk.Label(enc_frame, text="ENCODER:", bg=PANEL, fg=MUTED, font=FONT_LBL).pack(side="left")
encoder_menu = tk.OptionMenu(enc_frame, var_encoder, *ENCODERS.keys(),
                              command=lambda _: save_config())
encoder_menu.config(bg=ENTRY_BG, fg=TEXT, font=("Courier New", 9),
                    activebackground=ACCENT2, activeforeground=TEXT,
                    highlightthickness=0, relief="flat", state="disabled",
                    indicatoron=True, bd=0)
encoder_menu["menu"].config(bg=ENTRY_BG, fg=TEXT, font=("Courier New", 9),
                              activebackground=ACCENT2)
encoder_menu.pack(side="left", padx=(8,0), fill="x", expand=True)

# CRF slider
crf_frame = tk.Frame(frame_join, bg=PANEL)
crf_frame.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(4,4))
tk.Label(crf_frame, text="QUALITY  CRF:", bg=PANEL, fg=MUTED,
         font=("Courier New", 9)).pack(side="left")
crf_slider = tk.Scale(crf_frame, from_=0, to=51, orient="horizontal",
                      variable=var_crf, length=180,
                      bg=PANEL, fg=TEXT, highlightthickness=0,
                      troughcolor=ACCENT2, activebackground=ACCENT,
                      font=("Courier New", 8), showvalue=True, state="disabled")
crf_slider.pack(side="left", padx=(8,8))
tk.Label(crf_frame, text="0=lossless  18=very good  23=good  51=low",
         bg=PANEL, fg=MUTED, font=("Courier New", 7)).pack(side="left")

frame_join.columnconfigure(0, weight=1)

# ── Show CUT panel by default ────────────────────────────────────
frame_cut.pack(fill="both", padx=16, pady=(0,4))

# Restore slider/dropdown state from loaded config
toggle_crf()

# ── Action button ────────────────────────────────────────────────
btn_frame = tk.Frame(root, bg=BG)
btn_frame.pack(pady=(4,6))
btn_action = make_btn(btn_frame, "  ✂  CUT & SAVE  ", run_cut)
btn_action.pack(ipadx=20, ipady=6)

# ── Status bar ───────────────────────────────────────────────────
status_bar = tk.Frame(root, bg=ACCENT2, height=28)
status_bar.pack(fill="x", side="bottom")
tk.Label(status_bar, textvariable=status_var, bg=ACCENT2, fg=TEXT,
         font=("Courier New", 9), anchor="w").pack(side="left", padx=12, pady=4)

root.mainloop()