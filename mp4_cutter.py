APP_VERSION = "1.9"

import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import subprocess
import threading
import os
import re
import json
import tempfile
import time
import sys

# Hide console window on Windows for all subprocess calls
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

from PIL import Image, ImageTk

# ── Config path ─────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    # Running as compiled EXE
    _BASE_DIR = os.path.dirname(sys.executable)
elif os.environ.get("MP4CUTTER_DIR"):
    # Running via start.bat — bat passes its own directory
    _BASE_DIR = os.environ["MP4CUTTER_DIR"]
else:
    # Running directly as .py script
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(_BASE_DIR, "mp4cutter_config.json")

def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_config():
    # grab current window position if root already exists
    try:
        wx = root.winfo_x()
        wy = root.winfo_y()
    except Exception:
        wx = wy = None
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
        "win_x":    wx,
        "win_y":    wy,
    }
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

# ── Colors & Fonts ──────────────────────────────────────────────
BG        = "#BADCFF"   # sanftes Hellblau — Haupthintergrund
PANEL     = "#9ECBF5"   # etwas dunkler Blau — Panel-Hintergrund
ACCENT    = "#D4721A"   # warmes Orange — Buttons & Akzente
ACCENT2   = "#F4A261"   # helles Apricot — sekundäre Buttons & Slider
TEXT      = "#0f1f30"   # dunkles Blau-Grau — gut lesbarer Text
MUTED     = "#4a6f8f"   # gedämpftes Blau — Labels & Hints
ENTRY_BG  = "#D6ECFF"   # sehr helles Blau — Eingabefelder
FONT_LBL  = ("Courier New", 10)
FONT_BTN  = ("Courier New", 11, "bold")
FONT_IN   = ("Courier New", 11)
FONT_RB   = ("Courier New", 11, "bold")
FONT_LOG  = ("Courier New", 9)

PREVIEW_W = 640
PREVIEW_H = 360

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

# ── Tooltip ──────────────────────────────────────────────────────
class Tooltip:
    """Hover tooltip for the Shortcuts… label — shows all keybindings."""
    SHORTCUTS = [
        "── Global ──────────────────────────",
        "F1             = Switch to Cut mode",
        "F2             = Switch to Join mode",
        "F5             = Cut & Save",
        "F6             = Join Files",
        "── Cut mode ────────────────────────",
        "S              = Browse Source file",
        "O              = Browse Output folder",
        "← / →         = Jump 1 keyframe",
        "Ctrl+← / →   = Jump 10 keyframes",
        "Home          = Set IN point (Start)",
        "End            = Set OUT point (End)",
        "Page Up      = Previous file in folder",
        "Page Down  = Next file in folder",
        "── Join mode ───────────────────────",
        "1              = Open File 1",
        "2              = Open File 2",
        "R              = Toggle Re-Encode",
        "E              = Open Encoder dropdown",
        "Q              = Focus CRF slider",
    ]

    def __init__(self, widget):
        self.widget  = widget
        self.tip_win = None
        self._poll   = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        if self.tip_win:
            return
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() - (len(self.SHORTCUTS) * 18 + 16)
        self.tip_win = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.bind("<Enter>", lambda e: None)
        tw.bind("<Leave>", self.hide)
        frame = tk.Frame(tw, bg="#E3CEAB", bd=1, relief="solid")
        frame.pack()
        for line in self.SHORTCUTS:
            tk.Label(frame, text=line, bg="#E3CEAB", fg="#000000",
                     font=("Courier New", 9), anchor="w", padx=10, pady=1
                     ).pack(fill="x")
        self._start_poll()

    def _start_poll(self):
        if not self.tip_win:
            return
        try:
            mx = self.widget.winfo_pointerx()
            my = self.widget.winfo_pointery()
            wx1 = self.widget.winfo_rootx(); wy1 = self.widget.winfo_rooty()
            wx2 = wx1 + self.widget.winfo_width(); wy2 = wy1 + self.widget.winfo_height()
            over_widget = wx1 <= mx <= wx2 and wy1 <= my <= wy2
            over_tip = False
            if self.tip_win:
                tx1 = self.tip_win.winfo_rootx(); ty1 = self.tip_win.winfo_rooty()
                tx2 = tx1 + self.tip_win.winfo_width(); ty2 = ty1 + self.tip_win.winfo_height()
                over_tip = tx1 <= mx <= tx2 and ty1 <= my <= ty2
            if not over_widget and not over_tip:
                self._destroy(); return
        except Exception:
            self._destroy(); return
        self._poll = self.widget.after(200, self._start_poll)

    def _destroy(self):
        if self._poll:
            try: self.widget.after_cancel(self._poll)
            except Exception: pass
            self._poll = None
        if self.tip_win:
            try: self.tip_win.destroy()
            except Exception: pass
            self.tip_win = None

    def hide(self, event=None):
        self._destroy()

# ── SimpleTooltip (individual widget hints) ──────────────────────
class SimpleTooltip:
    """Single or multi-line tooltip for individual widgets."""
    _active = []   # alle offenen Tooltips — für globales Cleanup

    def __init__(self, widget, text):
        self.widget  = widget
        self.text    = text
        self.tip_win = None
        self._poll   = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        if self.tip_win:
            return
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() - (self.text.count("\n") + 1) * 18 - 8
        self.tip_win = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.bind("<Enter>", lambda e: None)
        tw.bind("<Leave>", self.hide)
        frame = tk.Frame(tw, bg="#E3CEAB", bd=1, relief="solid")
        frame.pack()
        for line in self.text.split("\n"):
            tk.Label(frame, text=line, bg="#E3CEAB", fg="#000000",
                     font=("Courier New", 9), anchor="w", padx=8, pady=1
                     ).pack(fill="x")
        SimpleTooltip._active.append(self)
        self._start_poll()

    def _start_poll(self):
        """Poll every 200ms — destroy if mouse has left both widget and tooltip."""
        if not self.tip_win:
            return
        try:
            mx = self.widget.winfo_pointerx()
            my = self.widget.winfo_pointery()
            wx1 = self.widget.winfo_rootx()
            wy1 = self.widget.winfo_rooty()
            wx2 = wx1 + self.widget.winfo_width()
            wy2 = wy1 + self.widget.winfo_height()
            over_widget = wx1 <= mx <= wx2 and wy1 <= my <= wy2
            over_tip = False
            if self.tip_win:
                tx1 = self.tip_win.winfo_rootx()
                ty1 = self.tip_win.winfo_rooty()
                tx2 = tx1 + self.tip_win.winfo_width()
                ty2 = ty1 + self.tip_win.winfo_height()
                over_tip = tx1 <= mx <= tx2 and ty1 <= my <= ty2
            if not over_widget and not over_tip:
                self._destroy()
                return
        except Exception:
            self._destroy()
            return
        self._poll = self.widget.after(200, self._start_poll)

    def _destroy(self):
        if self._poll:
            try: self.widget.after_cancel(self._poll)
            except Exception: pass
            self._poll = None
        if self.tip_win:
            try: self.tip_win.destroy()
            except Exception: pass
            self.tip_win = None
        try: SimpleTooltip._active.remove(self)
        except ValueError: pass

    def hide(self, event=None):
        self._destroy()

