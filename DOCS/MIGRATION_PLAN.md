# Web Migration Plan

## 1. Goal
Migrate the Stella-Sora Potential Planner from a Python Windows Desktop application to a Web Browser-based application (TypeScript/JavaScript). The Web App will leverage Web APIs (`getDisplayMedia`, Canvas API, Web Workers) to achieve the same screen recognition capabilities.

## 2. Technical Obstacles & Solutions

### Obstacle 1: Screen Capture & Resolution Mapping
- **Problem:** Browsers cannot scan arbitrary desktop coordinates using WinAPI.
- **Solution:** 
  - Use `navigator.mediaDevices.getDisplayMedia({ video: true })` to request the user to select the game window.
  - Draw the video stream onto a hidden `<canvas>` element.
  - **Coordinate Mapping:** Instead of calculating absolute screen coordinates, calculate coordinates relative to the intrinsic size of the selected window (using `videoWidth` and `videoHeight`).

### Obstacle 2: Heavy Template Matching in the Main Thread
- **Problem:** `cv2.matchTemplate` operations represent heavy matrix calculations. If done on the main thread, the web UI will freeze.
- **Solution:** 
  - Migrate OpenCV operations to **Web Workers**.
  - Extract the ROI image data using `canvas.getContext('2d').getImageData()` and pass the `ImageData` buffer to the Web Worker.
  - The worker performs matching using **OpenCV.js** and posts the result back to the main thread.

### Obstacle 3: OpenCV.js Footprint & Performance
- **Problem:** The full OpenCV.js build is large (megabytes) and `cv.matchTemplate` might perform slowly depending on the browser's WebAssembly performance.
- **Solution:**
  - Use an asynchronous loading strategy for `opencv.js`.
  - Only process frames a few times per second (e.g., polling every 500ms instead of continuous busy-loop) to save CPU cycles.
  - Ensure image shrinking (`scale_factor`) is correctly handled in JS before triggering `matchTemplate` to minimize matrix sizes.

### Obstacle 4: Data Decoding Logic
- **Problem:** The python `decoder.py` uses python-specific byte handling (`int.from_bytes`, etc.).
- **Solution:** 
  - Re-implement Base91 decoding and Varint parsing in TypeScript.
  - Use `pako` library for Zlib (DEFLATE) decompression in the browser.
  - Extract `builds.json` interface cleanly into a TypeScript `interface`.

## 3. Step-by-Step Implementation Strategy
**Phase 1 (Data Layer):**
1. Implement TypeScript version of `decoder.py`.
2. Map `app-saveload.ts` logic maintaining schema consistency.

**Phase 2 (Capture & Canvas Layer):**
1. Create React/Vanilla UI with window selection button (`getDisplayMedia`).
2. Implement rendering of the live feed on a canvas.
3. Repurpose `load_resolution.py` logic to calculate Canvas-relative ROI bounds based on intrinsic video resolution.

**Phase 3 (Vision Layer):**
1. Setup Web Worker + OpenCV.js.
2. Port `worker.py` logic (`detect_face`, `detect_skill`).
3. Handle template preloading (fetching image assets via `fetch` API, storing them as OpenCV Mat objects in the worker).

**Phase 4 (Integration & UI):**
1. Connect Worker results to UI state.
2. Update `CHANGELOG.md` with final API specs.
