import { ageOn, describeRemoved, normalizeRect } from '../maske';

it('kutu her sürükleme yönünde sol üstten başlar', () => {
  expect(normalizeRect({ x: 50, y: 40 }, { x: 10, y: 100 })).toEqual({ x: 10, y: 40, w: 40, h: 60 });
});

it('yaş doğum gününe göre hesaplanır', () => {
  expect(ageOn('1992-10-29', new Date(2026, 9, 29))).toBe(34);
  expect(ageOn('1992-10-30', new Date(2026, 9, 29))).toBe(33);
});

it('silinen bilgiler türkçe özetlenir', () => {
  expect(describeRemoved({ ad: 1, tc: 2 })).toBe('Otomatik silinenler: 1 ad, 2 TC no');
  expect(describeRemoved({})).toBeNull();
  expect(describeRemoved(undefined)).toBeNull();
});