def tip(widget, text):
    SimpleTooltip(widget, text)

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

def secs_to_hms(sec: float) -> str:
    h = int(sec // 3600); m = int((sec % 3600) // 60); s = sec % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"

def hms_to_secs(s: str) -> float:
    try:
        parts = s.strip().split(":")
        if len(parts) == 3:
            return int(parts[0])*3600 + int(parts[1])*60 + float(parts[2])
        elif len(parts) == 2:
            return int(parts[0])*60 + float(parts[1])
        else:
            return float(parts[0])
    except Exception:
        return 0.0

def get_video_duration(src):
    try:
        result = subprocess.run(
            [find_ffprobe(), "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", src], capture_output=True, text=True,
            creationflags=_NO_WINDOW)
        return float(result.stdout.strip())
    except Exception:
        return 0.0

def get_encoder_args(crf: int):
    label = var_encoder.get()
    codec, extra = ENCODERS.get(label, ("libx264", ["-preset", "slow"]))
    resolved = [a.replace("{crf}", str(crf)) for a in extra]
    return codec, resolved

# ── Video Preview ────────────────────────────────────────────────
_preview_job    = None   # pending after() id
_video_duration = 0.0
_current_frame  = None   # keep reference so GC doesn't collect
_keyframes      = []     # sorted list of keyframe timestamps in seconds

def load_keyframes(src):
    """Load keyframe timestamps from video file using ffprobe (runs in thread)."""
    global _keyframes
    def worker():
        global _keyframes
        try:
            result = subprocess.run(
                [find_ffprobe(), "-v", "error",
                 "-select_streams", "v:0",
                 "-skip_frame", "nokey",
                 "-show_entries", "frame=pts_time",
                 "-of", "csv=p=0", src],
                capture_output=True, text=True, timeout=30,
                creationflags=_NO_WINDOW
            )
            kf = []
            for line in result.stdout.strip().splitlines():
                try:
                    kf.append(float(line.strip()))
                except ValueError:
                    pass
            _keyframes = sorted(set(kf))
            root.after(0, lambda: status_var.set(
                f"✅  Preview ready = {len(_keyframes)} keyframes found"))
        except Exception:
            _keyframes = []
    threading.Thread(target=worker, daemon=True).start()

def load_video_info(src):
    global _video_duration
    _video_duration = get_video_duration(src)
    if _video_duration > 0:
        timeline_slider.config(to=_video_duration)
        timeline_slider.set(0)
        show_frame_at(0)
        preview_time_lbl.config(text=f"0.000s  /  {_video_duration:.3f}s")
        status_var.set("⏳  Loading keyframes…")
        load_keyframes(src)

def jump_to_keyframe(direction: int, steps: int = 1):
    """Jump forward/backward by <steps> keyframes. direction: +1 or -1."""
    if not _keyframes:
        pos = timeline_slider.get() + direction * steps
        pos = max(0, min(_video_duration, pos))
        timeline_slider.set(pos)
        show_frame_at(pos)
        return
    pos = timeline_slider.get()
    target = pos
    for _ in range(steps):
        if direction > 0:
            candidates = [k for k in _keyframes if k > target + 0.001]
            target = candidates[0] if candidates else _keyframes[-1]
        else:
            candidates = [k for k in _keyframes if k < target - 0.001]
            target = candidates[-1] if candidates else _keyframes[0]
    timeline_slider.set(target)
    show_frame_at(target)
    preview_time_lbl.config(text=f"{target:.3f}s  /  {_video_duration:.3f}s")

def on_key(event):
    ctrl = (event.state & 0x4) != 0
    steps = 10 if ctrl else 1
    if event.keysym == "Right":
        jump_to_keyframe(+1, steps)
    elif event.keysym == "Left":
        jump_to_keyframe(-1, steps)

def show_frame_at(pos_sec: float):
    """Extract a frame at pos_sec from the current source file and display it."""
    global _current_frame, _preview_job
    src = var_src.get().strip()
    if not src or not os.path.isfile(src):
        return
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        return

    def worker():
        global _current_frame
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
                tmp = tf.name
            cmd = [ffmpeg, "-y", "-ss", str(pos_sec), "-i", src,
                   "-frames:v", "1", "-q:v", "2", tmp]
            subprocess.run(cmd, capture_output=True, creationflags=_NO_WINDOW)
            if os.path.isfile(tmp):
                img = Image.open(tmp).convert("RGB")
                img.thumbnail((PREVIEW_W, PREVIEW_H), Image.LANCZOS)
                # Letterbox onto black canvas
                canvas_img = Image.new("RGB", (PREVIEW_W, PREVIEW_H), (10, 10, 20))
                x = (PREVIEW_W - img.width) // 2
                y = (PREVIEW_H - img.height) // 2
                canvas_img.paste(img, (x, y))
                photo = ImageTk.PhotoImage(canvas_img)
                root.after(0, lambda p=photo: _update_preview(p))
                os.unlink(tmp)
        except Exception:
            pass

    threading.Thread(target=worker, daemon=True).start()

def _update_preview(photo):
    global _current_frame
    _current_frame = photo
    preview_canvas.create_image(0, 0, anchor="nw", image=photo)

def on_timeline_move(val):
    """Called while scrubbing — debounce 200ms."""
    global _preview_job
    pos = float(val)
    preview_time_lbl.config(text=f"{pos:.3f}s  /  {_video_duration:.3f}s")
    if _preview_job:
        root.after_cancel(_preview_job)
    _preview_job = root.after(200, lambda: show_frame_at(pos))

def set_in_point():
    """Set start time to current timeline position — only if it's before OUT."""
    pos = timeline_slider.get()
    out_sec = hms_to_secs(var_end.get()) if var_end.get().strip() else _video_duration
    if pos < out_sec:
        var_start.set(secs_to_hms(pos))
        draw_timeline_markers()

def set_out_point():
    """Set end time to current timeline position — only if it's after IN."""
    pos = timeline_slider.get()
    in_sec = hms_to_secs(var_start.get()) if var_start.get().strip() else 0.0
    if pos > in_sec:
        var_end.set(secs_to_hms(pos))
        draw_timeline_markers()

def draw_timeline_markers():
    """Draw IN/OUT marker lines on the timeline canvas."""
    if _video_duration <= 0:
        return
    w = marker_canvas.winfo_width()
    if w < 2:
        return
    marker_canvas.delete("all")
    marker_canvas.create_rectangle(0, 0, w, 22, fill=PANEL, outline="")

    IN_COLOR  = "#1a7a3a"   # dunkles Grün — gut lesbar
    OUT_COLOR = "#a83200"   # dunkles Orange-Rot — gut lesbar

    # IN marker (green)
    try:
        in_sec = hms_to_secs(var_start.get())
        x_in = int(in_sec / _video_duration * w)
        marker_canvas.create_line(x_in, 0, x_in, 22, fill=IN_COLOR, width=3)
        marker_canvas.create_text(x_in+5, 4, text="<-", fill=IN_COLOR,
                                  font=("Courier New", 9, "bold"), anchor="nw")
    except Exception:
        pass

    # OUT marker (dark orange-red)
    try:
        out_sec = hms_to_secs(var_end.get())
        x_out = int(out_sec / _video_duration * w)
        marker_canvas.create_line(x_out, 0, x_out, 22, fill=OUT_COLOR, width=3)
        marker_canvas.create_text(x_out-5, 4, text="->", fill=OUT_COLOR,
                                  font=("Courier New", 9, "bold"), anchor="ne")
    except Exception:
        pass

    # Selected region fill
    try:
        in_sec  = hms_to_secs(var_start.get())
        out_sec = hms_to_secs(var_end.get())
        x_in  = int(in_sec  / _video_duration * w)
        x_out = int(out_sec / _video_duration * w)
        if x_out > x_in:
            marker_canvas.create_rectangle(x_in, 0, x_out, 22,
                                           fill="#8ab4d4", outline="", stipple="gray50")
    except Exception:
        pass

# ── Progress (inline, no popup) ──────────────────────────────────
import logging
logging.disable(logging.CRITICAL)  # logging disabled — no log file created

_current_proc   = None  # running ffmpeg process — for cancel
_cancelled      = False # flag to suppress on_done after cancel

def cancel_join():
    global _current_proc, _cancelled
    if _current_proc and _current_proc.poll() is None:
        _cancelled = True
        _current_proc.terminate()
        logging.info("Process cancelled by user")
    progress_bar.config(value=0)
    status_var.set("🚫  Cancelled — Ready")
    btn_action.config(text="  ⛓  JOIN FILES  ", command=run_join,
                      bg="#2e7d32", fg="#000000", state="normal")

def run_ffmpeg_with_progress(cmd, total_secs, on_done):
    """Run ffmpeg in a thread. Parse time= from stderr for % progress.
    total_secs = duration of the cut/join segment for % calculation."""
    global _current_proc
    start_wall = time.time()
    logging.info("CMD: " + " ".join(cmd))

    def worker():
        global _current_proc, _cancelled
        _cancelled = False
        try:
            proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                    text=True, encoding="utf-8", errors="replace",
                                    creationflags=_NO_WINDOW)
            _current_proc = proc
            last_line = ""
            for line in proc.stderr:
                line = line.strip()
                if not line:
                    continue
                logging.info(line)
                # ignore ffmpeg internal progress key=value lines
                if re.match(r"^(frame|fps|stream_\d|bitrate|total_size|out_time|dup_frames|drop_frames|speed|progress)=", line):
                    pass
                else:
                    last_line = line  # real info/error line
                # parse out_time_ms= or time= for progress
                m = re.search(r"out_time_ms=(\d+)", line)
                if not m:
                    m = re.search(r"time=(\d+):(\d+):([\d.]+)", line)
                    if m:
                        processed = int(m.group(1))*3600 + int(m.group(2))*60 + float(m.group(3))
                    else:
                        continue
                else:
                    processed = int(m.group(1)) / 1_000_000

                if total_secs > 0:
                    pct = min(100, int(processed / total_secs * 100))
                    elapsed = int(time.time() - start_wall)
                    root.after(0, lambda p=pct, e=elapsed:
                        status_var.set(f"⏳  {p}% = {e}s elapsed"))
                    root.after(0, lambda p=pct: progress_bar.config(value=p))

            proc.wait()
            _current_proc = None
            elapsed = int(time.time() - start_wall)
            logging.info(f"EXIT {proc.returncode}  elapsed={elapsed}s")
            if _cancelled:
                return  # cancel_join already updated the UI
            if proc.returncode == 0:
                root.after(0, lambda: on_done(True, elapsed))
            else:
                root.after(0, lambda: on_done(False, last_line))
        except Exception as e:
            _current_proc = None
            if _cancelled:
                return
            logging.error(str(e))
            root.after(0, lambda: on_done(False, str(e)))

    threading.Thread(target=worker, daemon=True).start()

