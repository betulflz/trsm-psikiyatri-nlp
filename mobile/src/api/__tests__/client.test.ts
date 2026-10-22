import { createApiClient } from '../client';
import { ApiError, describeError } from '../errors';

type AnyMock = jest.Mock<any, any>;

function jsonResponse(status: number, body: unknown) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  } as Response);
}

function makeClient(fetchImpl: AnyMock, token: string | null = 'tok') {
  const onUnauthorized = jest.fn();
  const client = createApiClient({
    getBaseUrl: () => 'http://sunucu:8765/',
    getToken: () => token,
    onUnauthorized,
    fetchImpl: fetchImpl as unknown as typeof fetch,
    timeoutMs: 50,
  });
  return { client, onUnauthorized };
}

it('başarılı GET token ekler ve JSON döner', async () => {
  const fetchImpl: AnyMock = jest.fn(() => jsonResponse(200, { a: 1 }));
  const { client } = makeClient(fetchImpl);
  await expect(client.get('/api/m/ozet')).resolves.toEqual({ a: 1 });
  const [url, init] = fetchImpl.mock.calls[0];
  expect(url).toBe('http://sunucu:8765/api/m/ozet');
  expect(init.headers.Authorization).toBe('Bearer tok');
});

it('token yoksa Authorization başlığı yok', async () => {
  const fetchImpl: AnyMock = jest.fn(() => jsonResponse(200, {}));
  const { client } = makeClient(fetchImpl, null);
  await client.post('/api/m/giris', { kullanici_adi: 'x' });
  expect(fetchImpl.mock.calls[0][1].headers.Authorization).toBeUndefined();
  expect(fetchImpl.mock.calls[0][1].body).toBe('{"kullanici_adi":"x"}');
});

it('401 oturumu kapatır ve yetkisiz hatası verir', async () => {
  const fetchImpl = jest.fn(() => jsonResponse(401, { hata: 'Oturum geçersiz', kod: 'oturum_gecersiz' }));
  const { client, onUnauthorized } = makeClient(fetchImpl);
  await expect(client.get('/api/m/ben')).rejects.toMatchObject({ kind: 'yetkisiz', status: 401 });
  expect(onUnauthorized).toHaveBeenCalledTimes(1);
});

it('giriş uç noktasındaki 401 oturumu kapatmaz', async () => {
  const fetchImpl = jest.fn(() => jsonResponse(401, { hata: 'Hatalı', kod: 'hatali_giris' }));
  const { client, onUnauthorized } = makeClient(fetchImpl);
  await expect(client.post('/api/m/giris', {})).rejects.toMatchObject({ kind: 'yetkisiz', kod: 'hatali_giris' });
  expect(onUnauthorized).not.toHaveBeenCalled();
});

it.each([
  [403, 'yasak'],
  [404, 'bulunamadi'],
  [400, 'istek'],
  [500, 'sunucu'],
])('%i → %s', async (status, kind) => {
  const fetchImpl = jest.fn(() => jsonResponse(status, { hata: 'Mesaj', kod: 'k' }));
  const { client } = makeClient(fetchImpl);
  const error = (await client.get('/x').catch((e) => e)) as ApiError;
  expect(error.kind).toBe(kind);
  expect(error.message).toBe('Mesaj');
});

it('ağ hatası ve zaman aşımı → ag', async () => {
  const failing = jest.fn(() => Promise.reject(new TypeError('Network request failed')));
  await expect(makeClient(failing).client.get('/x')).rejects.toMatchObject({ kind: 'ag', status: null });

  const hanging = jest.fn(
    (_url: string, init: RequestInit) =>
      new Promise((_resolve, reject) => {
        init.signal?.addEventListener('abort', () => reject(new Error('aborted')));
      }),
  );
  await expect(makeClient(hanging).client.get('/x')).rejects.toMatchObject({ kind: 'ag' });
});

it('JSON olmayan hata gövdesi', async () => {
  const fetchImpl = jest.fn(() =>
    Promise.resolve({ ok: false, status: 502, json: () => Promise.reject(new Error('html')) } as Response),
  );
  await expect(makeClient(fetchImpl).client.get('/x')).rejects.toMatchObject({ kind: 'sunucu' });
});

it('describeError kullanıcı dostu başlık verir', () => {
  expect(describeError(new ApiError('ag', null, 'x')).title).toBe('Sunucuya ulaşılamıyor');
  expect(describeError(new ApiError('yasak', 403, 'Bu alan rolünüze kapalı.')).message).toBe('Bu alan rolünüze kapalı.');
  expect(describeError(new Error('?')).title).toBe('Beklenmeyen hata');
});
