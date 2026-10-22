import { useState } from 'react';
import { View } from 'react-native';
import { useServerUrl } from '@/api/ServerUrlProvider';
import { normalizeServerUrl } from '@/lib/serverOrigin';
import { Button, FormField } from '@/ui';

/** Sunucu adresini doğrular, sağlık ucunu sınar, başarılıysa kaydeder. */
export function SunucuAdresi({ onSaved }: { onSaved?: () => void }) {
  const { url, setUrl } = useServerUrl();
  const [draft, setDraft] = useState(url);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function save() {
    const normalized = normalizeServerUrl(draft);
    if (!normalized) {
      setError('Geçerli bir adres girin (örn. http://192.168.1.20:8765).');
      return;
    }
    setBusy(true);
    setError(null);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 5000);
    try {
      const response = await fetch(`${normalized}/api/m/saglik`, { signal: controller.signal });
      if (!response.ok) throw new Error('sağlık');
      await setUrl(normalized);
      onSaved?.();
    } catch {
      setError('Bu adreste Psikord sunucusuna ulaşılamadı.');
    } finally {
      clearTimeout(timer);
      setBusy(false);
    }
  }

  return (
    <View style={{ gap: 10 }}>
      <FormField
        label="Sunucu adresi"
        value={draft}
        onChangeText={(v) => {
          setDraft(v);
          setError(null);
        }}
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType="url"
        mono
        error={error}
      />
      <Button title="Sına ve kaydet" onPress={save} loading={busy} variant="deep" />
    </View>
  );
}
