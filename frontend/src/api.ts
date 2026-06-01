import type { TranscriptionRecord } from './types';

export async function transcribeAudio(blob: Blob, language: string): Promise<TranscriptionRecord> {
  const formData = new FormData();
  formData.append('audio', blob, 'recording.webm');
  formData.append('language', language);

  const response = await fetch('/api/transcribe', {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Transcription failed: ${response.statusText}`);
  }

  return response.json() as Promise<TranscriptionRecord>;
}
