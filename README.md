# ✂ SimpleMp4Cutter

A simple, clean MP4 cutter and joiner with GUI — powered by **ffmpeg** and built with Python/tkinter.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey?logo=windows)
![License](https://img.shields.io/badge/License-MIT-green)
![ffmpeg](https://img.shields.io/badge/Powered%20by-ffmpeg-orange?logo=ffmpeg)

---

## 📸 Features

- **✂ Cut Mode** — Cut any video by setting a start and end time (precise to milliseconds)
- **⛓ Join Mode** — Merge two video files, with optional re-encoding for a seamless join
- **GPU Encoder Support** — Choose between CPU (libx264), NVIDIA (h264_nvenc), AMD (h264_amf) or Intel QuickSync (h264_qsv)
- **Live Progress Window** — See real-time ffmpeg output and elapsed time while processing
- **CRF Quality Slider** — Control encode quality from 0 (lossless) to 51 (low)
- **Auto-detect ffmpeg** — or manually point to your `ffmpeg.exe`
- **Smart file naming** — Output files are automatically named `_part01`, `_part02`, `_joined01` etc. — no overwrites
- **Config persistence** — All settings saved automatically to `~/.mp4cutter_config.json`

---

## 🚀 Requirements

- Python 3.8+
- [ffmpeg](https://ffmpeg.org/download.html) (includes `ffprobe`)

No additional Python packages required — only the standard library + `tkinter`.

---

## 📦 Installation

1. **Clone this repo:**
   ```bash
   git clone https://github.com/IschNehmDirGleichDemTabletWeg/SimpleMp4Cutter.git
   cd SimpleMp4Cutter
   ```

2. **Install ffmpeg** — Download from [ffmpeg.org](https://ffmpeg.org/download.html) and either add it to your system PATH or select it manually inside the app.

3. **Run:**
   ```bash
   python mp4_cutter.py
   ```

---

## 🎬 Usage

### ✂ Cut Mode

| Field | Description |
|---|---|
| **Source File** | The video you want to cut |
| **Output Folder** | Where the cut file is saved |
| **ffmpeg.exe** | Path to ffmpeg (auto-detected if in PATH) |
| **Start Time** | Use `◀ Set Start` to set `00:00:00.000` |
| **End Time** | Use `⏱ Set End` to auto-read video duration via ffprobe |

**Time format:** `HH:MM:SS.mmm` or plain seconds like `83.5`

Output is saved as `originalname_part01.mp4`, `_part02.mp4`, etc.

---

### ⛓ Join Mode

1. Select **File 1** and **File 2**
2. Optionally enable **Re-Encode** for a seamless join at the cut point
3. Choose your **encoder** and adjust the **CRF slider**
4. Hit **⛓ JOIN FILES** — output saves next to File 1 as `_joined01.mp4`

#### Encoder Options

| Encoder | Requires | Speed | Notes |
|---|---|---|---|
| `libx264` | CPU only | Slow | Best compatibility |
| `h264_nvenc` | NVIDIA GPU | Very fast | Requires CUDA driver |
| `h264_amf` | AMD GPU | Very fast | Requires AMD drivers |
| `h264_qsv` | Intel GPU | Fast | Requires Intel drivers |

> **Tip:** If you're unsure which GPU encoder to use, try `h264_nvenc` (NVIDIA) first. If it fails, fall back to `libx264`.

---

## 🔨 Build as .exe

To create a standalone Windows executable (no Python required on target machine):

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=icon.ico --name="MP4Cutter" mp4_cutter.py
```

| Flag | Effect |
|---|---|
| `--onefile` | Everything packed into a single `.exe` |
| `--windowed` | No black terminal window on launch |
| `--icon=icon.ico` | Uses the scissors icon |
| `--name="MP4Cutter"` | Name of the output file |

Output: `dist\MP4Cutter.exe`

> Note: `dist\` and `build\` folders are already excluded via `.gitignore`

---



The app searches in this order:
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