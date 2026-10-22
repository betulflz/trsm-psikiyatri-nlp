import type { HastaOzeti } from '@/api/types';
import { matchesQuery } from '@/lib/turkishSearch';

export type Filtre = 'tumu' | 'son' | 'okunmadi';

export function filterPatients(list: HastaOzeti[], query: string, filtre: Filtre): HastaOzeti[] {
  let result = list.filter((p) => matchesQuery(p.ad, query));
  if (filtre === 'okunmadi') result = result.filter((p) => p.okunmamis);
  if (filtre === 'son') {
    result = [...result].sort((a, b) => {
      if (a.son_ziyaret === b.son_ziyaret) return a.id - b.id;
      if (a.son_ziyaret === null) return 1;
      if (b.son_ziyaret === null) return -1;
      return a.son_ziyaret < b.son_ziyaret ? 1 : -1;
    });
  }
  return result;
}
