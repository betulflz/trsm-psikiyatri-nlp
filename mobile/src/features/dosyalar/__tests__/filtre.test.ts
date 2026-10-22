import type { HastaOzeti } from '@/api/types';
import { filterPatients } from '../filtre';

const base = { cinsiyet: null, yas: null, yogunluk: [], okunmamis: false };
const list: HastaOzeti[] = [
  { ...base, id: 1, ad: 'Ayşe Kaya', not_sayisi: 4, son_ziyaret: '2023-06-10' },
  { ...base, id: 2, ad: 'Boş Dosya', not_sayisi: 0, son_ziyaret: null },
  { ...base, id: 3, ad: 'İsmail Işık', not_sayisi: 1, son_ziyaret: '2025-01-15', okunmamis: true },
];

it('tümü: sunucu sırası korunur, arama Türkçe duyarlı', () => {
  expect(filterPatients(list, '', 'tumu').map((p) => p.id)).toEqual([1, 2, 3]);
  expect(filterPatients(list, 'ayse', 'tumu').map((p) => p.id)).toEqual([1]);
  expect(filterPatients(list, 'IŞI', 'tumu').map((p) => p.id)).toEqual([3]);
});

it('son ziyaret: tarihliler yeniden eskiye, tarihsizler en sonda', () => {
  expect(filterPatients(list, '', 'son').map((p) => p.id)).toEqual([3, 1, 2]);
});

it('okunmadı: yalnızca okunmamış dosyalar', () => {
  expect(filterPatients(list, '', 'okunmadi').map((p) => p.id)).toEqual([3]);
});