# ── CUT ─────────────────────────────────────────────────────────
def _lock_geometry():
    """Re-apply current window size to prevent tkinter resizing on widget state changes."""
    root.update_idletasks()
    w = root.winfo_width()
    h = root.winfo_height()
    root.geometry(f"{w}x{h}")
    root.resizable(False, False)

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
    total_secs = max(0.001, hms_to_secs(t_end) - hms_to_secs(t_start))
    save_config()
    progress_bar.config(value=0)
    status_var.set("⏳  Cutting…  0%")
    def on_done(success, info):
        progress_bar.config(value=100 if success else 0)
        btn_action.config(command=run_cut)
        if success:
            status_var.set(f"✅  Done in {info}s  →  {os.path.basename(out_path)}")
        else:
            status_var.set(f"❌  Error: {info[:80]}")
    run_ffmpeg_with_progress(cmd, total_secs, on_done)

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
    # total duration = both files combined
    total_secs = get_video_duration(f1) + get_video_duration(f2)
    if var_reencode.get():
        crf = int(var_crf.get())
        codec, extra = get_encoder_args(crf)
        cmd = ([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", list_file,
                "-c:v", codec] + extra +
               ["-c:a", "aac", "-b:a", "192k", "-progress", "pipe:2", out_path])
    else:
        cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0",
               "-i", list_file, "-c", "copy", "-progress", "pipe:2", out_path]
    save_config()
    progress_bar.config(value=0)
    status_var.set("⏳  Joining…  0%")
    btn_action.config(text="  🚫  CANCEL  ", command=cancel_join,
                      bg="#f9a825", fg="#000000", state="normal")
    def on_done(success, info):
        os.unlink(list_file)
        progress_bar.config(value=100 if success else 0)
        btn_action.config(text="  ⛓  JOIN FILES  ", command=run_join,
                          bg="#2e7d32", fg="#000000", state="normal")
        if success:
            status_var.set(f"✅  Done in {info}s  →  {os.path.basename(out_path)}")
        else:
            status_var.set(f"❌  Error: {info[:80]}")
    run_ffmpeg_with_progress(cmd, total_secs, on_done)

