import { useState, useRef, useEffect, useCallback } from 'react';
import { decodeSstoyUrl } from './decoder';
import { requestScreenMedia, getCaptureArea, REFERENCE_WIDTH, REFERENCE_HEIGHT, ROIS, FACE_OFFSET, Rect } from './capture';
import type { DecodeResult } from './types';
import './App.css';

function App() {
  const [url, setUrl] = useState('');
  const [buildData, setBuildData] = useState<DecodeResult | null>(null);
  const [workerReady, setWorkerReady] = useState(false);
  const [streamActive, setStreamActive] = useState(false);
  const [matchResults, setMatchResults] = useState<Record<number, number>>({});

  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const workerRef = useRef<Worker | null>(null);

  useEffect(() => {
    const worker = new Worker(new URL('./vision.worker.ts', import.meta.url), { type: 'module' });

    worker.onmessage = (e) => {
      const msg = e.data;
      if (msg.type === 'READY') {
        setWorkerReady(true);
      } else if (msg.type === 'MATCH_RESULT') {
        setMatchResults(prev => ({ ...prev, [msg.id]: msg.score }));
      } else if (msg.type === 'ERROR') {
        console.error('Worker Error:', msg.message);
      }
    };
    workerRef.current = worker;

    return () => {
      worker.terminate();
    };
  }, []);

  const handleDecode = () => {
    const res = decodeSstoyUrl(url);
    setBuildData(res);
  };

  const startCapture = async () => {
    const stream = await requestScreenMedia();
    if (stream && videoRef.current) {
      videoRef.current.srcObject = stream;
      setStreamActive(true);
    }
  };

  const processFrame = useCallback(() => {
    if (!streamActive || !videoRef.current || !canvasRef.current || !workerRef.current || !workerReady) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });

    if (!ctx) return;

    const vw = video.videoWidth;
    const vh = video.videoHeight;

    if (vw === 0 || vh === 0) return;

    if (canvas.width !== vw || canvas.height !== vh) {
      canvas.width = vw;
      canvas.height = vh;
    }

    ctx.drawImage(video, 0, 0, vw, vh);

    ROIS.forEach((roi, index) => {
      const faceRect: Rect = getCaptureArea(vw, vh, roi, FACE_OFFSET);

      if (faceRect.x < 0 || faceRect.y < 0 || faceRect.x + faceRect.w > vw || faceRect.y + faceRect.h > vh) return;

      const imgData = ctx.getImageData(faceRect.x, faceRect.y, faceRect.w, faceRect.h);

      // Dummy check sending actual image as mock template to verify OpenCV bridge
      workerRef.current?.postMessage({
        type: 'MATCH_TEMPLATE',
        id: index,
        image: imgData,
        template: imgData,
        isMasked: true
      });
    });

  }, [streamActive, workerReady]);

  // Use low polling frequency for prototype migration performance safety
  useEffect(() => {
    if (!streamActive) return;
    const timer = setInterval(processFrame, 1000);
    return () => clearInterval(timer);
  }, [streamActive, processFrame]);

  return (
    <div className="container">
      <div className="header">
        <h1>Stella-Sora Potential Planner (Web)</h1>
        <p>OpenCV.js Status: {workerReady ? '✅ Ready (Worker)' : '⏳ Loading...'}</p>
      </div>

      <div className="controls">
        <h3>1. Data Decoder (SSToy)</h3>
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Paste SSToy hash here (e.g. v2d-...)"
        />
        <button onClick={handleDecode}>Decode Build Data</button>
        {buildData && (
          <div className="results">
            {buildData.error ? (
              <p style={{ color: 'red' }}>Error: {buildData.error}</p>
            ) : (
              <p>Successfully loaded: <strong>{buildData.build_name}</strong> (Version {buildData.version}) Setup for {Object.keys(buildData.raw_characters || {}).length} Character Positions</p>
            )}
          </div>
        )}

        <h3>2. Vision Engine</h3>
        <button onClick={startCapture} disabled={streamActive}>
          {streamActive ? 'Capturing Window...' : 'Select Game Window to Capture'}
        </button>

        <div className="video-container" style={{ display: streamActive ? 'block' : 'none' }}>
          <video ref={videoRef} autoPlay playsInline muted />
          <canvas ref={canvasRef} style={{ display: 'none' }} />
        </div>

        {streamActive && (
          <div className="results">
            <h4>Worker Health Monitor (Mock Score Checks)</h4>
            <ul>
              {ROIS.map((_, i) => (
                <li key={i}>ROI {i + 1} processing result score: {matchResults[i] !== undefined ? matchResults[i].toFixed(4) : 'Waiting for frame...'}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
