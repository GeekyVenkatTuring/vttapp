import type { TranscriptionRecord } from './types';

export async function transcribeAudio(blob: Blob, language: string): Promise<TranscriptionRecord> {
  const formData = new FormData();
  formData.append('audio_file', blob, 'recording.webm');
  formData.append('language', language);

  const response = await fetch('/api/transcribe', {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(err.detail ?? `Transcription failed: ${response.statusText}`);
  }

  return response.json() as Promise<TranscriptionRecord>;
}