# ── Browse / helpers ─────────────────────────────────────────────
def toggle_crf(*_):
    if crf_slider is None or encoder_menu is None:
        return
    state = "normal" if var_reencode.get() else "disabled"
    crf_slider.config(state=state)
    encoder_menu.config(state=state)

crf_slider   = None
encoder_menu = None

def browse_src():
    path = filedialog.askopenfilename(title="Select video file",
        filetypes=[("Video", "*.mp4 *.mkv *.mov *.avi *.webm"), ("All files", "*.*")])
    if path:
        _load_src(path)

def _load_src(path):
    var_src.set(path)
    if not var_dest.get():
        var_dest.set(os.path.dirname(path))
    var_start.set("00:00:00.000")
    var_end.set("")
    save_config()
    _update_path_labels()
    status_var.set("⏳  Loading preview…")
    root.after(100, lambda: load_video_info(path))

VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".avi", ".webm"}

def shorten_path(path, max_chars=90):
    """Shorten path from the right — single line."""
    if not path:
        return "—"
    if len(path) <= max_chars:
        return path
    return "…" + path[-(max_chars-1):]

def shorten_src_path(path, max_chars=90):
    """Same as shorten_path — single line, full path+filename from the right."""
    return shorten_path(path, max_chars)

def _natural_key(s):
    """Sort key that handles numbers naturally: file9 < file13."""
    return [int(c) if c.isdigit() else c.lower()
            for c in re.split(r'(\d+)', s)]

def _get_folder_videos(src):
    """Return naturally sorted list of video files in the same folder as src."""
    folder = os.path.dirname(src)
    return sorted([
        f for f in os.listdir(folder)
        if os.path.splitext(f)[1].lower() in VIDEO_EXTS
    ], key=_natural_key)

def next_file_in_folder():
    src = var_src.get().strip()
    if not src or not os.path.isfile(src):
        browse_src(); return
    files = _get_folder_videos(src)
    if not files: return
    current = os.path.basename(src)
    try:
        idx = (files.index(current) + 1) % len(files)
    except ValueError:
        idx = 0
    _load_src(os.path.join(os.path.dirname(src), files[idx]))
    status_var.set(f"📂  {files[idx]}  ({idx+1}/{len(files)})")

def prev_file_in_folder():
    src = var_src.get().strip()
    if not src or not os.path.isfile(src):
        browse_src(); return
    files = _get_folder_videos(src)
    if not files: return
    current = os.path.basename(src)
    try:
        idx = (files.index(current) - 1) % len(files)
    except ValueError:
        idx = 0
    _load_src(os.path.join(os.path.dirname(src), files[idx]))
    status_var.set(f"📂  {files[idx]}  ({idx+1}/{len(files)})")

def _update_path_labels():
    try:
        lbl_src_path.config(text=shorten_src_path(var_src.get()))
        lbl_dest_path.config(text=shorten_path(var_dest.get()))
    except Exception:
        pass  # labels not yet created on startup

def browse_dest():
    path = filedialog.askdirectory(title="Select output folder")
    if path:
        var_dest.set(path)
        save_config()
        _update_path_labels()

def browse_ffmpeg():
    path = filedialog.askopenfilename(title="Select ffmpeg.exe",
        filetypes=[("ffmpeg", "ffmpeg.exe"), ("Executable", "*.exe"), ("All files", "*.*")])
    if path:
        var_ffmpeg.set(path); save_config()
        status_var.set(f"✅  ffmpeg set: {path}")

def browse_join(var, lbl):
    path = filedialog.askopenfilename(title="Select video file",
        filetypes=[("Video", "*.mp4 *.mkv *.mov *.avi *.webm"), ("All files", "*.*")])
    if path:
        var.set(path)
        lbl.config(text=shorten_path(path, 90))
        save_config()
        status_var.set("")

def set_start_zero():
    """Set start time to current slider position — only if before OUT."""
    pos = timeline_slider.get()
    out_sec = hms_to_secs(var_end.get()) if var_end.get().strip() else _video_duration
    if pos < out_sec:
        var_start.set(secs_to_hms(pos))
        draw_timeline_markers()

