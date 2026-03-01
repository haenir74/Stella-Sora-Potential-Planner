export const REFERENCE_WIDTH = 1280;
export const REFERENCE_HEIGHT = 720;

export const ROIS = [
    { x: 0.16016, y: 0.20139, w: 0.14453, h: 0.34722 },
    { x: 0.42969, y: 0.20139, w: 0.14453, h: 0.34722 },
    { x: 0.69922, y: 0.20139, w: 0.14453, h: 0.34722 }
];

export const FACE_OFFSET = { x: -0.05078, y: -0.02083, w: 0.05569, h: 0.16278 };

export interface Rect {
    x: number;
    y: number;
    w: number;
    h: number;
}

/**
 * Parses intrinsic video element dimensions and relative ROIs into explicit Canvas pixel locations.
 */
export function getCaptureArea(
    videoWidth: number,
    videoHeight: number,
    roiRatio: Rect,
    faceOffsetRatio?: Rect
): Rect {
    const roiX = Math.floor(videoWidth * roiRatio.x);
    const roiY = Math.floor(videoHeight * roiRatio.y);

    if (faceOffsetRatio) {
        const offsetX = Math.floor(videoWidth * faceOffsetRatio.x);
        const offsetY = Math.floor(videoHeight * faceOffsetRatio.y);
        const offsetW = Math.floor(videoWidth * faceOffsetRatio.w);
        const offsetH = Math.floor(videoHeight * faceOffsetRatio.h);

        return {
            x: roiX + offsetX,
            y: roiY + offsetY,
            w: offsetW,
            h: offsetH
        };
    } else {
        return {
            x: roiX,
            y: roiY,
            w: Math.floor(videoWidth * roiRatio.w),
            h: Math.floor(videoHeight * roiRatio.h)
        };
    }
}

export async function requestScreenMedia(): Promise<MediaStream | null> {
    try {
        const stream = await navigator.mediaDevices.getDisplayMedia({
            video: {
                displaySurface: 'window'
            }
        });
        return stream;
    } catch (error) {
        console.error('Failed to get screen capture:', error);
        return null;
    }
}
