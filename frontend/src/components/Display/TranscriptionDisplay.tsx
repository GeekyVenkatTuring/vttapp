import { useState } from 'react';
import type { TranscriptionRecord } from '../../types';

interface Props {
  record: TranscriptionRecord | null;
}

export default function TranscriptionDisplay({ record }: Props) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    if (!record) return;
    navigator.clipboard.writeText(record.text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  function handleExport() {
    if (!record) return;
    const blob = new Blob([record.text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transcription-${record.id}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="bg-gray-800 rounded-xl p-6">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold text-white">Transcription</h2>
        {record && (
          <div className="flex items-center gap-2">
            <span className="text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">
              {record.language === 'auto' ? 'Auto' : record.language.toUpperCase()}
            </span>
            <span className="text-xs bg-gray-600 text-gray-200 px-2 py-0.5 rounded-full">
              {record.duration.toFixed(1)}s
            </span>
          </div>
        )}
      </div>

      <textarea
        readOnly
        value={record?.text ?? ''}
        placeholder="Your transcription will appear here..."
        className="w-full h-40 bg-gray-700 text-white text-lg rounded-lg p-3 resize-none border border-gray-600 placeholder-gray-500 focus:outline-none"
      />

      <div className="flex gap-2 mt-3">
        <button
          onClick={handleCopy}
          disabled={!record}
          className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm rounded-lg transition-colors"
        >
          {copied ? (
            <>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Copied!
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              Copy
            </>
          )}
        </button>

        <button
          onClick={handleExport}
          disabled={!record}
          className="flex items-center gap-1.5 px-4 py-2 bg-gray-600 hover:bg-gray-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm rounded-lg transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Export .txt
        </button>
      </div>
    </div>
  );
}
