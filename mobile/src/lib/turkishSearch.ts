const ASCII_MAP: Record<string, string> = { ç: 'c', ğ: 'g', ı: 'i', ö: 'o', ş: 's', ü: 'u' };

/** Türkçe kurallarıyla küçük harf (İ→i, I→ı) ve NFC. */
export function foldTr(value: string): string {
  return value.normalize('NFC').replace(/İ/g, 'i').replace(/I/g, 'ı').toLowerCase();
}

function asciiFold(value: string): string {
  return value.replace(/[çğıöşü]/g, (ch) => ASCII_MAP[ch]);
}

export function matchesQuery(text: string, query: string): boolean {
  const q = foldTr(query.trim());
  if (!q) return true;
  const t = foldTr(text);
  // Aksansız arama yalnızca sorgu aksansızsa devreye girer; "ISMA" gibi
  // Türkçe büyük I yazımı ı olarak yorumlanmaya devam eder.
  const queryHasTurkish = /[çğıöşü]/.test(q);
  return t.includes(q) || (!queryHasTurkish && asciiFold(t).includes(q));
}
