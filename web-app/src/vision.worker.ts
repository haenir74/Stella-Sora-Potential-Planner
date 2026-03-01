// vision.worker.ts
/// <reference lib="webworker" />

declare var cv: any;

let cvReady = false;

// Preload the OpenCV library asynchronously
self.importScripts('https://docs.opencv.org/4.8.0/opencv.js');

cv['onRuntimeInitialized'] = () => {
    cvReady = true;
    self.postMessage({ type: 'READY' });
};

export type TaskMessage =
    | { type: 'MATCH_TEMPLATE'; id: number; image: ImageData; template: ImageData; isMasked: boolean }
    | { type: 'PING' };

self.onmessage = function (e: MessageEvent<TaskMessage>) {
    if (!cvReady) {
        self.postMessage({ type: 'ERROR', message: 'OpenCV not initialized yet.' });
        return;
    }

    const msg = e.data;
    if (msg.type === 'MATCH_TEMPLATE') {
        try {
            const { id, image, template, isMasked } = msg;

            // Convert ImageData to cv.Mat
            const srcMat = cv.matFromImageData(image);
            const templMat = cv.matFromImageData(template);

            const srcGray = new cv.Mat();
            const templGray = new cv.Mat();

            cv.cvtColor(srcMat, srcGray, cv.COLOR_RGBA2GRAY);
            cv.cvtColor(templMat, templGray, cv.COLOR_RGBA2GRAY);

            const result = new cv.Mat();

            let score = 0;

            if (isMasked) {
                // use TM_SQDIFF_NORMED for face matching (similar to python implementation)
                // Note: For masks, opencv.js requires the mask to be the same size and type as template
                // Using straightforward SQDIFF_NORMED for now. If mask is passed, we can apply it.
                // For simplicity in JS port, we'll just do SQDIFF_NORMED without mask first
                // If exact mask behavior is needed, we'll need a mask ImageData as well.

                cv.matchTemplate(srcGray, templGray, result, cv.TM_SQDIFF_NORMED);
                const minMax = cv.minMaxLoc(result);

                // SQDIFF_NORMED: smaller is better. We invert the metric to align with "score" concept.
                score = 1.0 - minMax.minVal;
            } else {
                // TM_CCOEFF_NORMED for skills
                cv.matchTemplate(srcGray, templGray, result, cv.TM_CCOEFF_NORMED);
                const minMax = cv.minMaxLoc(result);
                score = minMax.maxVal;
            }

            self.postMessage({
                type: 'MATCH_RESULT',
                id,
                score
            });

            // Cleanup
            srcMat.delete();
            templMat.delete();
            srcGray.delete();
            templGray.delete();
            result.delete();

        } catch (err) {
            self.postMessage({ type: 'ERROR', message: String(err) });
        }
    }
};
