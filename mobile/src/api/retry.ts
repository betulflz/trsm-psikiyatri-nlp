import { ApiError } from './errors';

/** Ağ hatası bir kez, sunucu hatası iki kez yeniden denenir; istemci/yetki hataları hiç. */
export function shouldRetryQuery(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError) {
    if (error.kind === 'ag') return failureCount < 1;
    if (error.kind !== 'sunucu') return false;
  }
  return failureCount < 2;
}
