import { validateKimlik } from '../dogrulama';
import { movePage } from '../taslak';

jest.mock('expo-file-system', () => ({}));
jest.mock('expo-secure-store', () => ({}));
jest.mock('@react-native-async-storage/async-storage', () =>
  require('@react-native-async-storage/async-storage/jest/async-storage-mock'),
);

const today = new Date('2026-10-12T12:00:00Z');
const valid = { adSoyad: 'Ali Rıza', cinsiyet: 'Erkek' as const, dogumTarihi: '1985-04-02', tcKimlik: '10000000146' };

it('geçerli form hatasız', () => {
  expect(validateKimlik(valid, today)).toEqual({});
});

it('ad soyad zorunlu, en az iki kelime', () => {
  expect(validateKimlik({ ...valid, adSoyad: '  ' }, today).adSoyad).toBe('Ad soyad gerekli.');
  expect(validateKimlik({ ...valid, adSoyad: 'Ali' }, today).adSoyad).toBe('Ad ve soyadı birlikte girin.');
});

it('TC boşsa sorun yok, doluysa algoritma kontrolü', () => {
  expect(validateKimlik({ ...valid, tcKimlik: '' }, today).tcKimlik).toBeUndefined();
  expect(validateKimlik({ ...valid, tcKimlik: '10000000147' }, today).tcKimlik).toBe('Geçerli bir T.C. Kimlik No girin.');
});

it('gelecekteki doğum tarihi reddedilir', () => {
  expect(validateKimlik({ ...valid, dogumTarihi: '2027-01-01' }, today).dogumTarihi).toBe('Doğum tarihi gelecekte olamaz.');
});

it('sayfa sırası', () => {
  expect(movePage(['a', 'b', 'c'], 0, 1)).toEqual(['b', 'a', 'c']);
  expect(movePage(['a', 'b', 'c'], 0, -1)).toEqual(['a', 'b', 'c']);
  expect(movePage(['a', 'b', 'c'], 2, 1)).toEqual(['a', 'b', 'c']);
});
