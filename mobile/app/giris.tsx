import { useState } from 'react';
import { KeyboardAvoidingView, Platform, View } from 'react-native';
import Animated, { FadeInDown, useAnimatedStyle, useSharedValue, withSequence, withTiming } from 'react-native-reanimated';
import { SafeAreaView } from 'react-native-safe-area-context';
import { describeError } from '@/api/errors';
import { useAuth } from '@/auth/AuthProvider';
import { useTheme } from '@/theme/ThemeProvider';
import { SunucuAdresi } from '@/features/baglanti/SunucuAdresi';
import { Button, FormField, Logo, PressableScale, Text } from '@/ui';
import { useServerUrl } from '@/api/ServerUrlProvider';

// Demo hesapları yalnızca geliştirme derlemesine girer; üretim paketinde bu require elenir.
const DEMO_ACCOUNTS: typeof import('@/auth/demoAccounts').DEMO_ACCOUNTS = __DEV__
  ? require('@/auth/demoAccounts').DEMO_ACCOUNTS
  : [];

export default function Giris() {
  const { colors } = useTheme();
  const { login } = useAuth();
  const { url } = useServerUrl();
  const [adresAcik, setAdresAcik] = useState(false);
  const [kullaniciAdi, setKullaniciAdi] = useState('');
  const [sifre, setSifre] = useState('');
  const [hata, setHata] = useState<string | null>(null);
  const [yukleniyor, setYukleniyor] = useState(false);
  const shake = useSharedValue(0);
  const shakeStyle = useAnimatedStyle(() => ({ transform: [{ translateX: shake.value }] }));

  async function submit(k = kullaniciAdi, s = sifre) {
    setHata(null);
    setYukleniyor(true);
    try {
      await login(k.trim(), s);
    } catch (error) {
      setHata(describeError(error).message);
      shake.value = withSequence(
        withTiming(-10, { duration: 50 }),
        withTiming(10, { duration: 50 }),
        withTiming(-6, { duration: 50 }),
        withTiming(0, { duration: 50 }),
      );
    } finally {
      setYukleniyor(false);
    }
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.deep }}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1, justifyContent: 'center', padding: 24 }}>
        <Animated.View entering={FadeInDown.duration(500)} style={{ gap: 10, marginBottom: 32 }}>
          <Logo size={60} />
          <Text variant="display" color="onDeep">
            psikord
          </Text>
          <Text variant="body" color="onDeep" style={{ opacity: 0.7 }}>
            TRSM hasta arşivi
          </Text>
        </Animated.View>

        <Animated.View
          entering={FadeInDown.delay(120).duration(500)}
          style={[{ backgroundColor: colors.surface, borderRadius: 22, padding: 18, gap: 14 }, shakeStyle]}
        >
          <FormField
            label="Kullanıcı adı"
            value={kullaniciAdi}
            onChangeText={setKullaniciAdi}
            autoCapitalize="none"
            autoCorrect={false}
            textContentType="username"
          />
          <FormField
            label="Şifre"
            value={sifre}
            onChangeText={setSifre}
            secureTextEntry
            textContentType="password"
            error={hata}
            onSubmitEditing={() => submit()}
          />
          <Button title="Giriş yap" onPress={() => submit()} loading={yukleniyor} disabled={!kullaniciAdi || !sifre} />
          <Button title="Google ile giriş (yakında)" variant="ghost" onPress={() => {}} disabled />
        </Animated.View>

        <Animated.View entering={FadeInDown.delay(180).duration(500)} style={{ marginTop: 16, gap: 10 }}>
          {adresAcik ? (
            <View style={{ backgroundColor: colors.surface, borderRadius: 22, padding: 18 }}>
              <SunucuAdresi onSaved={() => setAdresAcik(false)} />
            </View>
          ) : (
            <PressableScale accessibilityLabel="Sunucu adresini değiştir" onPress={() => setAdresAcik(true)} style={{ alignSelf: 'center', padding: 6 }}>
              <Text variant="label" color="onDeep" style={{ opacity: 0.7 }}>
                {`Sunucu: ${url}  ·  değiştir`}
              </Text>
            </PressableScale>
          )}
        </Animated.View>

        {__DEV__ && (
          <Animated.View entering={FadeInDown.delay(240).duration(500)} style={{ flexDirection: 'row', gap: 8, marginTop: 20, justifyContent: 'center' }}>
            {DEMO_ACCOUNTS.map((account) => (
              <PressableScale
                key={account.rol}
                accessibilityLabel={`${account.etiket} olarak gir`}
                onPress={() => {
                  setKullaniciAdi(account.kullaniciAdi);
                  setSifre(account.sifre);
                  submit(account.kullaniciAdi, account.sifre);
                }}
                style={{ backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: 10, paddingHorizontal: 12, paddingVertical: 7 }}
              >
                <Text variant="label" color="onDeep">
                  {account.etiket}
                </Text>
              </PressableScale>
            ))}
          </Animated.View>
        )}
        <View style={{ height: 24 }} />
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
