import type { TranscriptionRecord } from '../../types';

interface Props {
  history: TranscriptionRecord[];
  currentId: string | null;
  onSelect: (r: TranscriptionRecord) => void;
  onDelete: (id: string) => void;
  onClear: () => void;
}

function relativeTime(ts: string): string {
  const diff = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} hr ago`;
  return `${Math.floor(diff / 86400)} d ago`;
}

export default function TranscriptionHistory({ history, currentId, onSelect, onDelete, onClear }: Props) {
  function handleClear() {
    if (window.confirm('Clear all transcription history?')) {
      onClear();
    }
  }

  return (
    <div className="bg-gray-800 rounded-xl flex flex-col h-full">
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
        <h2 className="text-lg font-semibold text-white">History</h2>
        {history.length > 0 && (
          <button
            onClick={handleClear}
            className="text-sm text-red-400 hover:text-red-300 transition-colors"
          >
            Clear All
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {history.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No transcriptions yet</p>
        ) : (
          history.map(record => (
            <div
              key={record.id}
              onClick={() => onSelect(record)}
              className={`bg-gray-700 rounded-lg p-3 cursor-pointer hover:bg-gray-600 transition-colors border-2 ${
                record.id === currentId ? 'border-blue-500' : 'border-transparent'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <p className="text-white text-sm flex-1 truncate">
                  {record.text.slice(0, 80)}{record.text.length > 80 ? '…' : ''}
                </p>
                <button
                  onClick={e => { e.stopPropagation(); onDelete(record.id); }}
                  className="text-gray-400 hover:text-red-400 transition-colors flex-shrink-0 mt-0.5"
                  aria-label="Delete"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs bg-blue-600 text-white px-1.5 py-0.5 rounded-full">
                  {record.language === 'auto' ? 'Auto' : record.language.toUpperCase()}
                </span>
                <span className="text-xs bg-gray-600 text-gray-300 px-1.5 py-0.5 rounded-full">
                  {record.duration.toFixed(1)}s
                </span>
                <span className="text-xs text-gray-400 ml-auto">{relativeTime(record.timestamp)}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
