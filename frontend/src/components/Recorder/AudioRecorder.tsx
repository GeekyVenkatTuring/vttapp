import { useState, useRef, useEffect } from 'react';
import type { TranscriptionRecord } from '../../types';
import { transcribeAudio } from '../../api';

interface Props {
  onTranscriptionComplete: (record: TranscriptionRecord) => void;
  onStreamChange: (stream: MediaStream | null) => void;
  onProcessingChange: (processing: boolean) => void;
  language: string;
  disabled?: boolean;
}

export default function AudioRecorder({
  onTranscriptionComplete,
  onStreamChange,
  onProcessingChange,
  language,
  disabled = false,
}: Props) {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const startTimeRef = useRef<number>(0);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  const startRecording = async () => {
    if (disabled) return;
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    streamRef.current = stream;
    onStreamChange(stream);
    chunksRef.current = [];

    const mediaRecorder = new MediaRecorder(stream);
    mediaRecorderRef.current = mediaRecorder;

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };

    mediaRecorder.onstop = async () => {
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
      onStreamChange(null);
      setIsProcessing(true);
      onProcessingChange(true);
      try {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        const record = await transcribeAudio(blob, language);
        onTranscriptionComplete(record);
      } finally {
        setIsProcessing(false);
        onProcessingChange(false);
      }
    };

    mediaRecorder.start();
    startTimeRef.current = Date.now();
    setElapsed(0);
    setIsRecording(true);

    timerRef.current = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTimeRef.current) / 1000));
    }, 1000);
  };

  const stopRecording = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setIsRecording(false);
    mediaRecorderRef.current?.stop();
  };

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  return (
    <div className="flex flex-col items-center gap-4 bg-gray-800 rounded-xl p-6">
      {isRecording && (
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-red-500 animate-pulse" />
          <span className="font-mono text-lg text-white">{formatTime(elapsed)}</span>
        </div>
      )}
      {isProcessing && (
        <div className="flex items-center gap-2">
          <svg className="h-5 w-5 animate-spin text-blue-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-blue-400">Transcribing...</span>
        </div>
      )}
      <div className="flex gap-4">
        {!isRecording && !isProcessing && (
          <button
            onClick={startRecording}
            disabled={disabled}
            className="flex items-center gap-2 rounded-full bg-green-600 px-6 py-3 font-semibold text-white transition-colors hover:bg-green-500 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <svg className="h-6 w-6" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 1a4 4 0 0 1 4 4v7a4 4 0 0 1-8 0V5a4 4 0 0 1 4-4zm-1 16.93V20H9v2h6v-2h-2v-2.07A8.001 8.001 0 0 0 20 12h-2a6 6 0 0 1-12 0H4a8.001 8.001 0 0 0 7 7.93z" />
            </svg>
            Start Recording
          </button>
        )}
        {isRecording && (
          <button
            onClick={stopRecording}
            className="flex items-center gap-2 rounded-full bg-red-600 px-6 py-3 font-semibold text-white transition-colors hover:bg-red-500"
          >
            <svg className="h-6 w-6" fill="currentColor" viewBox="0 0 24 24">
              <rect x="6" y="6" width="12" height="12" />
            </svg>
            Stop
          </button>
        )}
      </div>
    </div>
  );
}
