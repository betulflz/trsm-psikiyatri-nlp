export type Rect = { x: number; y: number; w: number; h: number };
type Point = { x: number; y: number };

/** Sürükleme yönü ne olursa olsun sol üst köşeden başlayan kutu döner. */
export function normalizeRect(a: Point, b: Point): Rect {
  return { x: Math.min(a.x, b.x), y: Math.min(a.y, b.y), w: Math.abs(b.x - a.x), h: Math.abs(b.y - a.y) };
}

/** Sunucuya gidecek kayıt için yaş: ziyaret günündeki tam yıl. */
export function ageOn(birthIso: string, today: Date): number {
  const [y, m, d] = birthIso.split('-').map(Number);
  let age = today.getFullYear() - y;
  if (today.getMonth() + 1 < m || (today.getMonth() + 1 === m && today.getDate() < d)) age -= 1;
  return age;
}

const LABELS: Record<string, string> = {
  tc: 'TC no', ad: 'ad', yakin: 'yakın adı', adres: 'adres', telefon: 'telefon',
  eposta: 'e-posta', dogum: 'doğum bilgisi', dosya_no: 'dosya no',
};

export function describeRemoved(removed: Record<string, number> | undefined): string | null {
  const parts = Object.entries(removed ?? {}).filter(([, n]) => n > 0).map(([k, n]) => `${n} ${LABELS[k] ?? k}`);
  return parts.length ? `Otomatik silinenler: ${parts.join(', ')}` : null;
}
