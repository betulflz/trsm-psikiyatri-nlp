import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';
import type { ThemePreference } from '@/theme/tokens';
import { migrateLegacyKeys } from './legacyMigration';

const KEYS = {
  theme: 'psikord.tema',
  serverUrl: 'psikord.sunucu',
  drafts: 'psikord.taslaklar',
} as const;

export type DraftPatient = {
  id: string;
  sahipId: number; // taslağı oluşturan kullanıcı; başkasına gösterilmez
  adSoyad: string;
  cinsiyet: 'Kadın' | 'Erkek' | null;
  dogumTarihi: string | null; // YYYY-MM-DD
  tcKimlik: string | null;
  sayfalar: string[]; // uygulama dizinindeki dosya URI'leri, sıralı
  olusturma: string; // ISO
};

// T.C. Kimlik No cihazın güvenli deposunda (Keychain/Keystore) tutulur; taslak JSON'una yazılmaz.
const tcKey = (draftId: string) => `psikord.tc.${draftId}`;

async function readJson<T>(key: string, fallback: T): Promise<T> {
  await migrateLegacyKeys();
  try {
    const raw = await AsyncStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

export const prefs = {
  async getThemePreference(): Promise<ThemePreference> {
    await migrateLegacyKeys();
    const value = await AsyncStorage.getItem(KEYS.theme);
    return value === 'acik' || value === 'koyu' ? value : 'sistem';
  },
  setThemePreference: (value: ThemePreference) => AsyncStorage.setItem(KEYS.theme, value),
  async getServerUrl() {
    await migrateLegacyKeys();
    return AsyncStorage.getItem(KEYS.serverUrl);
  },
  setServerUrl: (value: string) => AsyncStorage.setItem(KEYS.serverUrl, value),
  async getDrafts(): Promise<DraftPatient[]> {
    const stored = await readJson<DraftPatient[]>(KEYS.drafts, []);
    return Promise.all(
      stored.map(async (draft) => ({ ...draft, tcKimlik: await SecureStore.getItemAsync(tcKey(draft.id)) })),
    );
  },
  /** Cihaz birden çok kullanıcıyla paylaşılabilir; her kullanıcı yalnızca kendi taslaklarını görür. */
  async getDraftsFor(ownerId: number): Promise<DraftPatient[]> {
    return (await this.getDrafts()).filter((d) => d.sahipId === ownerId);
  },
  /** Taslağı yalnızca sahibi silebilir; silindiyse true döner. */
  async removeDraft(draftId: string, ownerId: number): Promise<boolean> {
    const all = await this.getDrafts();
    if (!all.some((d) => d.id === draftId && d.sahipId === ownerId)) return false;
    await this.setDrafts(all.filter((d) => d.id !== draftId));
    return true;
  },
  async setDrafts(drafts: DraftPatient[]): Promise<void> {
    const previous = await readJson<DraftPatient[]>(KEYS.drafts, []);
    const keep = new Set(drafts.map((d) => d.id));
    await Promise.all(previous.filter((d) => !keep.has(d.id)).map((d) => SecureStore.deleteItemAsync(tcKey(d.id))));
    await Promise.all(
      drafts.map((d) =>
        d.tcKimlik ? SecureStore.setItemAsync(tcKey(d.id), d.tcKimlik) : SecureStore.deleteItemAsync(tcKey(d.id)),
      ),
    );
    await AsyncStorage.setItem(KEYS.drafts, JSON.stringify(drafts.map((d) => ({ ...d, tcKimlik: null }))));
  },
};
