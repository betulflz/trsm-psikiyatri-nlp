import { View } from 'react-native';
import { useKullanicilar } from '@/api/hooks';
import { initials } from '@/lib/format';
import { useTheme } from '@/theme/ThemeProvider';
import { Card, Chip, ErrorState, Screen, Skeleton, Text } from '@/ui';

const ROL_ADI = { doktor: 'Doktor', hemsire: 'Hemşire', admin: 'Admin' } as const;

export function KullanicilarEkrani() {
  const { colors } = useTheme();
  const query = useKullanicilar();
  return (
    <Screen refreshing={query.isRefetching} onRefresh={() => query.refetch()}>
      <Text variant="title">Kullanıcılar</Text>
      <Text variant="bodySmall" color="inkMuted">
        Aşama 1'de hesaplar sunucudaki seed scriptiyle oluşturulur; buradan düzenlenmez.
      </Text>
      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : !query.data ? (
        <Skeleton height={200} radius={18} />
      ) : (
        query.data.map((user) => (
          <Card key={user.id} style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
            <View style={{ width: 42, height: 42, borderRadius: 13, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center' }}>
              <Text variant="bodySmall" weight={800} color="primary">
                {initials(user.ad_soyad)}
              </Text>
            </View>
            <View style={{ flex: 1 }}>
              <Text variant="body" weight={700}>
                {user.ad_soyad}
              </Text>
              <Text variant="mono" color="inkMuted">
                {user.kullanici_adi}
              </Text>
            </View>
            <View style={{ alignItems: 'flex-end', gap: 4 }}>
              <Chip label={ROL_ADI[user.rol]} tone="primary" />
              <Text variant="label" weight={500} color="inkMuted">
                {user.google_bagli ? 'Google bağlı' : 'Google yok'}
              </Text>
            </View>
          </Card>
        ))
      )}
    </Screen>
  );
}
