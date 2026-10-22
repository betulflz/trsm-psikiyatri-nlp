import type { Rol } from '@/lib/roleTabs';

/** scripts/seed_mobile_users.py varsayılanlarıyla aynı; yalnızca __DEV__'de gösterilir. */
export const DEMO_ACCOUNTS: { rol: Rol; kullaniciAdi: string; sifre: string; etiket: string }[] = [
  { rol: 'doktor', kullaniciAdi: 'doktor', sifre: 'psikord-doktor', etiket: 'Doktor' },
  { rol: 'hemsire', kullaniciAdi: 'hemsire', sifre: 'psikord-hemsire', etiket: 'Hemşire' },
  { rol: 'admin', kullaniciAdi: 'admin', sifre: 'psikord-admin', etiket: 'Admin' },
];
