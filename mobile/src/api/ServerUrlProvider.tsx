import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { prefs } from '@/storage/prefs';

const DEFAULT_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://127.0.0.1:8765';

type Value = { url: string; ready: boolean; setUrl: (url: string) => Promise<void> };
const ServerUrlContext = createContext<Value | null>(null);

export function ServerUrlProvider({ children }: { children: ReactNode }) {
  const [url, setUrlState] = useState(DEFAULT_URL);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    prefs
      .getServerUrl()
      .then((saved) => {
        if (saved) setUrlState(saved);
      })
      .catch(() => {})
      .finally(() => setReady(true));
  }, []);

  const setUrl = async (next: string) => {
    const cleaned = next.trim().replace(/\/+$/, '');
    setUrlState(cleaned);
    await prefs.setServerUrl(cleaned);
  };

  return <ServerUrlContext.Provider value={{ url, ready, setUrl }}>{children}</ServerUrlContext.Provider>;
}

export function useServerUrl(): Value {
  const value = useContext(ServerUrlContext);
  if (!value) throw new Error('useServerUrl ServerUrlProvider içinde kullanılmalı');
  return value;
}
