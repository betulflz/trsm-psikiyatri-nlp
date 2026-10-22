import { ApiError, kindForStatus } from './errors';

export type ApiClient = {
  get<T>(path: string): Promise<T>;
  post<T>(path: string, body: unknown): Promise<T>;
  upload<T>(path: string, body: FormData): Promise<T>;
};

type Options = {
  getBaseUrl: () => string;
  getToken: () => string | null;
  onUnauthorized: () => void;
  fetchImpl?: typeof fetch;
  timeoutMs?: number;
};

const LOGIN_PATH = '/api/m/giris';

export function createApiClient({
  getBaseUrl,
  getToken,
  onUnauthorized,
  fetchImpl = fetch,
  timeoutMs = 10_000,
}: Options): ApiClient {
  async function request<T>(method: 'GET' | 'POST', path: string, body?: unknown, upload = false): Promise<T> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), upload ? 65_000 : timeoutMs);
    const token = getToken();
    const headers: Record<string, string> = { Accept: 'application/json' };
    if (token) headers.Authorization = `Bearer ${token}`;
    if (body !== undefined && !upload) headers['Content-Type'] = 'application/json';
    let response: Response;
    try {
      response = await fetchImpl(getBaseUrl().replace(/\/+$/, '') + path, {
        method,
        headers,
        body: upload ? body as FormData : body === undefined ? undefined : JSON.stringify(body),
        signal: controller.signal,
      });
    } catch {
      throw new ApiError('ag', null, 'Sunucuya ulaşılamıyor.');
    } finally {
      clearTimeout(timer);
    }
    let payload: unknown = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    if (response.ok) return payload as T;
    const data = (payload ?? {}) as { hata?: string; kod?: string };
    const error = new ApiError(kindForStatus(response.status), response.status, data.hata ?? '', data.kod);
    if (error.kind === 'yetkisiz' && path !== LOGIN_PATH) onUnauthorized();
    throw error;
  }

  return {
    get: (path) => request('GET', path),
    post: (path, body) => request('POST', path, body),
    upload: (path, body) => request('POST', path, body, true),
  };
}
