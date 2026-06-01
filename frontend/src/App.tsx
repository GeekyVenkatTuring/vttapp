import { useState } from 'react';
import { useTranscriptionHistory } from './hooks/useTranscriptionHistory';
import type { TranscriptionRecord } from './types/transcription';
import TranscriptionDisplay from './components/Display/TranscriptionDisplay';
import TranscriptionHistory from './components/History/TranscriptionHistory';
import LanguageSelector from './components/Settings/LanguageSelector';
import AudioRecorder from './components/Recorder/AudioRecorder';
import Waveform from './components/Recorder/Waveform';

export default function App() {
  const { history, addRecord, deleteRecord, clearHistory } = useTranscriptionHistory();
  const [currentRecord, setCurrentRecord] = useState<TranscriptionRecord | null>(null);
  const [language, setLanguage] = useState('auto');
  const [isProcessing, setIsProcessing] = useState(false);

  function handleTranscriptionComplete(record: TranscriptionRecord) {
    addRecord(record);
    setCurrentRecord(record);
    setIsProcessing(false);
  }

  return (
    <div className="bg-gray-900 min-h-screen text-white flex flex-col">
      <header className="bg-gradient-to-r from-blue-700 via-blue-600 to-indigo-700 px-6 py-4 flex items-center justify-between shadow-lg">
        <h1 className="text-2xl font-bold tracking-tight">🎙️ VoiceToText</h1>
        <LanguageSelector value={language} onChange={setLanguage} />
      </header>

      <main className="flex-1 p-4 lg:p-6">
        <div className="grid lg:grid-cols-5 gap-4 lg:gap-6">
          <div className="lg:col-span-2 flex flex-col gap-4">
            <Waveform />
            <AudioRecorder
              onTranscriptionComplete={handleTranscriptionComplete}
              language={language}
              disabled={isProcessing}
              onStreamChange={() => {}}
            />
            <TranscriptionDisplay record={currentRecord} />
          </div>

          <div className="lg:col-span-3 min-h-64 lg:min-h-0">
            <TranscriptionHistory
              history={history}
              currentId={currentRecord?.id ?? null}
              onSelect={setCurrentRecord}
              onDelete={deleteRecord}
              onClear={clearHistory}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
