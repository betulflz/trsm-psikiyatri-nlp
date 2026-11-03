import { File } from 'expo-file-system';
import type { ApiClient } from '@/api/client';
import { ApiError } from '@/api/errors';
import type { CropFraction } from './maske';

export type ReportOcr = { metin: string; motor: string; temizlenen?: Record<string, number> };
export type PageOcr = { status: 'loading' | 'done' | 'error'; result?: ReportOcr; error?: string; progress?: string };
type OcrJob = { is_id: string; durum: 'sirada' | 'okunuyor' | 'bitti' | 'hata'; motor: string; sira?: number; gecen_sn?: number; metin?: string; hata?: string; temizlenen?: Record<string, number> };

const POLL_MS = 5_000;
const MAX_WAIT_MS = 30 * 60_000;

/** view-shot bazı sürümlerde yolu "file://" öneki olmadan döner; expo-file-system önek ister. */
export function toFileUri(uri: string): string {
  return uri.startsWith('/') ? `file://${uri}` : uri;
}

export function createReportUpload(uri: string, crop?: CropFraction | null): FormData {
  const body = new FormData();
  // Expo fetch URI nesnesi değil, bytes() sağlayan bir File bekler.
  body.append('foto', new File(toFileUri(uri)));
  if (crop) body.append('kirp', JSON.stringify(crop));
  return body;
}

export function describeJob(job: OcrJob): string {
  if (job.durum === 'sirada') return job.sira ? `Sırada: önünde ${job.sira} sayfa var…` : 'Sırada, birazdan okunacak…';
  const minutes = Math.floor((job.gecen_sn ?? 0) / 60);
  return `Qwen okuyor… ${minutes} dk ${(job.gecen_sn ?? 0) % 60} sn (bir sayfa birkaç dakika sürebilir)`;
}

/** Uzun beklemede tek bir ağ kesintisi okumayı düşürmesin diye birkaç kez dener. */
async function pollOnce(client: ApiClient, job: OcrJob, wait: (ms: number) => Promise<void>): Promise<OcrJob> {
  for (let attempt = 1; ; attempt++) {
    try {
      return await client.get<OcrJob>(`/api/m/rapor/ocr/${job.is_id}`);
    } catch (error) {
      if (attempt >= 3 || (error instanceof ApiError && error.kind !== 'ag' && error.kind !== 'sunucu')) throw error;
      await wait(POLL_MS);
    }
  }
}

/** Fotoğrafı sunucudaki okuma kuyruğuna gönderir ve sonuç gelene kadar durumu sorar. */
export async function readReport(
  client: ApiClient,
  uri: string,
  onProgress: (text: string) => void,
  wait = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms)),
  crop?: CropFraction | null,
): Promise<ReportOcr> {
  let job = await client.upload<OcrJob>('/api/m/rapor/ocr', createReportUpload(uri, crop));
  const started = Date.now();
  while (job.durum === 'sirada' || job.durum === 'okunuyor') {
    onProgress(describeJob(job));
    if (Date.now() - started > MAX_WAIT_MS) throw new Error('Okuma 30 dakikayı aştı. Yeniden okumayı deneyin.');
    await wait(POLL_MS);
    job = await pollOnce(client, job, wait);
  }
  if (job.durum === 'hata') throw new Error(job.hata || 'Rapor okunamadı.');
  return { metin: job.metin ?? '', motor: job.motor, temizlenen: job.temizlenen ?? {} };
}
