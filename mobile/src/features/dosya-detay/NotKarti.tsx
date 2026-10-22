import { useRecyclingState } from '@shopify/flash-list';
import { View } from 'react-native';
import type { Not } from '@/api/types';
import { Card, Chip, OcrText, PressableScale } from '@/ui';

export function NotKarti({ not }: { not: Not }) {
  // FlashList hücreleri geri dönüştürür; açık/kapalı durumu nota bağlı kalsın.
  const [acik, setAcik] = useRecyclingState(false, [not.id]);
  return (
    <PressableScale accessibilityLabel="Notu aç/kapat" onPress={() => setAcik((v) => !v)}>
      <Card style={{ gap: 10 }}>
        {not.metin ? (
          <OcrText key={acik ? 'acik' : 'kapali'} text={not.metin} highlights={not.vurgular} numberOfLines={acik ? undefined : 4} animate={acik} />
        ) : (
          <OcrText text="(Bu notta okunabilir metin yok)" highlights={[]} animate={false} />
        )}
        <View style={{ flexDirection: 'row', gap: 6, flexWrap: 'wrap' }}>
          {not.ilaclar.length > 0 && <Chip label={`${not.ilaclar.length} ilaç`} tone="highlight" />}
          {not.belirti_sayisi > 0 && <Chip label={`${not.belirti_sayisi} belirti`} tone="primary" />}
          {acik &&
            not.ilaclar.map((ilac) => (
              <Chip key={ilac.ad} label={[ilac.ad, ilac.doz, ilac.siklik].filter(Boolean).join(' · ')} tone="neutral" />
            ))}
        </View>
      </Card>
    </PressableScale>
  );
}
