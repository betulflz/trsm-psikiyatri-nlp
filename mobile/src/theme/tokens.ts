export type ThemeName = 'light' | 'dark';
export type ThemePreference = 'sistem' | 'acik' | 'koyu';

const light = {
  bg: '#F3F4F4',
  surface: '#FFFFFF',
  surfaceRaised: '#FFFFFF',
  ink: '#111418',
  inkMuted: '#5F656D',
  line: '#E4E6E9',
  deep: '#15181D',
  onDeep: '#FFFFFF',
  primary: '#1E8C6E',
  primarySoft: '#DCEFE7',
  accent: '#9ED9C3',
  onAccent: '#15181D',
  accentSoft: '#E2F4EC',
  highlight: '#F3E08A',
  highlightInk: '#111418',
  danger: '#E5484D',
  dangerSoft: '#FDECEC',
};

export type Colors = Record<keyof typeof light, string>;

const dark: Colors = {
  bg: '#0E1013',
  surface: '#171A1F',
  surfaceRaised: '#1E2228',
  ink: '#ECEFF1',
  inkMuted: '#9AA1A9',
  line: '#262A31',
  deep: '#1B1F25',
  onDeep: '#ECEFF1',
  primary: '#34B48F',
  primarySoft: '#12302A',
  accent: '#9ED9C3',
  onAccent: '#0E1013',
  accentSoft: '#1A3A30',
  highlight: '#E6CF6A',
  highlightInk: '#111418',
  danger: '#FF6369',
  dangerSoft: '#3A1A1C',
};

export const palettes: Record<ThemeName, Colors> = { light, dark };

export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 20, xxl: 24, xxxl: 32 } as const;
export const radius = { chip: 8, input: 12, card: 18, hero: 22, tab: 22 } as const;

export const fontFamily = {
  400: 'Geist_400Regular',
  500: 'Geist_500Medium',
  600: 'Geist_600SemiBold',
  700: 'Geist_700Bold',
  800: 'Geist_800ExtraBold',
  mono: 'GeistMono_400Regular',
  monoMedium: 'GeistMono_500Medium',
} as const;

export type FontWeight = 400 | 500 | 600 | 700 | 800;

export const typeScale = {
  display: { fontSize: 44, lineHeight: 48, weight: 800 as FontWeight, letterSpacing: -1.5 },
  title: { fontSize: 24, lineHeight: 30, weight: 800 as FontWeight, letterSpacing: -0.5 },
  heading: { fontSize: 18, lineHeight: 24, weight: 700 as FontWeight, letterSpacing: -0.3 },
  body: { fontSize: 15, lineHeight: 21, weight: 500 as FontWeight, letterSpacing: 0 },
  bodySmall: { fontSize: 13, lineHeight: 18, weight: 500 as FontWeight, letterSpacing: 0 },
  label: { fontSize: 11, lineHeight: 14, weight: 600 as FontWeight, letterSpacing: 0.2 },
  mono: { fontSize: 12, lineHeight: 19, weight: 400 as FontWeight, letterSpacing: 0 },
} as const;

export type TypeVariant = keyof typeof typeScale;

export function resolveTheme(
  preference: ThemePreference,
  system: 'light' | 'dark' | 'unspecified' | null | undefined,
): ThemeName {
  if (preference === 'acik') return 'light';
  if (preference === 'koyu') return 'dark';
  return system === 'dark' ? 'dark' : 'light';
}
