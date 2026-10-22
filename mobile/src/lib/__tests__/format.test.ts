import { formatDate, formatNumber, initials } from '../format';

it('tarih', () => {
  expect(formatDate('2025-09-03')).toBe('3 Eyl 2025');
  expect(formatDate(null)).toBe('Tarihsiz');
  expect(formatDate('bozuk')).toBe('Tarihsiz');
});

it('sayı binlik ayracı', () => {
  expect(formatNumber(41676)).toBe('41.676');
  expect(formatNumber(434)).toBe('434');
});

it('baş harfler', () => {
  expect(initials('Ayşe Kaya')).toBe('AK');
  expect(initials('ismail ışık')).toBe('İI');
  expect(initials('Demo')).toBe('D');
  expect(initials('')).toBe('?');
});
