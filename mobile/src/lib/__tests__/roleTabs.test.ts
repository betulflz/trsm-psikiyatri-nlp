import { canViewPatients, homeTab, tabsForRole } from '../roleTabs';

it('rol → sekmeler (spec §3)', () => {
  expect(tabsForRole('doktor')).toEqual(['ozet', 'dosyalar', 'yeni', 'ayarlar']);
  expect(tabsForRole('hemsire')).toEqual(['ozet', 'dosyalar', 'ayarlar']);
  expect(tabsForRole('admin')).toEqual(['sistem', 'kullanicilar', 'ayarlar']);
});

it('ana sekme ve hasta erişimi', () => {
  expect(homeTab('doktor')).toBe('ozet');
  expect(homeTab('admin')).toBe('sistem');
  expect(canViewPatients('hemsire')).toBe(true);
  expect(canViewPatients('admin')).toBe(false);
});
