import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useColorScheme } from 'react-native';
import { prefs } from '@/storage/prefs';
import { palettes, resolveTheme, type Colors, type ThemeName, type ThemePreference } from './tokens';

type ThemeContextValue = {
  colors: Colors;
  name: ThemeName;
  preference: ThemePreference;
  setPreference: (value: ThemePreference) => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const system = useColorScheme();
  const [preference, setPreferenceState] = useState<ThemePreference>('sistem');

  useEffect(() => {
    prefs.getThemePreference().then(setPreferenceState).catch(() => {});
  }, []);

  const value = useMemo<ThemeContextValue>(() => {
    const name = resolveTheme(preference, system);
    return {
      colors: palettes[name],
      name,
      preference,
      setPreference: (next) => {
        setPreferenceState(next);
        prefs.setThemePreference(next).catch(() => {});
      },
    };
  }, [preference, system]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const value = useContext(ThemeContext);
  if (!value) throw new Error('useTheme ThemeProvider içinde kullanılmalı');
  return value;
}
