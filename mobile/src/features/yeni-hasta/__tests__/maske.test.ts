import { ageOn, describeRemoved, normalizeRect, outsideRects, toCropFraction } from '../maske';

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

it('kırpma alanı orana çevrilir ve dışı dört kutuyla kaplanır', () => {
  const size = { width: 200, height: 400 };
  const crop = { x: 20, y: 100, w: 160, h: 200 };
  expect(toCropFraction(crop, size)).toEqual({ x: 0.1, y: 0.25, w: 0.8, h: 0.5 });
  expect(toCropFraction(crop, { width: 0, height: 0 })).toBeNull();
  const outside = outsideRects(crop, size);
  expect(outside).toHaveLength(4);
  const covered = outside.reduce((sum, r) => sum + r.w * r.h, 0) + crop.w * crop.h;
  expect(covered).toBe(200 * 400);
});
