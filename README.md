# ✂ SimpleMp4Cutter

A simple, clean MP4 cutter and joiner with GUI — powered by **ffmpeg** and built with Python/tkinter.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey?logo=windows)
![License](https://img.shields.io/badge/License-MIT-green)
![ffmpeg](https://img.shields.io/badge/Powered%20by-ffmpeg-orange?logo=ffmpeg)

---

## 📸 Features

- **✂ Cut Mode** — Cut any video by setting a start and end time (precise to milliseconds)
- **⛓ Join Mode** — Merge two video files with optional re-encoding for a seamless join
- **Auto-detect ffmpeg** — or manually point to your `ffmpeg.exe`
- **Smart file naming** — Output files are automatically named `_part01`, `_part02`, `_joined01` etc. — no overwrites
- **Config persistence** — All settings saved automatically to `~/.mp4cutter_config.json`
- **CRF Quality Slider** — When re-encoding, choose quality from 0 (perfect) to 51 (low)

---

## 🚀 Requirements

- Python 3.8+
- [ffmpeg](https://ffmpeg.org/download.html) (includes `ffprobe`)

No additional Python packages required — only the standard library + `tkinter`.

---

## 📦 Installation

1. **Download or clone this repo:**
   ```bash
   git clone https://github.com/IschNehmDirGleichDemTabletWeg/SimpleMp4Cutter.git
   cd SimpleMp4Cutter
   ```

2. **Make sure ffmpeg is installed.**
   - Download from [ffmpeg.org](https://ffmpeg.org/download.html)
   - Either add it to your system PATH, or point to it manually inside the app

3. **Run the app:**
   ```bash
   python mp4_cutter.py
   ```

---

## 🎬 Usage

### Cut Mode
| Field | Description |
|---|---|
| **Quelldatei** | Source video file |
| **Zielordner** | Output folder |
| **ffmpeg.exe** | Path to ffmpeg (auto-detected if in PATH) |
| **Startzeit** | Start time — use `◀ Start` to set to `00:00:00.000` |
| **Endzeit** | End time — use `⏱ Ende` to auto-read video duration |

**Time format:** `HH:MM:SS.mmm` or just seconds like `83.5`

### Join Mode
1. Select **Datei 1** and **Datei 2**
2. Optionally enable **Re-Encoding** and adjust the **CRF slider** for a seamless join
3. Hit **⛓ ZUSAMMENFÜGEN** — output saves next to Datei 1 as `_joined01.mp4`

> **Tip:** Use Re-Encoding if you notice a small video lag at the join point. CRF 18 = very high quality.

---

## ⚙️ ffmpeg auto-detect paths

The app searches for `ffmpeg.exe` in this order:
1. Manually set path in the UI
2. System `PATH`
3. `C:\ffmpeg\bin\ffmpeg.exe`
4. `C:\Program Files\ffmpeg\bin\ffmpeg.exe`
5. `C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe`

---

## 📁 Project Structure

```
SimpleMp4Cutter/
├── mp4_cutter.py       # Main application
├── icon.ico            # App icon
├── README.md           # This file
├── .gitignore          # Git ignore rules
└── LICENSE             # MIT License
```

---

## 📝 License

MIT License — free to use, modify and share.

---

*Built with ❤️ and ffmpeg*