def reset_start():
    """Reset start time back to 00:00:00.000 and move slider to 0."""
    var_start.set("00:00:00.000")
    timeline_slider.set(0)
    show_frame_at(0)
    draw_timeline_markers()

def reset_end():
    var_end.set("")
    draw_timeline_markers()

def set_end_duration():
    """Set end time to current slider position — only if after IN."""
    pos = timeline_slider.get()
    in_sec = hms_to_secs(var_start.get()) if var_start.get().strip() else 0.0
    if pos > in_sec:
        var_end.set(secs_to_hms(pos))
        draw_timeline_markers()

def set_end_to_duration():
    """Set end time to full video duration (used by reset)."""
    src = var_src.get().strip()
    if not src or not os.path.isfile(src):
        return
    try:
        duration = get_video_duration(src)
        var_end.set(secs_to_hms(duration))
        status_var.set(f"⏱  Video duration: {secs_to_hms(duration)}")
        draw_timeline_markers()
    except Exception:
        pass

def make_label(parent, text):
    return tk.Label(parent, text=text, bg=PANEL, fg=MUTED, font=FONT_LBL, anchor="w")

def make_entry(parent, textvariable, width=52):
    return tk.Entry(parent, textvariable=textvariable, width=width,
                    bg=ENTRY_BG, fg=TEXT, insertbackground=ACCENT, font=FONT_IN,
                    relief="flat", highlightthickness=1,
                    highlightcolor=ACCENT, highlightbackground=ACCENT2)

def make_btn(parent, text, cmd, color=ACCENT):
    return tk.Button(parent, text=text, command=cmd, bg=color, fg=TEXT,
                     font=FONT_BTN, relief="flat", cursor="hand2", padx=6, pady=2,
                     activebackground=ACCENT2, activeforeground=TEXT)

def make_icon_btn(parent, text, cmd, color=ACCENT):
    """Small button for browse icons — minimal padding."""
    return tk.Button(parent, text=text, command=cmd, bg=color, fg=TEXT,
                     font=FONT_BTN, relief="flat", cursor="hand2", padx=2, pady=2,
                     activebackground=ACCENT2, activeforeground=TEXT)

def switch_mode(*_):
    if var_mode.get() == "cut":
        frame_join.pack_forget()
        nav_frame.pack(fill="x", padx=16, pady=(0,2))
        file_panel.pack(fill="x", padx=16, pady=(0,2))
        preview_outer.pack(fill="x", padx=16, pady=(0,2))
        frame_cut.pack(fill="both", padx=16, pady=(0,2))
        btn_frame.pack_forget()
        btn_frame.pack(pady=(4,6), fill="x", padx=16)
        btn_action.config(text="  ✂  CUT & SAVE  ", command=run_cut,
                          bg="#2e7d32", fg="#000000")
        timeline_slider.config(state="normal")
    else:
        frame_cut.pack_forget()
        preview_outer.pack_forget()
        file_panel.pack_forget()
        nav_frame.pack_forget()
        frame_join.pack(fill="both", padx=16, pady=(0,4))
        btn_frame.pack_forget()
        btn_frame.pack(pady=(4,6), fill="x", padx=16)
        btn_action.config(text="  ⛓  JOIN FILES  ", command=run_join,
                          bg="#2e7d32", fg="#000000")
        timeline_slider.config(state="disabled")
    root.update_idletasks()

# ════════════════════════════════════════════════════════════════
# MAIN WINDOW
# ════════════════════════════════════════════════════════════════
root = tk.Tk()
APP_VERSION_STR = f"MP4 Cutter & Joiner  v{APP_VERSION}"
root.title(APP_VERSION_STR)
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

cfg = load_config()
if cfg.get("ffmpeg")  and os.path.isfile(cfg["ffmpeg"]):  var_ffmpeg.set(cfg["ffmpeg"])
if cfg.get("src")     and os.path.isfile(cfg["src"]):     var_src.set(cfg["src"])
if cfg.get("dest")    and os.path.isdir(cfg["dest"]):     var_dest.set(cfg["dest"])
if cfg.get("start"):   var_start.set(cfg["start"])
else:                  var_start.set("00:00:00.000")
if cfg.get("end"):     var_end.set(cfg["end"])
if cfg.get("join1")   and os.path.isfile(cfg["join1"]):   var_join1.set(cfg["join1"])
if cfg.get("join2")   and os.path.isfile(cfg["join2"]):   var_join2.set(cfg["join2"])
if cfg.get("encoder") and cfg["encoder"] in ENCODERS:     var_encoder.set(cfg["encoder"])
if "reencode" in cfg:  var_reencode.set(cfg["reencode"])
if "crf"      in cfg:  var_crf.set(cfg["crf"])

var_start.trace_add("write", lambda *_: (save_config(), draw_timeline_markers()))
var_end.trace_add("write",   lambda *_: (save_config(), draw_timeline_markers()))

# ── Header ──────────────────────────────────────────────────────
tk.Frame(root, bg=ACCENT, height=4).pack(fill="x")
title_frame = tk.Frame(root, bg=BG)
title_frame.pack(fill="x", padx=20, pady=(10,4))
tk.Label(title_frame, text="✂  MP4 CUTTER & JOINER", bg=BG, fg=ACCENT,
         font=("Courier New", 16, "bold")).pack(side="left")
tk.Label(title_frame, text=f"v{APP_VERSION}  powered by ffmpeg", bg=BG, fg=MUTED,
         font=("Courier New", 9)).pack(side="left", padx=(10,0), pady=(4,0))

# ffmpeg status — right side of header
ffmpeg_status_lbl = tk.Label(title_frame, text="", bg=BG,
                              font=("Courier New", 11, "bold"))
ffmpeg_status_lbl.pack(side="right", padx=(0,4))

ffmpeg_gear_btn = tk.Button(title_frame, text="⚙", bg=BG, fg=MUTED,
                             font=("Courier New", 13), relief="flat",
                             cursor="hand2", bd=0, padx=4,
                             activebackground=BG, activeforeground=TEXT,
                             command=browse_ffmpeg)
ffmpeg_gear_btn.pack(side="right")

