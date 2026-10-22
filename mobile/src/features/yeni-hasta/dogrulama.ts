import { isValidTcKimlik } from '@/lib/tcKimlik';

export type KimlikForm = {
  adSoyad: string;
  cinsiyet: 'Kadın' | 'Erkek' | null;
  dogumTarihi: string | null; // YYYY-MM-DD
  tcKimlik: string;
};

export function validateKimlik(form: KimlikForm, today: Date): Partial<Record<keyof KimlikForm, string>> {
  const errors: Partial<Record<keyof KimlikForm, string>> = {};
  const name = form.adSoyad.trim();
  if (!name) errors.adSoyad = 'Ad soyad gerekli.';
  else if (name.split(/\s+/).length < 2) errors.adSoyad = 'Ad ve soyadı birlikte girin.';
  if (form.tcKimlik && !isValidTcKimlik(form.tcKimlik)) errors.tcKimlik = 'Geçerli bir T.C. Kimlik No girin.';
  if (form.dogumTarihi && form.dogumTarihi > today.toISOString().slice(0, 10)) {
    errors.dogumTarihi = 'Doğum tarihi gelecekte olamaz.';
  }
  return errors;
}
