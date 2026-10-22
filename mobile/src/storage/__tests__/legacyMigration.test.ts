import AsyncStorage from '@react-native-async-storage/async-storage';
import { migrateLegacyKeys, resetLegacyMigrationForTests } from '../legacyMigration';

jest.mock('@react-native-async-storage/async-storage', () =>
  require('@react-native-async-storage/async-storage/jest/async-storage-mock'),
);

const mockSecure = new Map<string, string>();
jest.mock('expo-secure-store', () => ({
  setItemAsync: jest.fn(async (key: string, value: string) => void mockSecure.set(key, value)),
  getItemAsync: jest.fn(async (key: string) => mockSecure.get(key) ?? null),
  deleteItemAsync: jest.fn(async (key: string) => void mockSecure.delete(key)),
}));

beforeEach(async () => {
  mockSecure.clear();
  await AsyncStorage.clear();
  resetLegacyMigrationForTests();
});

it('eski Kartela anahtarlarını veri kaybetmeden Psikord anahtarlarına taşır', async () => {
  await AsyncStorage.setItem('kartela.tema', 'koyu');
  await AsyncStorage.setItem('kartela.taslaklar', JSON.stringify([{ id: 't1' }]));
  mockSecure.set('kartela.oturum', 'tok');
  mockSecure.set('kartela.oturum.sunucu', 'http://x');
  mockSecure.set('kartela.tc.t1', '10000000146');

  await migrateLegacyKeys();

  expect(await AsyncStorage.getItem('psikord.tema')).toBe('koyu');
  expect(await AsyncStorage.getItem('kartela.tema')).toBeNull();
  expect(await AsyncStorage.getItem('psikord.taslaklar')).toContain('t1');
  expect(mockSecure.get('psikord.oturum')).toBe('tok');
  expect(mockSecure.get('psikord.oturum.sunucu')).toBe('http://x');
  expect(mockSecure.get('psikord.tc.t1')).toBe('10000000146');
  expect([...mockSecure.keys()].some((k) => k.startsWith('kartela.'))).toBe(false);
});

it('yeni anahtarda değer varsa eskisinin üstüne yazmaz', async () => {
  await AsyncStorage.setItem('kartela.tema', 'koyu');
  await AsyncStorage.setItem('psikord.tema', 'acik');

  await migrateLegacyKeys();

  expect(await AsyncStorage.getItem('psikord.tema')).toBe('acik');
});