tk.Label(title_frame, text="ffmpeg:", bg=BG, fg=MUTED,
         font=("Courier New", 9)).pack(side="right", padx=(0,4))

def update_ffmpeg_status():
    """Update the ✅/❌ indicator in the header."""
    if find_ffmpeg():
        ffmpeg_status_lbl.config(text="✅", fg="#00e676")
        ffmpeg_gear_btn.config(fg="#00e676")
    else:
        ffmpeg_status_lbl.config(text="❌", fg=ACCENT)
        ffmpeg_gear_btn.config(fg=ACCENT)

# patch browse_ffmpeg to also update status after selection
_orig_browse_ffmpeg = browse_ffmpeg
def browse_ffmpeg():
    _orig_browse_ffmpeg()
    update_ffmpeg_status()

ffmpeg_gear_btn.config(command=browse_ffmpeg)
tip(ffmpeg_gear_btn, "Click to set ffmpeg.exe path manually")

update_ffmpeg_status()

# ── Mode selector ────────────────────────────────────────────────
mode_frame = tk.Frame(root, bg=BG)
mode_frame.pack(fill="x", padx=20, pady=(0,6))
mode_inner = tk.Frame(mode_frame, bg=BG)
mode_inner.pack(anchor="center")
for val, label in [("cut", "✂  Cut Movie"), ("join", "⛓  Join Movie")]:
    rb = tk.Radiobutton(mode_inner, text=label, variable=var_mode, value=val,
                   command=switch_mode, bg=BG, fg=TEXT, selectcolor=ACCENT2,
                   activebackground=BG, activeforeground=ACCENT,
                   font=FONT_RB, relief="flat", cursor="hand2")
    rb.pack(side="left", padx=(0,20))
    if val == "cut":
        tip(rb, "F1 = Switch to Cut mode")
    else:
        tip(rb, "F2 = Switch to Join mode")

# ── Prev / Next navigation (centered) ───────────────────────────
nav_frame = tk.Frame(root, bg=BG)
nav_frame.pack(fill="x", padx=16, pady=(0,2))
nav_inner = tk.Frame(nav_frame, bg=BG)
nav_inner.pack(anchor="center")
btn_prev = make_btn(nav_inner, "◀ Prev", prev_file_in_folder, ACCENT2)
btn_prev.pack(side="left", padx=(0,8))
tip(btn_prev, "Page Up = Previous file in folder")
btn_next = make_btn(nav_inner, "Next ▶", next_file_in_folder, ACCENT2)
btn_next.pack(side="left")
tip(btn_next, "Page Down = Next file in folder")

# ════════════════════════════════════════════════════════════════
# SHARED FILE PANEL (above preview, always visible)
# ════════════════════════════════════════════════════════════════
file_panel = tk.Frame(root, bg=PANEL, padx=12, pady=2)
file_panel.pack(fill="x", padx=16, pady=(0,2))

# Row 0: SOURCE FILE label
src_header = tk.Frame(file_panel, bg=PANEL)
src_header.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0,1))
make_label(src_header, "SOURCE FILE").pack(side="left")

# Row 1: path label + Browse
lbl_src_path = tk.Label(file_panel, text="—", bg=ENTRY_BG, fg=TEXT,
                         font=("Arial", 10), anchor="w", padx=6, pady=1,
                         relief="flat")
lbl_src_path.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0,1))
btn_browse_src = make_icon_btn(file_panel, "📂", browse_src, ACCENT2)
btn_browse_src.grid(row=1, column=2, padx=(6,0), pady=(0,3))
tip(btn_browse_src, "S = Open source video file")

# Row 2: OUTPUT FOLDER label
make_label(file_panel, "OUTPUT FOLDER").grid(row=2, column=0, columnspan=3, sticky="w", pady=(0,1))

# Row 3: path label + Browse
lbl_dest_path = tk.Label(file_panel, text="—", bg=ENTRY_BG, fg=TEXT,
                          font=("Arial", 10), anchor="w", padx=6, pady=1,
                          relief="flat")
lbl_dest_path.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0,2))
btn_browse_dest = make_icon_btn(file_panel, "📁", browse_dest, ACCENT2)
btn_browse_dest.grid(row=3, column=2, padx=(6,0), pady=(0,2))
tip(btn_browse_dest, "O = Set output folder")

file_panel.columnconfigure(0, weight=1)

# Init labels from config
if var_src.get():  lbl_src_path.config(text=shorten_src_path(var_src.get()))
if var_dest.get(): lbl_dest_path.config(text=shorten_path(var_dest.get()))

# ════════════════════════════════════════════════════════════════
# VIDEO PREVIEW (always visible in Cut mode)
# ════════════════════════════════════════════════════════════════
preview_outer = tk.Frame(root, bg=BG)
preview_outer.pack(fill="x", padx=16, pady=(0,2))

preview_canvas = tk.Canvas(preview_outer, width=PREVIEW_W, height=PREVIEW_H,
                            bg="#c8e6ff", highlightthickness=1,
                            highlightbackground=ACCENT2)
preview_canvas.pack()

# Placeholder text
preview_canvas.create_text(PREVIEW_W//2, PREVIEW_H//2,
                            text="Select a source file to load preview",
                            fill=MUTED, font=("Courier New", 12))

# Timeline scrubber
timeline_outer = tk.Frame(preview_outer, bg=BG)
timeline_outer.pack(fill="x", pady=(2,0))

preview_time_lbl = tk.Label(timeline_outer, text="0.000s  /  0.000s",
                             bg=BG, fg=MUTED, font=("Courier New", 8),
                             width=26, anchor="e")
preview_time_lbl.pack(side="right", padx=(0,4))

timeline_slider = tk.Scale(timeline_outer, from_=0, to=100, orient="horizontal",
                            resolution=0.001, showvalue=False,
                            bg=BG, fg=TEXT, highlightthickness=0,
                            troughcolor=ACCENT2, activebackground=ACCENT,
                            command=on_timeline_move)
timeline_slider.pack(side="left", fill="x", expand=True)
tip(timeline_slider, "Drag or click to scrub\n← → = Jump 1 keyframe\nCtrl+← → = Jump 10 keyframes\nHome = Set IN point\nEnd   = Set OUT point")

