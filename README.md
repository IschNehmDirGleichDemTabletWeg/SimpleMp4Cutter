# ✂ SimpleMp4Cutter

A simple, clean MP4 cutter and joiner with GUI — powered by **ffmpeg** and built with Python/tkinter.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey?logo=windows)
![License](https://img.shields.io/badge/License-MIT-green)
![ffmpeg](https://img.shields.io/badge/Powered%20by-ffmpeg-orange?logo=ffmpeg)
![Version](https://img.shields.io/badge/Version-1.9-brightgreen)

---
<img width="676" height="830" alt="grafik" src="https://github.com/user-attachments/assets/27346dd5-7a80-44ae-a1ff-5f80e7524b19" />
<img width="676" height="829" alt="grafik" src="https://github.com/user-attachments/assets/42bb2e3c-9baa-40a0-b441-1da9addc939d" />




## 📸 Features

- **✂ Cut Mode** — Cut any video by setting a start and end time (precise to milliseconds)
- **⛓ Join Mode** — Merge two video files, with optional re-encoding for a seamless join
- **🎬 Video Preview** — Live frame preview with timeline scrubber directly in the app
- **⌨ Keyframe Navigation** — Jump between keyframes with ← → arrow keys
- **🖱 Click-to-Jump** — Click anywhere on the timeline to jump to that position
- **[ IN / OUT ]** — Set cut points directly from the timeline, with silent validation (IN always < OUT)
- **🚫 Reset Buttons** — Reset start/end times back to defaults with one click
- **GPU Encoder Support** — Choose between CPU (libx264), NVIDIA (h264_nvenc), AMD (h264_amf) or Intel QuickSync (h264_qsv)
- **Inline Progress Bar** — Percentage and elapsed time shown in the status bar — no popup window
- **🚫 Cancel Join** — Button turns yellow during join and allows cancelling mid-process
- **⏮⏭ Prev/Next Navigation** — Browse through all videos in the same folder with Prev/Next buttons
- **📂 Dynamic Path Labels** — Long paths are automatically shortened, always showing the filename
- **CRF Quality Slider** — Control encode quality from 0 (lossless) to 51 (low)
- **✅ ffmpeg Status** — Header shows ffmpeg status at a glance — click ⚙ to set path manually
- **Auto-detect ffmpeg** — Prompts automatically on first start if ffmpeg is not found
- **Window position memory** — App reopens exactly where you left it
- **Smart file naming** — Output files are automatically named `_part01`, `_part02`, `_joined01` etc. — no overwrites
- **Config persistence** — All settings saved automatically next to the exe

---

## 🎬 Usage

### ✂ Cut Mode

| Field | Description |
|---|---|
| **Source File** | The video you want to cut |
| **Output Folder** | Where the cut file is saved |
| **Timeline** | Scrub through the video — click anywhere or drag |
| **← →** | Jump between keyframes with arrow keys |
| **[ Set IN** | Sets start time to current timeline position (only if < OUT) |
| **Set OUT ]** | Sets end time to current timeline position (only if > IN) |
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

## 🗺 Roadmap

| Version | Feature |
|---|---|
| ✅ v1.0 | Basic cut & join GUI |
| ✅ v1.1 | GPU encoder support, live progress window, English UI |
| ✅ v1.2 | Video preview, timeline scrubber, IN/OUT markers, keyframe navigation |
| ✅ v1.3 | Click-to-jump on timeline, ffmpeg auto-prompt on first start |
| ✅ v1.4 | Window position memory, reset buttons for start/end time |
| ✅ v1.5 | New warm light blue/orange theme — easier on the eyes |
| ✅ v1.6 | Inline progress bar, cancel join button, log file, layout & UX polish |
| ✅ v1.7 | Fix terminal window flashing on Windows, disable logging |
| ✅ v1.8 | Prev/Next file navigation, dynamic path labels, smaller buttons, new scissors icon |
| ✅ v1.9 | Compact layout, START/END inline with time fields, clean marker labels |
| 🔜 v2.0 | Fine-tune cut mode — frame-accurate cut point selection |
| 🔜 v3.0 | Linux & Mac compatibility |

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

> `mp4cutter.log` and `mp4cutter_config.json` are created automatically next to the exe and are excluded from git.

---

## 📝 License

MIT License — free to use, modify and share.

---

*Built with ❤️ and ffmpeg*
