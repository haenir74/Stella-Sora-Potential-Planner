# Changelog

## [Web Migration Prototype] - 2026-03-01

### Changed: Technology Stack
The application architecture has been completely migrated from a Windows Desktop Application to a modern Web Browser Application.
- **Language**: Python 3.11 \-\> TypeScript / React
- **UI Framework**: PyQt5 \-\> React (Vite)
- **Screen Capture**: `mss` & `pygetwindow` \-\> `navigator.mediaDevices.getDisplayMedia` & HTML5 `<canvas>`
- **Computer Vision**: `cv2` (Python) \-\> `opencv.js` running in a Web Worker
- **Data Decompression**: `zlib` (Python) \-\> `pako` (JavaScript)

### Added: API Specifications

#### Data Engine (`src/decoder.ts`)
- `decodeSstoyUrl(url: string): DecodeResult`
  - Parses an SSToy hash string (`v2d-`, `v3d-`).
  - Decodes Base91 strings into byte arrays.
  - Inflates DEFLATE binary stream using `pako.inflateRaw`.
  - Maps binary VarInt representations back to `BuildData` structures mapped with legacy IDs.

#### Canvas Vision Manager (`src/capture.ts`)
- `requestScreenMedia(): Promise<MediaStream | null>`
  - Requests user permission to capture a window/screen and returns a video stream.
- `getCaptureArea(videoWidth: number, videoHeight: number, roiRatio: Rect, faceOffsetRatio?: Rect): Rect`
  - Replaces `load_resolution.py`. Accepts mathematical ROI ratios and dynamic intrinsic video sizes, returning explicit device pixel coordinates for `CanvasRenderingContext2D.getImageData`.

#### OpenCV Web Worker (`src/vision.worker.ts`)
- Accepts `MessageEvent` objects on background threads.
- `MATCH_TEMPLATE` Payload: `{ id: number, image: ImageData, template: ImageData, isMasked: boolean }`
- Internal operations: Uses `cv.matchTemplate` with either `TM_SQDIFF_NORMED` (Face) or `TM_CCOEFF_NORMED` (Skill).
- Returns: `MATCH_RESULT` with computed scores safely marshalled across thread boundaries without freezing the React UI.