def on_timeline_click(event):
    """Jump slider to clicked position on single click."""
    w = timeline_slider.winfo_width()
    if w <= 0 or _video_duration <= 0:
        return
    pad = 10
    rel = (event.x - pad) / (w - 2 * pad)
    rel = max(0.0, min(1.0, rel))
    pos = rel * _video_duration
    timeline_slider.set(pos)
    on_timeline_move(pos)

timeline_slider.bind("<Button-1>", on_timeline_click)

# IN/OUT marker canvas
marker_canvas = tk.Canvas(preview_outer, height=22, bg=PANEL,
                           highlightthickness=0)
marker_canvas.pack(fill="x", pady=(2,0))
marker_canvas.bind("<Configure>", lambda e: draw_timeline_markers())

# ════════════════════════════════════════════════════════════════
# CUT PANEL (time fields only)
# ════════════════════════════════════════════════════════════════
frame_cut = tk.Frame(root, bg=PANEL, padx=12, pady=6)

tk.Frame(frame_cut, bg=PANEL, height=4).grid(row=0, column=0, columnspan=3, sticky="ew")

# Time fields
time_frame = tk.Frame(frame_cut, bg=PANEL)
time_frame.grid(row=1, column=0, columnspan=3, sticky="ew")
tk.Frame(time_frame, bg=PANEL).pack(side="left", expand=True, fill="x")

single_row = tk.Frame(time_frame, bg=PANEL)
single_row.pack(side="left", expand=True, fill="x")

make_label(single_row, "START").pack(side="left", padx=(0,4))
make_entry(single_row, var_start, width=14).pack(side="left")
btn_set_start = make_btn(single_row, "Start", set_start_zero, "#2e7d32")
btn_set_start.pack(side="left", padx=(6,2))
tip(btn_set_start, "Home = Set IN point to current position")
btn_reset_start = make_btn(single_row, "🚫", reset_start, "#b84c00")
btn_reset_start.pack(side="left", padx=(0,10))
tip(btn_reset_start, "Reset start time to 00:00:00.000")

tk.Label(single_row, text="→", bg=PANEL, fg=ACCENT,
         font=("Courier New", 16, "bold")).pack(side="left", padx=(0,10))

btn_set_end = make_btn(single_row, "End", set_end_duration, "#b84c00")
btn_set_end.pack(side="left", padx=(0,2))
tip(btn_set_end, "End = Set OUT point to current position")
btn_reset_end = make_btn(single_row, "🚫", reset_end, ACCENT2)
btn_reset_end.pack(side="left", padx=(0,6))
tip(btn_reset_end, "Clear end time")
make_entry(single_row, var_end, width=14).pack(side="left")
make_label(single_row, "END").pack(side="left", padx=(4,0))


frame_cut.columnconfigure(0, weight=1)

# ════════════════════════════════════════════════════════════════
# JOIN PANEL
# ════════════════════════════════════════════════════════════════
frame_join = tk.Frame(root, bg=PANEL, padx=12, pady=2)

make_label(frame_join, "FILE 1").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0,1))
lbl_join1 = tk.Label(frame_join, text="—", bg=ENTRY_BG, fg=TEXT,
                      font=("Arial", 10), anchor="w", padx=6, pady=1, relief="flat")
lbl_join1.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0,1))
btn_join1 = make_icon_btn(frame_join, "📂", lambda: browse_join(var_join1, lbl_join1), ACCENT2)
btn_join1.grid(row=1, column=2, padx=(6,0), pady=(0,3))
tip(btn_join1, "1 = Open File 1")

make_label(frame_join, "FILE 2").grid(row=2, column=0, columnspan=3, sticky="w", pady=(0,1))
lbl_join2 = tk.Label(frame_join, text="—", bg=ENTRY_BG, fg=TEXT,
                      font=("Arial", 10), anchor="w", padx=6, pady=1, relief="flat")
lbl_join2.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0,1))
btn_join2 = make_icon_btn(frame_join, "📂", lambda: browse_join(var_join2, lbl_join2), ACCENT2)
btn_join2.grid(row=3, column=2, padx=(6,0), pady=(0,3))
tip(btn_join2, "2 = Open File 2")

tk.Label(frame_join, text="Output is saved as  _joined01.mp4  next to File 1.",
         bg=PANEL, fg=MUTED, font=("Courier New", 8)).grid(
    row=4, column=0, columnspan=3, pady=(2,0))

tk.Frame(frame_join, bg=ACCENT2, height=1).grid(row=5, column=0, columnspan=3, sticky="ew", pady=5)

cb_frame = tk.Frame(frame_join, bg=PANEL)
cb_frame.grid(row=6, column=0, columnspan=3, sticky="w")
cb_reencode = tk.Checkbutton(cb_frame, text="Re-Encode  (seamless join, slower — enables options below)",
               variable=var_reencode, bg=PANEL, fg=TEXT, selectcolor=ACCENT2,
               activebackground=PANEL, activeforeground=ACCENT,
               font=("Courier New", 9, "bold"), cursor="hand2",
               command=toggle_crf)
cb_reencode.pack(side="left")
tip(cb_reencode, "R = Toggle Re-Encode on/off")

enc_frame = tk.Frame(frame_join, bg=PANEL)
enc_frame.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(4,1))
tk.Label(enc_frame, text="ENCODER:", bg=PANEL, fg=MUTED, font=FONT_LBL).pack(side="left")
encoder_menu = tk.OptionMenu(enc_frame, var_encoder, *ENCODERS.keys(),
                              command=lambda _: save_config())
encoder_menu.config(bg=ENTRY_BG, fg=TEXT, font=("Courier New", 9),
                    activebackground=ACCENT2, activeforeground=TEXT,
                    highlightthickness=0, relief="flat", state="disabled", bd=0)
encoder_menu["menu"].config(bg=ENTRY_BG, fg=TEXT, font=("Courier New", 9),
                              activebackground=ACCENT2)
encoder_menu.pack(side="left", padx=(8,0), fill="x", expand=True)
tip(encoder_menu, "E = Open encoder dropdown\n(only active when Re-Encode is enabled)")

