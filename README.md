# ✂ SimpleMp4Cutter

A simple, clean MP4 cutter and joiner with GUI — powered by **ffmpeg** and built with Python/tkinter.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey?logo=windows)
![License](https://img.shields.io/badge/License-MIT-green)
![ffmpeg](https://img.shields.io/badge/Powered%20by-ffmpeg-orange?logo=ffmpeg)
![Version](https://img.shields.io/badge/Version-1.4-brightgreen)

---

## 📸 Features

- **✂ Cut Mode** — Cut any video by setting a start and end time (precise to milliseconds)
- **⛓ Join Mode** — Merge two video files, with optional re-encoding for a seamless join
- **🎬 Video Preview** — Live frame preview with timeline scrubber directly in the app
- **⌨ Keyframe Navigation** — Jump between keyframes with ← → arrow keys
- **🖱 Click-to-Jump** — Click anywhere on the timeline to jump to that position
- **[ IN / OUT ]** — Set cut points directly from the timeline with IN/OUT marker buttons
- **🚫 Reset Buttons** — Reset start/end times back to defaults with one click
- **GPU Encoder Support** — Choose between CPU (libx264), NVIDIA (h264_nvenc), AMD (h264_amf) or Intel QuickSync (h264_qsv)
- **Live Progress Window** — See real-time ffmpeg output and elapsed time while processing
- **CRF Quality Slider** — Control encode quality from 0 (lossless) to 51 (low)
- **✅ ffmpeg Status** — Header shows ffmpeg status at a glance — click ⚙ to set path manually
- **Auto-detect ffmpeg** — Prompts automatically on first start if ffmpeg is not found
- **Window position memory** — App reopens exactly where you left it
- **Smart file naming** — Output files are automatically named `_part01`, `_part02`, `_joined01` etc. — no overwrites
- **Config persistence** — All settings saved automatically next to the exe

---

## 🚀 Requirements

- Python 3.8+
- [ffmpeg](https://ffmpeg.org/download.html) (includes `ffprobe`)
- Pillow (`pip install Pillow`)

No other Python packages required.

---

## 📦 Installation

1. **Clone this repo:**
   ```bash
   git clone https://github.com/IschNehmDirGleichDemTabletWeg/SimpleMp4Cutter.git
   cd SimpleMp4Cutter
   ```

2. **Install Pillow:**
   ```bash
   pip install Pillow
   ```

3. **Install ffmpeg** — Download from [ffmpeg.org](https://ffmpeg.org/download.html) and either add it to your system PATH or select it manually inside the app (the app will ask on first start if it can't find it).

4. **Run:**
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
| **Timeline** | Scrub through the video — click anywhere or drag |
| **← →** | Jump between keyframes with arrow keys |
| **[ Set IN point** | Sets the start time to the current timeline position |
| **Set OUT point ]** | Sets the end time to the current timeline position |
| **◀ Set Start** | Sets start time to `00:00:00.000` |
| **⏱ Set End** | Auto-reads video duration via ffprobe |
| **🚫** | Resets start to `00:00:00.000` / clears end time |

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
| `libx264` | CPU only | Slow | Best compatibility, most accurate CRF |
| `h264_nvenc` | NVIDIA GPU | Very fast | Requires CUDA driver |
| `h264_amf` | AMD GPU | Very fast | Requires AMD drivers |
| `h264_qsv` | Intel GPU | Fast | Requires Intel drivers |

> **Note on GPU file size:** GPU encoders need a higher CRF value (28–35) to produce similar file sizes as CPU at CRF 23. The quality difference is minimal — GPU encoders are simply more efficient per bit.

---

## ⚙️ ffmpeg

The ✅/❌ indicator in the top-right of the header shows whether ffmpeg is available.
Click **⚙** to manually select your `ffmpeg.exe`.

**Auto-detect search order:**
1. Manually set path
2. System `PATH`
3. `C:\ffmpeg\bin\ffmpeg.exe`
4. `C:\Program Files\ffmpeg\bin\ffmpeg.exe`
5. `C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe`

---

## 🔨 Build as .exe

To create a standalone Windows executable (no Python required on target machine):

```bash
pip install pyinstaller
python -m PyInstaller --onefile --windowed --icon=icon.ico --name="MP4Cutter" mp4_cutter.py
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

## 🗺 Roadmap

| Version | Feature |
|---|---|
| ✅ v1.0 | Basic cut & join GUI |
| ✅ v1.1 | GPU encoder support, live progress window, English UI |
| ✅ v1.2 | Video preview, timeline scrubber, IN/OUT markers, keyframe navigation |
| ✅ v1.3 | Click-to-jump on timeline, ffmpeg auto-prompt on first start |
| ✅ v1.4 | Window position memory, reset buttons for start/end time |
| 🔜 v2.0 | Fine-tune cut mode — frame-accurate cut point selection |

---

## 📁 Project Structure

```
SimpleMp4Cutter/
├── mp4_cutter.py       # Main application
├── icon.ico            # App icon
├── README.md           # This file
├── .gitattributes      # GitHub language detection fix
├── .gitignore          # Git ignore rules
└── LICENSE             # MIT License
```

---

## 📝 License

MIT License — free to use, modify and share.

---

*Built with ❤️ and ffmpeg*
