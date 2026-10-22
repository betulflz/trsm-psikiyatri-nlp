import { View } from 'react-native';
import { useSistem } from '@/api/hooks';
import { formatNumber } from '@/lib/format';
import { Card, Chip, ErrorState, HeroCard, Screen, Skeleton, Text } from '@/ui';

const TABLO_ADI: Record<string, string> = {
  hasta: 'Hasta dosyası',
  ziyaret: 'Ziyaret notu',
  ilac_kullanimi: 'İlaç kaydı',
  semptom_kaydi: 'Semptom kaydı',
  ilac_sozluk: 'Sözlükteki ilaç',
  kullanici: 'Kullanıcı',
};

export function SistemEkrani() {
  const query = useSistem();
  const data = query.data;
  return (
    <Screen refreshing={query.isRefetching} onRefresh={() => query.refetch()}>
      <Text variant="title">Sistem</Text>
      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : !data ? (
        <Skeleton height={260} radius={22} />
      ) : (
        <>
          <HeroCard>
            <Text variant="label" color="onDeep" style={{ opacity: 0.7 }}>
              Veritabanı
            </Text>
            <Text variant="display" color="onDeep">
              {`${data.db_boyutu_mb} MB`}
            </Text>
            <View style={{ flexDirection: 'row', gap: 6, marginTop: 8 }}>
              <Chip label={data.semptom_indeksi ? 'Semptom indeksi hazır' : 'Semptom indeksi yok'} tone={data.semptom_indeksi ? 'accent' : 'danger'} />
              <Chip label={data.ollama ? 'Ollama açık' : 'Ollama kapalı'} tone={data.ollama ? 'accent' : 'neutral'} />
            </View>
          </HeroCard>
          <Card style={{ gap: 10 }}>
            {Object.entries(data.tablolar).map(([table, count]) => (
              <View key={table} style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                <Text variant="bodySmall">{TABLO_ADI[table] ?? table}</Text>
                <Text variant="mono" color="inkMuted">
                  {formatNumber(count)}
                </Text>
              </View>
            ))}
          </Card>
        </>
      )}
    </Screen>
  );
}
