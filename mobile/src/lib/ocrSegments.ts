export type Highlight = { bas: number; son: number; tur: 'ilac' | 'belirti' };
export type Segment = { text: string; tur: 'ilac' | 'belirti' | null };

/** Sunucunun UTF-16 aralıklarını (JS string indeksleri) metin parçalarına çevirir. */
export function splitHighlights(text: string, highlights: Highlight[]): Segment[] {
  const valid = [...highlights]
    .filter((h) => h.bas >= 0 && h.son <= text.length && h.son > h.bas)
    .sort((a, b) => a.bas - b.bas);
  const segments: Segment[] = [];
  let cursor = 0;
  for (const h of valid) {
    if (h.bas < cursor) continue; // çakışan aralık
    if (h.bas > cursor) segments.push({ text: text.slice(cursor, h.bas), tur: null });
    segments.push({ text: text.slice(h.bas, h.son), tur: h.tur });
    cursor = h.son;
  }
  if (cursor < text.length) segments.push({ text: text.slice(cursor), tur: null });
  return segments;
}
