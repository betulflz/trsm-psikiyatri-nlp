import { useEffect, useState } from 'react';
import { useReducedMotion } from 'react-native-reanimated';

/** Sayıyı 0'dan hedefe ease-out ile sayar; "hareketi azalt" açıksa doğrudan hedef. */
export function useCountUp(target: number, durationMs = 1100): number {
  const reduced = useReducedMotion();
  const [value, setValue] = useState(reduced ? target : 0);
  useEffect(() => {
    if (reduced) {
      setValue(target);
      return;
    }
    let frame = 0;
    const start = Date.now();
    const tick = () => {
      const k = Math.min(1, (Date.now() - start) / durationMs);
      setValue(Math.round(target * (1 - Math.pow(1 - k, 3))));
      if (k < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, durationMs, reduced]);
  return value;
}
