import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { useAuth } from '@/auth/AuthProvider';
import type { HastaDetayi, HastaOzeti, Kullanici, NotSayfasi, Ozet, SistemDurumu } from './types';

function useUserKey() {
  const { user } = useAuth();
  return user?.id ?? 0;
}

export function useOzet() {
  const { client } = useAuth();
  const uid = useUserKey();
  return useQuery({ queryKey: ['ozet', uid], queryFn: () => client.get<Ozet>('/api/m/ozet') });
}

export function useHastalar() {
  const { client } = useAuth();
  const uid = useUserKey();
  return useQuery({
    queryKey: ['hastalar', uid],
    queryFn: async () => (await client.get<{ hastalar: HastaOzeti[] }>('/api/m/hastalar')).hastalar,
  });
}

export function useHasta(id: number) {
  const { client } = useAuth();
  const uid = useUserKey();
  return useQuery({
    queryKey: ['hasta', uid, id],
    queryFn: () => client.get<HastaDetayi>(`/api/m/hastalar/${id}`),
    enabled: Number.isFinite(id),
  });
}

export function useNotlar(id: number) {
  const { client } = useAuth();
  const uid = useUserKey();
  return useInfiniteQuery({
    queryKey: ['notlar', uid, id],
    initialPageParam: null as number | null,
    queryFn: ({ pageParam }) =>
      client.get<NotSayfasi>(`/api/m/hastalar/${id}/notlar?limit=20${pageParam ? `&once=${pageParam}` : ''}`),
    getNextPageParam: (last) => last.sonraki,
    enabled: Number.isFinite(id),
  });
}

export function useSistem() {
  const { client } = useAuth();
  const uid = useUserKey();
  return useQuery({ queryKey: ['sistem', uid], queryFn: () => client.get<SistemDurumu>('/api/m/sistem') });
}

export function useKullanicilar() {
  const { client } = useAuth();
  const uid = useUserKey();
  return useQuery({
    queryKey: ['kullanicilar', uid],
    queryFn: async () => (await client.get<{ kullanicilar: Kullanici[] }>('/api/m/kullanicilar')).kullanicilar,
  });
}
