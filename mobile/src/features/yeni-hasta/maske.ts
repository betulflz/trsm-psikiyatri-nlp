export type Rect = { x: number; y: number; w: number; h: number };
type Point = { x: number; y: number };

/** Sürükleme yönü ne olursa olsun sol üst köşeden başlayan kutu döner. */
export function normalizeRect(a: Point, b: Point): Rect {
  return { x: Math.min(a.x, b.x), y: Math.min(a.y, b.y), w: Math.abs(b.x - a.x), h: Math.abs(b.y - a.y) };
}

export type CropFraction = { x: number; y: number; w: number; h: number }; // 0–1 oranları

/** Ekrandaki kutuyu fotoğrafa göre orana çevirir; sunucu bu oranla keser. */
export function toCropFraction(crop: Rect, size: { width: number; height: number }): CropFraction | null {
  if (!size.width || !size.height) return null;
  const clamp = (v: number) => Math.min(1, Math.max(0, v));
  const x = clamp(crop.x / size.width);
  const y = clamp(crop.y / size.height);
  return { x, y, w: clamp((crop.x + crop.w) / size.width) - x, h: clamp((crop.y + crop.h) / size.height) - y };
}

/** Seçilen alanın dışını kaplayan dört kutu (üst, alt, sol, sağ). */
export function outsideRects(crop: Rect, size: { width: number; height: number }): Rect[] {
  const { width: W, height: H } = size;
  const bottom = crop.y + crop.h;
  const right = crop.x + crop.w;
  return [
    { x: 0, y: 0, w: W, h: crop.y },
    { x: 0, y: bottom, w: W, h: Math.max(0, H - bottom) },
    { x: 0, y: crop.y, w: crop.x, h: crop.h },
    { x: right, y: crop.y, w: Math.max(0, W - right), h: crop.h },
  ].filter((r) => r.w > 0 && r.h > 0);
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
