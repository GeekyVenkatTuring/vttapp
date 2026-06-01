import { useState, useCallback } from 'react';
import type { TranscriptionRecord } from '../types/transcription';

const STORAGE_KEY = 'vtt_history';

function load(): TranscriptionRecord[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function save(records: TranscriptionRecord[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(records));
}

export function useTranscriptionHistory() {
  const [history, setHistory] = useState<TranscriptionRecord[]>(load);

  const addRecord = useCallback((record: TranscriptionRecord) => {
    setHistory(prev => {
      const next = [record, ...prev];
      save(next);
      return next;
    });
  }, []);

  const deleteRecord = useCallback((id: string) => {
    setHistory(prev => {
      const next = prev.filter(r => r.id !== id);
      save(next);
      return next;
    });
  }, []);

  const clearHistory = useCallback(() => {
    setHistory([]);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  return { history, addRecord, deleteRecord, clearHistory };
}
