import { ApiError } from '../errors';
import { shouldRetryQuery } from '../retry';

it('ağ hatası en fazla bir kez daha denenir (kullanıcı 30 sn iskelet görmesin)', () => {
  const error = new ApiError('ag', null, '');
  expect(shouldRetryQuery(0, error)).toBe(true);
  expect(shouldRetryQuery(1, error)).toBe(false);
});

it('sunucu hatası iki kez daha denenir', () => {
  const error = new ApiError('sunucu', 500, '');
  expect(shouldRetryQuery(1, error)).toBe(true);
  expect(shouldRetryQuery(2, error)).toBe(false);
});

it.each(['yetkisiz', 'yasak', 'bulunamadi', 'istek'] as const)('%s hiç yeniden denenmez', (kind) => {
  expect(shouldRetryQuery(0, new ApiError(kind, 400, ''))).toBe(false);
});
