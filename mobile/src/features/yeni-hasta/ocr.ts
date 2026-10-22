import { File } from 'expo-file-system';

export type ReportOcr = { metin: string; motor: string; dil: string };
export type PageOcr = { status: 'loading' | 'done' | 'error'; result?: ReportOcr; error?: string };

export function createReportUpload(uri: string): FormData {
  const body = new FormData();
  // Expo fetch URI nesnesi değil, bytes() sağlayan bir File bekler.
  body.append('foto', new File(uri));
  return body;
}
