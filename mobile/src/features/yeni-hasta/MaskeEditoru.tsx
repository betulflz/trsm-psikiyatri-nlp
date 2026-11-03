import { useEffect, useRef, useState, type ComponentRef } from 'react';
import { Alert, Image, Modal, PanResponder, View, type LayoutRectangle } from 'react-native';
import { captureRef } from 'react-native-view-shot';
import { useTheme } from '@/theme/ThemeProvider';
import { Button, Text } from '@/ui';
import { normalizeRect, outsideRects, toCropFraction, type CropFraction, type Rect } from './maske';
import { toFileUri } from './ocr';

type Props = { uri: string; onDone: (maskedUri: string, crop: CropFraction | null) => void; onCancel: () => void };
type Step = 'kirp' | 'karart';

/**
 * 1. Yazılı alan seçilir: dışı siyaha boyanır, sunucu yalnızca bu alanı okur (daha az piksel, daha kısa süre).
 * 2. Kimlik alanları karartılır. Sunucuya yalnızca bu işlenmiş kopya gider.
 */
export function MaskeEditoru({ uri, onDone, onCancel }: Props) {
  const { colors } = useTheme();
  const shot = useRef<ComponentRef<typeof View>>(null);
  const [ratio, setRatio] = useState(3 / 4);
  const [box, setBox] = useState<LayoutRectangle | null>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });
  const [step, setStep] = useState<Step>('kirp');
  const stepRef = useRef<Step>('kirp');
  const [crop, setCrop] = useState<Rect | null>(null);
  const [rects, setRects] = useState<Rect[]>([]);
  const [drawing, setDrawing] = useState<Rect | null>(null);
  const [saving, setSaving] = useState(false);
  const start = useRef({ x: 0, y: 0 });

  useEffect(() => {
    Image.getSize(uri, (w, h) => setRatio(w / h), () => setRatio(3 / 4));
  }, [uri]);

  function goTo(next: Step) {
    stepRef.current = next;
    setStep(next);
  }

  const pan = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderGrant: (e) => {
        start.current = { x: e.nativeEvent.locationX, y: e.nativeEvent.locationY };
        setDrawing({ x: start.current.x, y: start.current.y, w: 0, h: 0 });
      },
      onPanResponderMove: (_, g) => setDrawing(normalizeRect(start.current, { x: start.current.x + g.dx, y: start.current.y + g.dy })),
      onPanResponderRelease: (_, g) => {
        const rect = normalizeRect(start.current, { x: start.current.x + g.dx, y: start.current.y + g.dy });
        setDrawing(null);
        if (rect.w <= 8 || rect.h <= 8) return;
        if (stepRef.current === 'kirp') setCrop(rect);
        else setRects((old) => [...old, rect]);
      },
    }),
  ).current;

  async function finish() {
    if (rects.length === 0) {
      const ok = await new Promise<boolean>((resolve) =>
        Alert.alert('Hiç alan karartılmadı', 'Seçtiğiniz alanda ad, TC, adres gibi kimlik bilgisi olmadığından emin misiniz?', [
          { text: 'Geri dön', style: 'cancel', onPress: () => resolve(false) },
          { text: 'Eminim, gönder', onPress: () => resolve(true) },
        ]),
      );
      if (!ok) return;
    }
    setSaving(true);
    try {
      const masked = toFileUri(await captureRef(shot, { format: 'jpg', quality: 0.9, result: 'tmpfile' }));
      onDone(masked, crop ? toCropFraction(crop, size) : null);
    } catch {
      Alert.alert('Kaydedilemedi', 'Karartılmış fotoğraf oluşturulamadı. Tekrar deneyin.');
    } finally {
      setSaving(false);
    }
  }

  const liveCrop = step === 'kirp' && drawing ? drawing : crop;
  const masks = step === 'karart' && drawing ? [...rects, drawing] : rects;
  return (
    <Modal visible animationType="slide" onRequestClose={onCancel}>
      <View style={{ flex: 1, backgroundColor: colors.bg, padding: 16, paddingTop: 56, gap: 12 }}>
        <Text variant="title">{step === 'kirp' ? '1/2 · Yazılı alanı seçin' : '2/2 · Kimlik bilgilerini karartın'}</Text>
        <Text variant="bodySmall" color="inkMuted">
          {step === 'kirp'
            ? 'Okunacak yazının bulunduğu bölgeyi parmağınızla kutu içine alın. Dışı gönderilmez; alan küçüldükçe okuma hızlanır.'
            : 'Ad, soyad, TC, adres, telefon ve dosya numarasının üzerine kutu çizin. Sunucuya yalnızca bu hali gider.'}
        </Text>
        <View style={{ flex: 1, justifyContent: 'center' }} onLayout={(e) => setBox(e.nativeEvent.layout)}>
          {box && (
            <View
              ref={shot}
              collapsable={false}
              {...pan.panHandlers}
              onLayout={(e) => setSize({ width: e.nativeEvent.layout.width, height: e.nativeEvent.layout.height })}
              style={{ width: Math.min(box.width, box.height * ratio), aspectRatio: ratio, alignSelf: 'center' }}
            >
              <Image source={{ uri }} style={{ width: '100%', height: '100%' }} />
              {liveCrop &&
                outsideRects(liveCrop, size).map((r, i) => (
                  <View key={`dis${i}`} pointerEvents="none" style={{ position: 'absolute', left: r.x, top: r.y, width: r.w, height: r.h, backgroundColor: '#000' }} />
                ))}
              {masks.map((r, i) => (
                <View key={i} pointerEvents="none" style={{ position: 'absolute', left: r.x, top: r.y, width: r.w, height: r.h, backgroundColor: '#000' }} />
              ))}
            </View>
          )}
        </View>
        {step === 'kirp' ? (
          <>
            <View style={{ flexDirection: 'row', gap: 10 }}>
              <View style={{ flex: 1 }}>
                <Button title="Tüm sayfa" variant="ghost" onPress={() => { setCrop(null); goTo('karart'); }} />
              </View>
              <View style={{ flex: 1 }}>
                <Button title="Vazgeç" variant="ghost" onPress={onCancel} />
              </View>
            </View>
            <Button title="Bu alanı kullan" disabled={!crop} onPress={() => goTo('karart')} />
          </>
        ) : (
          <>
            <View style={{ flexDirection: 'row', gap: 10 }}>
              <View style={{ flex: 1 }}>
                <Button
                  title={rects.length ? 'Geri al' : 'Alanı değiştir'}
                  variant="ghost"
                  disabled={saving}
                  onPress={() => (rects.length ? setRects((old) => old.slice(0, -1)) : goTo('kirp'))}
                />
              </View>
              <View style={{ flex: 1 }}>
                <Button title="Vazgeç" variant="ghost" disabled={saving} onPress={onCancel} />
              </View>
            </View>
            <Button title={`Tamam, gönder${rects.length ? ` (${rects.length} alan)` : ''}`} loading={saving} onPress={finish} />
          </>
        )}
      </View>
    </Modal>
  );
}
