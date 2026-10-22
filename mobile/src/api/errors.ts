export type ApiErrorKind = 'yetkisiz' | 'yasak' | 'bulunamadi' | 'istek' | 'sunucu' | 'ag';

export class ApiError extends Error {
  constructor(
    public kind: ApiErrorKind,
    public status: number | null,
    message: string,
    public kod?: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export function kindForStatus(status: number): ApiErrorKind {
  if (status === 401) return 'yetkisiz';
  if (status === 403) return 'yasak';
  if (status === 404) return 'bulunamadi';
  if (status >= 400 && status < 500) return 'istek';
  return 'sunucu';
}

const TITLES: Record<ApiErrorKind, string> = {
  ag: 'Sunucuya ulaşılamıyor',
  yetkisiz: 'Oturum sona erdi',
  yasak: 'Erişim yok',
  bulunamadi: 'Bulunamadı',
  istek: 'İstek hatalı',
  sunucu: 'Sunucu hatası',
};

export function describeError(error: unknown): { title: string; message: string } {
  if (error instanceof ApiError) {
    const fallback =
      error.kind === 'ag'
        ? 'Telefon ve bilgisayarın aynı Wi-Fi ağında olduğundan ve sunucunun açık olduğundan emin olun.'
        : 'Lütfen tekrar deneyin.';
    return { title: TITLES[error.kind], message: error.kind === 'ag' ? fallback : error.message || fallback };
  }
  return { title: 'Beklenmeyen hata', message: 'Lütfen tekrar deneyin.' };
}
