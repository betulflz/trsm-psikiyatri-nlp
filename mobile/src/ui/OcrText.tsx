import { useEffect, useMemo, useState } from 'react';
import { useReducedMotion } from 'react-native-reanimated';
import { splitHighlights, type Highlight } from '@/lib/ocrSegments';
import { useTheme } from '@/theme/ThemeProvider';
import { Text } from './Text';

type Props = { text: string; highlights: Highlight[]; numberOfLines?: number; animate?: boolean };

/**
 * OCR metni (mono). İlaçlar fosforlu zeminle, belirtiler ana renkli altçizgiyle.
 * animate=true iken vurgular sırayla (140 ms arayla) belirir; RN satır içi metinde
 * genişlik animasyonu desteklenmediği için "sweep" sıralı görünür olmayla verilir.
 * Not: Android'de altçizgi rengi metin rengini kullanır (textDecorationColor yalnızca iOS).
 */
export function OcrText({ text, highlights, numberOfLines, animate = true }: Props) {
  const { colors } = useTheme();
  const reduced = useReducedMotion();
  const segments = useMemo(() => splitHighlights(text, highlights), [text, highlights]);
  const marked = segments.filter((s) => s.tur !== null).length;
  const instant = !animate || reduced;
  const [revealed, setRevealed] = useState(instant ? marked : 0);

  useEffect(() => {
    if (instant) {
      setRevealed(marked);
      return;
    }
    setRevealed(0);
    const timers = Array.from({ length: marked }, (_, i) => setTimeout(() => setRevealed(i + 1), 250 + i * 140));
    return () => timers.forEach(clearTimeout);
  }, [instant, marked, text]);

  let order = 0;
  return (
    <Text variant="mono" numberOfLines={numberOfLines}>
      {segments.map((segment, i) => {
        if (segment.tur === null) return segment.text;
        const visible = order++ < revealed;
        if (segment.tur === 'ilac') {
          return (
            <Text
              key={i}
              variant="mono"
              style={{ backgroundColor: visible ? colors.highlight : 'transparent', color: visible ? colors.highlightInk : colors.ink }}
            >
              {segment.text}
            </Text>
          );
        }
        return (
          <Text key={i} variant="mono" style={visible ? { textDecorationLine: 'underline', textDecorationColor: colors.primary } : undefined}>
            {segment.text}
          </Text>
        );
      })}
    </Text>
  );
}
