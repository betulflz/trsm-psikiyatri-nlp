import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';

// Uygulamanın eski adı "Kartela" iken kullanılan anahtarlar; ilk açılışta veri kaybolmadan yeni adlara taşınır.
const OLD = 'kartela.';
const NEW = 'psikord.';
const ASYNC_SUFFIXES = ['tema', 'sunucu', 'taslaklar'];
const SECURE_SUFFIXES = ['oturum', 'oturum.sunucu'];

async function moveAsync(suffix: string): Promise<void> {
  const old = await AsyncStorage.getItem(OLD + suffix);
  if (old === null) return;
  if ((await AsyncStorage.getItem(NEW + suffix)) === null) await AsyncStorage.setItem(NEW + suffix, old);
  await AsyncStorage.removeItem(OLD + suffix);
}

async function moveSecure(suffix: string): Promise<void> {
  const old = await SecureStore.getItemAsync(OLD + suffix);
  if (old === null) return;
  if ((await SecureStore.getItemAsync(NEW + suffix)) === null) await SecureStore.setItemAsync(NEW + suffix, old);
  await SecureStore.deleteItemAsync(OLD + suffix);
}

async function migrate(): Promise<void> {
  for (const suffix of ASYNC_SUFFIXES) await moveAsync(suffix);
  for (const suffix of SECURE_SUFFIXES) await moveSecure(suffix);
  // Taslakların T.C. Kimlik No'ları taslak kimliğine göre ayrı anahtarlarda durur.
  const raw = await AsyncStorage.getItem(NEW + 'taslaklar');
  const drafts: { id?: unknown }[] = raw ? JSON.parse(raw) : [];
  for (const d of drafts) if (typeof d.id === 'string') await moveSecure(`tc.${d.id}`);
}

let pending: Promise<void> | null = null;

/** Uygulama ömründe bir kez çalışır; hata olursa uygulamayı durdurmaz. */
export function migrateLegacyKeys(): Promise<void> {
  return (pending ??= migrate().catch(() => undefined));
}

/** Yalnızca testler için: taşımanın yeniden çalışmasına izin verir. */
export function resetLegacyMigrationForTests(): void {
  pending = null;
}
