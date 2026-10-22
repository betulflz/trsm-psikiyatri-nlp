import type { Rol } from '@/lib/roleTabs';
import type { Highlight } from '@/lib/ocrSegments';

export type Kullanici = { id: number; kullanici_adi: string; ad_soyad: string; rol: Rol; google_bagli: boolean };
export type GirisYaniti = { token: string; kullanici: Kullanici };

export type Ozet = {
  toplam_dosya: number;
  toplam_not: number;
  ilacli_not: number;
  yillik_not: { yil: number; sayi: number }[];
  cinsiyet: { erkek: number; kadin: number; bilinmiyor: number };
  en_sik_ilaclar: { ilac: string; sayi: number }[];
  okunmamis_rapor: number;
};

export type HastaOzeti = {
  id: number;
  ad: string;
  cinsiyet: string | null;
  yas: number | null;
  not_sayisi: number;
  son_ziyaret: string | null;
  yogunluk: number[];
  okunmamis: boolean;
};

export type HastaDetayi = {
  id: number;
  ad: string;
  cinsiyet: string | null;
  yas: number | null;
  dosya_no: string;
  tc_maskeli: string | null;
  not_sayisi: number;
  ilac_sayisi: number;
  ilk_kayit: string | null;
  son_kayit: string | null;
};

export type Not = {
  id: number;
  tarih: string | null;
  sayfa_no: number | null;
  metin: string;
  vurgular: Highlight[];
  ilaclar: { ad: string; doz: string | null; siklik: string | null }[];
  belirti_sayisi: number;
  gorsel_var: boolean;
};

export type NotSayfasi = { notlar: Not[]; sonraki: number | null };

export type SistemDurumu = {
  tablolar: Record<string, number>;
  db_boyutu_mb: number;
  semptom_indeksi: boolean;
  ollama: boolean;
};
