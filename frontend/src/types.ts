export interface TranscriptionRecord {
  id: string;
  text: string;
  language: string;
  timestamp: Date;
  duration: number;
}

export type RecorderState = 'idle' | 'recording' | 'processing';
