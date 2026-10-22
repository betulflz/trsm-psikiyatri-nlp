import { Directory, File, Paths } from 'expo-file-system';
import { prefs, type DraftPatient } from '@/storage/prefs';
import type { KimlikForm } from './dogrulama';

export function movePage(pages: string[], index: number, delta: -1 | 1): string[] {
  const target = index + delta;
  if (target < 0 || target >= pages.length) return pages;
  const next = [...pages];
  [next[index], next[target]] = [next[target], next[index]];
  return next;
}

/** Görselleri uygulama belgeler dizinine kopyalar (önbellek temizlense de kalsın) ve taslağı kaydeder. */
export async function saveDraft(form: KimlikForm, pageUris: string[], ownerId: number, ocr?: DraftPatient['ocr']): Promise<DraftPatient> {
  const id = `taslak-${Date.now()}`;
  const dir = new Directory(Paths.document, 'taslaklar', id);
  dir.create({ intermediates: true });
  const sayfalar = pageUris.map((uri, i) => {
    const dest = new File(dir, `sayfa-${i + 1}.jpg`);
    new File(uri).copy(dest);
    return dest.uri;
  });
  const draft: DraftPatient = {
    id,
    sahipId: ownerId,
    adSoyad: form.adSoyad.trim(),
    cinsiyet: form.cinsiyet,
    dogumTarihi: form.dogumTarihi,
    tcKimlik: form.tcKimlik || null,
    sayfalar,
    ocr,
    olusturma: new Date().toISOString(),
  };
  await prefs.setDrafts([draft, ...(await prefs.getDrafts())]); // tümünü okuyup yazar; başka kullanıcıların taslakları korunur
  return draft;
}

export async function deleteDraft(id: string, ownerId: number): Promise<void> {
  if (!(await prefs.removeDraft(id, ownerId))) return; // başkasının taslağına dokunulmaz
  const dir = new Directory(Paths.document, 'taslaklar', id);
  if (dir.exists) dir.delete();
}
