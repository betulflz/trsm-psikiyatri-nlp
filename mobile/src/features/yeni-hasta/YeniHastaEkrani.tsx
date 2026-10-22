import { useFocusEffect } from 'expo-router';
import { Trash2 } from 'lucide-react-native';
import { useCallback, useRef, useState } from 'react';
import { Alert, Pressable, View } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { useAuth } from '@/auth/AuthProvider';
import { maskTcKimlik } from '@/lib/tcKimlik';
import { prefs, type DraftPatient } from '@/storage/prefs';
import { useTheme } from '@/theme/ThemeProvider';
import { Button, Card, Chip, Screen, Stamp, Text } from '@/ui';
import { validateKimlik, type KimlikForm } from './dogrulama';
import { KimlikAdimi } from './KimlikAdimi';
import { RaporAdimi } from './RaporAdimi';
import { deleteDraft, saveDraft } from './taslak';
import type { PageOcr, ReportOcr } from './ocr';
import { createReportUpload } from './ocr';

const EMPTY: KimlikForm = { adSoyad: '', cinsiyet: null, dogumTarihi: null, tcKimlik: '' };

export function YeniHastaEkrani() {
  const { colors } = useTheme();
  const { user, client } = useAuth();
  const ownerId = user?.id ?? 0;
  const [adim, setAdim] = useState<1 | 2 | 'bitti'>(1);
  const [form, setForm] = useState<KimlikForm>(EMPTY);
  const [errors, setErrors] = useState<Partial<Record<keyof KimlikForm, string>>>({});
  const [pages, setPages] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [drafts, setDrafts] = useState<DraftPatient[]>([]);
  const [ocr, setOcr] = useState<Record<string, PageOcr>>({});
  const [reading, setReading] = useState(false);
  const readingRef = useRef(false);

  async function readPages(uris: string[]) {
    if (readingRef.current) return;
    readingRef.current = true;
    setReading(true);
    try {
      for (const uri of uris) {
        setOcr((old) => ({ ...old, [uri]: { status: 'loading' } }));
        try {
          const body = createReportUpload(uri);
          const result = await client.upload<ReportOcr>('/api/m/rapor/ocr', body);
          setOcr((old) => ({ ...old, [uri]: { status: 'done', result } }));
        } catch (error) {
          setOcr((old) => ({ ...old, [uri]: { status: 'error', error: error instanceof Error ? error.message : 'Rapor okunamadı.' } }));
        }
      }
    } finally {
      readingRef.current = false;
      setReading(false);
    }
  }

  useFocusEffect(
    useCallback(() => {
      prefs.getDraftsFor(ownerId).then(setDrafts);
    }, [ownerId]),
  );

  function next() {
    const found = validateKimlik(form, new Date());
    setErrors(found);
    if (Object.keys(found).length === 0) setAdim(2);
  }

  async function save() {
    setSaving(true);
    try {
      await saveDraft(form, pages, ownerId, pages.map((uri) => ocr[uri]?.result ?? null));
      setDrafts(await prefs.getDraftsFor(ownerId));
      setAdim('bitti');
    } catch {
      Alert.alert('Kaydedilemedi', 'Taslak cihaza yazılamadı. Lütfen tekrar deneyin.');
    } finally {
      setSaving(false);
    }
  }

  function reset() {
    setForm(EMPTY);
    setPages([]);
    setOcr({});
    setErrors({});
    setAdim(1);
  }

  return (
    <Screen>
      <View style={{ gap: 4 }}>
        <Text variant="title">Yeni dosya</Text>
        <Text variant="bodySmall" color="inkMuted">
          {adim === 1 ? 'Adım 1/2 · Kimlik bilgileri' : adim === 2 ? 'Adım 2/2 · Rapor sayfaları' : 'Taslak kaydedildi'}
        </Text>
      </View>

      {adim !== 'bitti' && (
        <View style={{ flexDirection: 'row', gap: 6 }}>
          <View style={{ flex: 1, height: 4, borderRadius: 2, backgroundColor: colors.primary }} />
          <View style={{ flex: 1, height: 4, borderRadius: 2, backgroundColor: adim === 2 ? colors.primary : colors.line }} />
        </View>
      )}

      {adim === 1 && (
        <Animated.View entering={FadeInDown.duration(350)}>
          <KimlikAdimi form={form} errors={errors} onChange={(patch) => setForm((f) => ({ ...f, ...patch }))} onNext={next} />
        </Animated.View>
      )}
      {adim === 2 && (
        <Animated.View entering={FadeInDown.duration(350)}>
          <RaporAdimi pages={pages} onChange={setPages} onBack={() => setAdim(1)} onSave={save} saving={saving} ocr={ocr} reading={reading} onRead={readPages} />
        </Animated.View>
      )}
      {adim === 'bitti' && (
        <View style={{ gap: 18, paddingVertical: 20 }}>
          <Stamp title="TASLAK KAYDEDİLDİ" subtitle="RAPOR SAYFALARI VE OCR SONUÇLARI" />
          <Text variant="bodySmall" color="inkMuted" style={{ textAlign: 'center' }}>
            Fotoğraflar ve okunabilen metinler bu cihazda saklandı. Hasta kaydı henüz sunucuya eklenmedi.
          </Text>
          <Button title="Yeni dosya başlat" onPress={reset} />
        </View>
      )}

      {drafts.length > 0 && (
        <View style={{ gap: 8, marginTop: 10 }}>
          <Text variant="label" color="inkMuted">
            Cihazdaki taslaklar · {drafts.length}
          </Text>
          {drafts.map((draft) => (
            <Card key={draft.id} style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
              <View style={{ flex: 1, gap: 2 }}>
                <Text variant="body" weight={700}>
                  {draft.adSoyad}
                </Text>
                <Text variant="label" weight={500} color="inkMuted">
                  {[draft.cinsiyet, draft.tcKimlik ? maskTcKimlik(draft.tcKimlik) : null, `${draft.sayfalar.length} sayfa`]
                    .filter(Boolean)
                    .join(' · ')}
                </Text>
              </View>
              <Chip label="Taslak" tone="danger" />
              {draft.ocr?.some((item) => item?.metin) && (
                <Pressable accessibilityLabel="Okunan raporu göster" onPress={() => Alert.alert('Rapor metni', draft.ocr?.map((item, i) => `Sayfa ${i + 1}\n${item?.metin || 'Metin okunamadı.'}`).join('\n\n'))}>
                  <Text variant="label" color="primary">Metni gör</Text>
                </Pressable>
              )}
              <Pressable
                accessibilityLabel="Taslağı sil"
                hitSlop={8}
                onPress={async () => {
                  await deleteDraft(draft.id, ownerId);
                  setDrafts(await prefs.getDraftsFor(ownerId));
                }}
              >
                <Trash2 size={18} color={colors.inkMuted} />
              </Pressable>
            </Card>
          ))}
        </View>
      )}
    </Screen>
  );
}
