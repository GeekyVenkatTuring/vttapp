import { useState } from 'react';
import { AudioRecorder } from './components/Recorder/AudioRecorder';
import { Waveform } from './components/Recorder/Waveform';
import type { TranscriptionRecord, RecorderState } from './types';

function App() {
  const [currentRecord, setCurrentRecord] = useState<TranscriptionRecord | null>(null);
  const [history, setHistory] = useState<TranscriptionRecord[]>([]);
  const [language] = useState<string>('auto');
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);

  const recorderState: RecorderState = stream !== null ? 'recording' : isProcessing ? 'processing' : 'idle';

  const handleTranscriptionComplete = (record: TranscriptionRecord) => {
    setCurrentRecord(record);
    setHistory((prev) => [record, ...prev]);
  };

  return (
    <div className="flex min-h-screen flex-col bg-gray-900 text-white">
      <header className="border-b border-gray-800 px-8 py-6">
        <h1 className="text-2xl font-bold text-white">Voice-to-Text</h1>
      </header>

      <main className="flex flex-1 flex-col items-center gap-8 px-4 py-8">
        <section className="flex flex-col items-center gap-6">
          <Waveform stream={stream} isRecording={recorderState === 'recording'} />
          <AudioRecorder
            onTranscriptionComplete={handleTranscriptionComplete}
            onStreamChange={setStream}
            onProcessingChange={setIsProcessing}
            language={language}
          />
        </section>

        {/* Current result */}
        <div className="w-full max-w-2xl rounded-xl bg-gray-800 p-6" style={{ minHeight: '80px' }}>
          {recorderState === 'processing' ? (
            <p className="italic text-gray-400">Transcribing...</p>
          ) : currentRecord ? (
            <p className="text-white">{currentRecord.text}</p>
          ) : (
            <p className="text-gray-500">Your transcription will appear here</p>
          )}
        </div>

        {/* History */}
        <div className="w-full max-w-2xl">
          <h2 className="mb-3 text-lg font-semibold text-gray-300">History</h2>
          <ul className="flex flex-col gap-2">
            {history.map((record) => (
              <li key={record.id} className="rounded-lg bg-gray-800 p-4 text-sm text-gray-300">
                <span className="font-mono text-xs text-gray-500">
                  {record.timestamp instanceof Date
                    ? record.timestamp.toLocaleTimeString()
                    : new Date(record.timestamp).toLocaleTimeString()}
                </span>
                <p className="mt-1">{record.text}</p>
              </li>
            ))}
          </ul>
        </div>
      </main>
    </div>
  );
}

export default App;
