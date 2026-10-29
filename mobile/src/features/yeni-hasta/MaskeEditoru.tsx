import { useEffect, useRef, useState } from 'react';
import { Alert, Image, Modal, PanResponder, View, type LayoutRectangle } from 'react-native';
import { captureRef } from 'react-native-view-shot';
import { useTheme } from '@/theme/ThemeProvider';
import { Button, Text } from '@/ui';
import { normalizeRect, type Rect } from './maske';

type Props = { uri: string; onDone: (maskedUri: string) => void; onCancel: () => void };

/** Fotoğrafın kimlik alanları parmakla karartılır; sunucuya yalnızca karartılmış kopya gider. */
export function MaskeEditoru({ uri, onDone, onCancel }: Props) {
  const { colors } = useTheme();
  const shot = useRef<View>(null);
  const [ratio, setRatio] = useState(3 / 4);
  const [box, setBox] = useState<LayoutRectangle | null>(null);
  const [rects, setRects] = useState<Rect[]>([]);
  const [drawing, setDrawing] = useState<Rect | null>(null);
  const [saving, setSaving] = useState(false);
  const start = useRef({ x: 0, y: 0 });

  useEffect(() => {
    Image.getSize(uri, (w, h) => setRatio(w / h), () => setRatio(3 / 4));
  }, [uri]);

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
        if (rect.w > 8 && rect.h > 8) setRects((old) => [...old, rect]);
      },
    }),
  ).current;

  async function finish() {
    if (rects.length === 0) {
      const ok = await new Promise<boolean>((resolve) =>
        Alert.alert('Hiç alan karartılmadı', 'Bu sayfada ad, TC, adres gibi kimlik bilgisi olmadığından emin misiniz?', [
          { text: 'Geri dön', style: 'cancel', onPress: () => resolve(false) },
          { text: 'Eminim, gönder', onPress: () => resolve(true) },
        ]),
      );
      if (!ok) return;
    }
    setSaving(true);
    try {
      onDone(await captureRef(shot, { format: 'jpg', quality: 0.9, result: 'tmpfile' }));
    } catch {
      Alert.alert('Kaydedilemedi', 'Karartılmış fotoğraf oluşturulamadı. Tekrar deneyin.');
    } finally {
      setSaving(false);
    }
  }

  const all = drawing ? [...rects, drawing] : rects;
  return (
    <Modal visible animationType="slide" onRequestClose={onCancel}>
      <View style={{ flex: 1, backgroundColor: colors.bg, padding: 16, paddingTop: 56, gap: 12 }}>
        <Text variant="title">Kimlik bilgilerini karartın</Text>
        <Text variant="bodySmall" color="inkMuted">
          Ad, soyad, TC, adres, telefon ve dosya numarasının üzerine parmağınızla kutu çizin. Sunucuya yalnızca karartılmış hali gider.
        </Text>
        <View style={{ flex: 1, justifyContent: 'center' }} onLayout={(e) => setBox(e.nativeEvent.layout)}>
          {box && (
            <View
              ref={shot}
              collapsable={false}
              {...pan.panHandlers}
              style={{ width: Math.min(box.width, box.height * ratio), aspectRatio: ratio, alignSelf: 'center' }}
            >
              <Image source={{ uri }} style={{ width: '100%', height: '100%' }} />
              {all.map((r, i) => (
                <View key={i} pointerEvents="none" style={{ position: 'absolute', left: r.x, top: r.y, width: r.w, height: r.h, backgroundColor: '#000' }} />
              ))}
            </View>
          )}
        </View>
        <View style={{ flexDirection: 'row', gap: 10 }}>
          <View style={{ flex: 1 }}>
            <Button title="Geri al" variant="ghost" disabled={rects.length === 0 || saving} onPress={() => setRects((old) => old.slice(0, -1))} />
          </View>
          <View style={{ flex: 1 }}>
            <Button title="Vazgeç" variant="ghost" disabled={saving} onPress={onCancel} />
          </View>
        </View>
        <Button title={`Tamam, gönder${rects.length ? ` (${rects.length} alan)` : ''}`} loading={saving} onPress={finish} />
      </View>
    </Modal>
  );
}
