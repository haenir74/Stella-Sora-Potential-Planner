# System Architecture

## 1. Overview
The **Stella-Sora Potential Planner** was originally built as a Windows Desktop application using Python 3.11, PyQt5, OpenCV, and MSS. Its primary purpose is to capture the game screen in real-time, identify characters and skills using template matching, and map them with decoded build data (from the SSToy URLs).

## 2. Core Modules

### 2.1 Window Capture & Resolution (`load_resolution.py`)
- **Key Technology:** `pygetwindow`, `ctypes` (WinAPI)
- **Role:** Finds the target game window by title and calculates its client area bounds (absolute screen coordinates). It translates predefined ROI (Region of Interest) ratios into explicit coordinates to be captured by `mss`.

### 2.2 Template Matching Engine (`worker.py`)
- **Key Technology:** `mss`, `cv2` (OpenCV-Python), `PyQt5.QtCore.QThread`
- **Role:** Continuously captures the calculated ROIs of the screen.
  - **`detect_face`:** Uses `cv2.TM_SQDIFF_NORMED` with mask support to identify the characters.
  - **`detect_skill`:** Uses `cv2.TM_CCOEFF_NORMED` to identify specific skill icons for the matched characters.
- **Concurrency:** Runs on a background thread (`QThread`) emitting signals back to the UI upon match successes.

### 2.3 Build Decoder (`sstoy_loader/decoder.py`)
- **Key Technology:** `zlib`, Custom Base91 Decoder
- **Role:** Parses URL parameters, decodes Base91 encodings, decompresses standard DEFLATE (`zlib`), and parses bit/varint packed binary data into Python dictionaries representing characters and their potential skill levels.

## 3. Web Migration Scope
Currently, the application relies heavily on OS-level APIs (Win32 for resolution mapping, `mss` for high-speed absolute screen fetching) and native C-extensions (OpenCV, PyQt5). The web version will require a paradigm shift from OS-level access to Browser-level access (`getDisplayMedia`, Web Workers, Canvas API).
