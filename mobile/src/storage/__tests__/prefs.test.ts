import AsyncStorage from '@react-native-async-storage/async-storage';
import { prefs, type DraftPatient } from '../prefs';

jest.mock('@react-native-async-storage/async-storage', () =>
  require('@react-native-async-storage/async-storage/jest/async-storage-mock'),
);

const mockSecure = new Map<string, string>();
jest.mock('expo-secure-store', () => ({
  setItemAsync: jest.fn(async (key: string, value: string) => void mockSecure.set(key, value)),
  getItemAsync: jest.fn(async (key: string) => mockSecure.get(key) ?? null),
  deleteItemAsync: jest.fn(async (key: string) => void mockSecure.delete(key)),
}));

const draft = (id: string, tc: string | null, sahipId = 1): DraftPatient => ({
  id,
  sahipId,
  adSoyad: 'Ali Rıza',
  cinsiyet: 'Erkek',
  dogumTarihi: '1985-04-02',
  tcKimlik: tc,
  sayfalar: ['file:///a.jpg'],
  olusturma: '2026-10-12T10:00:00.000Z',
});

beforeEach(async () => {
  mockSecure.clear();
  await AsyncStorage.clear();
});

it('T.C. Kimlik No düz metin AsyncStorage içine yazılmaz, okununca geri gelir', async () => {
  await prefs.setDrafts([draft('t1', '10000000146')]);
  const raw = (await AsyncStorage.getItem('psikord.taslaklar')) ?? '';
  expect(raw).not.toContain('10000000146');
  expect(raw).toContain('Ali Rıza');
  expect([...mockSecure.values()]).toContain('10000000146');
  expect(await prefs.getDrafts()).toEqual([draft('t1', '10000000146')]);
});

it('silinen taslağın güvenli deposundaki numarası da silinir', async () => {
  await prefs.setDrafts([draft('t1', '10000000146'), draft('t2', null)]);
  await prefs.setDrafts([draft('t2', null)]);
  expect(mockSecure.size).toBe(0);
  expect((await prefs.getDrafts()).map((d) => d.id)).toEqual(['t2']);
});

it('taslaklar yalnızca sahibine görünür', async () => {
  await prefs.setDrafts([draft('t1', '10000000146', 1), draft('t2', null, 2)]);
  expect((await prefs.getDraftsFor(1)).map((d) => d.id)).toEqual(['t1']);
  expect((await prefs.getDraftsFor(2)).map((d) => d.id)).toEqual(['t2']);
  expect(await prefs.getDraftsFor(3)).toEqual([]);
});

it('taslağı yalnızca sahibi silebilir, başkasınınki yerinde kalır', async () => {
  await prefs.setDrafts([draft('t1', '10000000146', 1)]);
  expect(await prefs.removeDraft('t1', 2)).toBe(false);
  expect((await prefs.getDraftsFor(1)).map((d) => d.id)).toEqual(['t1']);
  expect([...mockSecure.values()]).toContain('10000000146');
  expect(await prefs.removeDraft('t1', 1)).toBe(true);
  expect(await prefs.getDraftsFor(1)).toEqual([]);
  expect(mockSecure.size).toBe(0);
});
