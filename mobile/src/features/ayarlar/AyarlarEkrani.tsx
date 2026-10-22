import { useState } from 'react';
import { View } from 'react-native';
import { useServerUrl } from '@/api/ServerUrlProvider';
import { useAuth } from '@/auth/AuthProvider';
import { initials } from '@/lib/format';
import { sameServer } from '@/lib/serverOrigin';
import { useTheme } from '@/theme/ThemeProvider';
import type { ThemePreference } from '@/theme/tokens';
import { Button, Card, Chip, FormField, Screen, SegmentedControl, Text } from '@/ui';

const ROL_ADI = { doktor: 'Doktor', hemsire: 'Hemşire', admin: 'Admin' } as const;

export function AyarlarEkrani() {
  const { colors, preference, setPreference } = useTheme();
  const { user, logout } = useAuth();
  const { url, setUrl } = useServerUrl();
  const [draftUrl, setDraftUrl] = useState(url);
  const [testResult, setTestResult] = useState<'ok' | 'hata' | null>(null);
  const [testing, setTesting] = useState(false);
  const changesServer = !sameServer(draftUrl, url);

  async function testConnection() {
    setTesting(true);
    setTestResult(null);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 5000);
    try {
      const response = await fetch(`${draftUrl.trim().replace(/\/+$/, '')}/api/m/saglik`, { signal: controller.signal });
      setTestResult(response.ok ? 'ok' : 'hata');
      if (response.ok) await setUrl(draftUrl);
    } catch {
      setTestResult('hata');
    } finally {
      clearTimeout(timer);
      setTesting(false);
    }
  }

  return (
    <Screen>
      <Text variant="title">Ayarlar</Text>

      <Card style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
        <View style={{ width: 48, height: 48, borderRadius: 15, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center' }}>
          <Text variant="heading" weight={800} color="onAccent">
            {initials(user?.ad_soyad ?? '')}
          </Text>
        </View>
        <View style={{ flex: 1 }}>
          <Text variant="heading">{user?.ad_soyad}</Text>
          <Text variant="bodySmall" color="inkMuted">
            {user ? ROL_ADI[user.rol] : ''} ·{' '}
            <Text variant="mono" color="inkMuted">
              {user?.kullanici_adi}
            </Text>
          </Text>
        </View>
      </Card>

      <Card style={{ gap: 10 }}>
        <Text variant="label" color="inkMuted">
          Tema
        </Text>
        <SegmentedControl<ThemePreference>
          value={preference}
          onChange={setPreference}
          options={[
            { value: 'sistem', label: 'Sistem' },
            { value: 'acik', label: 'Açık' },
            { value: 'koyu', label: 'Koyu' },
          ]}
        />
      </Card>

      <Card style={{ flexDirection: 'row', alignItems: 'center', gap: 10, opacity: 0.7 }}>
        <View style={{ flex: 1, gap: 2 }}>
          <Text variant="body" weight={700}>
            Google hesabı
          </Text>
          <Text variant="label" weight={500} color="inkMuted">
            Farklı e-postalı bir Google hesabını bu hesaba bağlayın.
          </Text>
        </View>
        <Chip label="Yakında" tone="primary" />
      </Card>

      <Card style={{ gap: 10 }}>
        <FormField
          label="Sunucu adresi"
          value={draftUrl}
          onChangeText={(v) => {
            setDraftUrl(v);
            setTestResult(null);
          }}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="url"
          mono
        />
        {changesServer && (
          <Text variant="label" color="inkMuted">
            Adres değişirse güvenliğiniz için oturum kapanır ve yeniden giriş yapmanız gerekir.
          </Text>
        )}
        {testResult && (
          <Text variant="label" color={testResult === 'ok' ? 'primary' : 'danger'}>
            {testResult === 'ok' ? 'Bağlantı başarılı, adres kaydedildi.' : 'Sunucuya ulaşılamadı.'}
          </Text>
        )}
        <Button title="Bağlantıyı sına" variant="deep" onPress={testConnection} loading={testing} />
      </Card>

      <Button title="Çıkış yap" variant="ghost" onPress={logout} />
    </Screen>
  );
}
