import * as SecureStore from 'expo-secure-store';
import { migrateLegacyKeys } from '@/storage/legacyMigration';

const KEY = 'psikord.oturum';
const SERVER_KEY = 'psikord.oturum.sunucu';

/** Token, kendisini veren sunucunun adresiyle birlikte saklanır; başka bir sunucuya gönderilmez. */
export const tokenStore = {
  async get(): Promise<{ token: string; server: string } | null> {
    await migrateLegacyKeys();
    const [token, server] = await Promise.all([SecureStore.getItemAsync(KEY), SecureStore.getItemAsync(SERVER_KEY)]);
    return token && server ? { token, server } : null;
  },
  async set(token: string, server: string): Promise<void> {
    await Promise.all([SecureStore.setItemAsync(KEY, token), SecureStore.setItemAsync(SERVER_KEY, server)]);
  },
  async clear(): Promise<void> {
    await Promise.all([SecureStore.deleteItemAsync(KEY), SecureStore.deleteItemAsync(SERVER_KEY)]);
  },
};
