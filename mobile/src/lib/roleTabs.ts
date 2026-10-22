export type Rol = 'admin' | 'doktor' | 'hemsire';
export type TabName = 'ozet' | 'dosyalar' | 'yeni' | 'sistem' | 'kullanicilar' | 'ayarlar';

export const ALL_TABS: TabName[] = ['ozet', 'dosyalar', 'yeni', 'sistem', 'kullanicilar', 'ayarlar'];

const TABS: Record<Rol, TabName[]> = {
  doktor: ['ozet', 'dosyalar', 'yeni', 'ayarlar'],
  hemsire: ['ozet', 'dosyalar', 'ayarlar'],
  admin: ['sistem', 'kullanicilar', 'ayarlar'],
};

export const TAB_LABELS: Record<TabName, string> = {
  ozet: 'Özet',
  dosyalar: 'Dosyalar',
  yeni: 'Yeni',
  sistem: 'Sistem',
  kullanicilar: 'Kullanıcılar',
  ayarlar: 'Ayarlar',
};

export function tabsForRole(rol: Rol): TabName[] {
  return TABS[rol];
}

export function homeTab(rol: Rol): TabName {
  return TABS[rol][0];
}

export function canViewPatients(rol: Rol): boolean {
  return rol === 'doktor' || rol === 'hemsire';
}
