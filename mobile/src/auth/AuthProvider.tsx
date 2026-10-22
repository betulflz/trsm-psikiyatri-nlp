import { useQueryClient } from '@tanstack/react-query';
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { createApiClient, type ApiClient } from '@/api/client';
import { ApiError } from '@/api/errors';
import { useServerUrl } from '@/api/ServerUrlProvider';
import type { GirisYaniti, Kullanici } from '@/api/types';
import { sameServer } from '@/lib/serverOrigin';
import { tokenStore } from './tokenStore';

type Status = 'yukleniyor' | 'girissiz' | 'girisli' | 'baglanti_hatasi';
type Value = {
  status: Status;
  user: Kullanici | null;
  client: ApiClient;
  login: (kullaniciAdi: string, sifre: string) => Promise<void>;
  logout: () => Promise<void>;
  retry: () => void;
};

const AuthContext = createContext<Value | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const { url, ready } = useServerUrl();
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<Status>('yukleniyor');
  const [user, setUser] = useState<Kullanici | null>(null);
  const [attempt, setAttempt] = useState(0);
  const tokenRef = useRef<string | null>(null);
  const tokenServerRef = useRef<string | null>(null);
  const urlRef = useRef(url);
  urlRef.current = url;

  const logout = useCallback(async () => {
    tokenRef.current = null;
    tokenServerRef.current = null;
    await tokenStore.clear();
    queryClient.clear();
    setUser(null);
    setStatus('girissiz');
  }, [queryClient]);

  const client = useMemo(
    () =>
      createApiClient({
        getBaseUrl: () => urlRef.current,
        // Token yalnızca kendisini veren sunucuya gönderilir; adres değişirse hiç eklenmez.
        getToken: () =>
          tokenRef.current && tokenServerRef.current && sameServer(tokenServerRef.current, urlRef.current) ? tokenRef.current : null,
        onUnauthorized: () => {
          void logout();
        },
      }),
    [logout],
  );

  useEffect(() => {
    if (!ready) return;
    let cancelled = false;
    (async () => {
      setStatus('yukleniyor');
      const stored = await tokenStore.get().catch(() => null);
      if (!stored || !sameServer(stored.server, urlRef.current)) {
        if (stored) await tokenStore.clear().catch(() => {});
        if (!cancelled) setStatus('girissiz');
        return;
      }
      tokenRef.current = stored.token;
      tokenServerRef.current = stored.server;
      try {
        const me = await client.get<Kullanici>('/api/m/ben');
        if (!cancelled) {
          setUser(me);
          setStatus('girisli');
        }
      } catch (error) {
        if (cancelled) return;
        if (error instanceof ApiError && error.kind === 'yetkisiz') return; // logout zaten çağrıldı
        setStatus('baglanti_hatasi');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [ready, client, attempt]);

  // Sunucu adresi oturum açıldıktan sonra değişirse eski sunucunun oturumu kapatılır.
  useEffect(() => {
    if (status === 'girisli' && tokenServerRef.current && !sameServer(tokenServerRef.current, url)) {
      void logout();
    }
  }, [url, status, logout]);

  const login = useCallback(
    async (kullaniciAdi: string, sifre: string) => {
      const result = await client.post<GirisYaniti>('/api/m/giris', { kullanici_adi: kullaniciAdi, sifre });
      tokenRef.current = result.token;
      tokenServerRef.current = urlRef.current;
      await tokenStore.set(result.token, urlRef.current);
      setUser(result.kullanici);
      setStatus('girisli');
    },
    [client],
  );

  const value = useMemo<Value>(
    () => ({ status, user, client, login, logout, retry: () => setAttempt((n) => n + 1) }),
    [status, user, client, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): Value {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth AuthProvider içinde kullanılmalı');
  return value;
}