crf_frame = tk.Frame(frame_join, bg=PANEL)
crf_frame.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(2,2))
tk.Label(crf_frame, text="QUALITY  CRF:", bg=PANEL, fg=MUTED,
         font=("Courier New", 9)).pack(side="left")
crf_slider = tk.Scale(crf_frame, from_=0, to=51, orient="horizontal",
                      variable=var_crf, length=180,
                      bg=PANEL, fg=TEXT, highlightthickness=0,
                      troughcolor=ACCENT2, activebackground=ACCENT,
                      font=("Courier New", 8), showvalue=True, state="disabled")
crf_slider.pack(side="left", padx=(8,8))
tip(crf_slider, "Q = Focus slider, then use ↑ ↓ to adjust\n(only active when Re-Encode is enabled)")
tk.Label(crf_frame, text="0=lossless  18=very good  23=good  51=low",
         bg=PANEL, fg=MUTED, font=("Courier New", 7)).pack(side="left")

frame_join.columnconfigure(0, weight=1)
if var_join1.get(): lbl_join1.config(text=shorten_path(var_join1.get(), 90))
if var_join2.get(): lbl_join2.config(text=shorten_path(var_join2.get(), 90))

# ── Default: show CUT panel ──────────────────────────────────────
frame_cut.pack(fill="both", padx=16, pady=(0,4))
toggle_crf()

# ── Action button ────────────────────────────────────────────────
btn_frame = tk.Frame(root, bg=BG)
btn_frame.pack(pady=(4,6), fill="x", padx=16)

# Left spacer — same width as shortcut label on the right
btn_left_spacer = tk.Frame(btn_frame, bg=BG, width=80)
btn_left_spacer.pack(side="left")
btn_left_spacer.pack_propagate(False)

# Center: button fills remaining space and centers itself
btn_center = tk.Frame(btn_frame, bg=BG)
btn_center.pack(side="left", expand=True, fill="x")

btn_action = make_btn(btn_center, "  ✂  CUT & SAVE  ", run_cut, color="#2e7d32")
btn_action.config(fg="#000000")
btn_action.pack(ipadx=10, ipady=3)
tip(btn_action, "F5 = Cut & Save\nF6 = Join Files")

# ── Status bar + Progressbar ─────────────────────────────────────
status_bar = tk.Frame(root, bg=ACCENT2, height=28)
status_bar.pack(fill="x", side="bottom")

style = ttk.Style()
style.theme_use("default")
style.configure("green.Horizontal.TProgressbar",
                troughcolor=ACCENT2, background="#2e7d32",
                thickness=6)

progress_bar = ttk.Progressbar(status_bar, style="green.Horizontal.TProgressbar",
                                orient="horizontal", length=120, mode="determinate",
                                maximum=100, value=0)
progress_bar.pack(side="right", padx=(0,10), pady=8)

tk.Label(status_bar, textvariable=status_var, bg=ACCENT2, fg=TEXT,
         font=("Courier New", 9), anchor="w").pack(side="left", padx=12, pady=4)

# ── Keyboard shortcuts ───────────────────────────────────────────
def _is_cut():
    return var_mode.get() == "cut"

def _is_join():
    return var_mode.get() == "join"

def _on_global_key(event):
    # Ignore when typing in an Entry widget
    if isinstance(event.widget, tk.Entry):
        return
    k = event.keysym
    ctrl = (event.state & 0x4) != 0

    # ── Global ───────────────────────────────────────
    if k == "F1":
        var_mode.set("cut");  switch_mode(); return
    if k == "F2":
        var_mode.set("join"); switch_mode(); return
    if k == "F5":
        run_cut();  return
    if k == "F6":
        run_join(); return

    # ── Cut-side only ────────────────────────────────
    if _is_cut():
        if k == "Home":
            set_start_zero();        return
        if k == "End":
            set_end_duration();      return
        if k == "Prior":
            prev_file_in_folder();   return  # PageUp
        if k == "Next":
            next_file_in_folder();   return  # PageDown
        if k == "s":
            browse_src();            return
        if k == "o":
            browse_dest();           return
        if k in ("Right", "Left"):
            steps = 10 if ctrl else 1
            jump_to_keyframe(+1 if k == "Right" else -1, steps)
            return

    # ── Join-side only ───────────────────────────────
    if _is_join():
        if k == "1":
            browse_join(var_join1, lbl_join1); return
        if k == "2":
            browse_join(var_join2, lbl_join2); return
        if k == "r":
            var_reencode.set(not var_reencode.get())
            toggle_crf();            return
        if k == "e":
            if var_reencode.get():
                encoder_menu.event_generate("<ButtonPress-1>")
            return
        if k == "q":
            if var_reencode.get():
                crf_slider.focus_set()
            return

root.bind("<Key>", _on_global_key)

# ── Window position ──────────────────────────────────────────────
def set_window_position():
    root.update_idletasks()
    w = root.winfo_width()
    h = root.winfo_height()
    wx = cfg.get("win_x")
    wy = cfg.get("win_y")
    if wx is not None and wy is not None:
        root.geometry(f"+{wx}+{wy}")
    else:
        # center on screen
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        root.geometry(f"+{x}+{y}")

_move_job = None
def on_window_move(event):
    global _move_job
    if _move_job:
        root.after_cancel(_move_job)
    _move_job = root.after(500, save_config)

root.bind("<Configure>", on_window_move)
root.after(200, _lock_geometry)
set_window_position()

# ── Load preview if src already in config ────────────────────────
if var_src.get() and os.path.isfile(var_src.get()):
    root.after(300, lambda: load_video_info(var_src.get()))

# ── ffmpeg startup check ─────────────────────────────────────────
def check_ffmpeg_on_start():
    if not find_ffmpeg():
        messagebox.showwarning(
            "ffmpeg not found",
            "ffmpeg was not found on this system.\n\n"
            "Please select your ffmpeg.exe in the next dialog.\n"
            "Download: https://ffmpeg.org/download.html"
        )
        browse_ffmpeg()

root.after(500, check_ffmpeg_on_start)

root.mainloop()