import { palettes, resolveTheme } from '../tokens';

describe('resolveTheme', () => {
  it('sistem tercihinde cihaz moduna uyar, bilinmiyorsa açık', () => {
    expect(resolveTheme('sistem', 'dark')).toBe('dark');
    expect(resolveTheme('sistem', 'light')).toBe('light');
    expect(resolveTheme('sistem', null)).toBe('light');
    expect(resolveTheme('sistem', undefined)).toBe('light');
  });

  it('açık ve koyu tercih cihazı geçersiz kılar', () => {
    expect(resolveTheme('acik', 'dark')).toBe('light');
    expect(resolveTheme('koyu', 'light')).toBe('dark');
  });
});

describe('palettes', () => {
  it('iki temada da aynı token anahtarları var', () => {
    expect(Object.keys(palettes.dark).sort()).toEqual(Object.keys(palettes.light).sort());
  });

  it('spec §4.2 değerleri', () => {
    expect(palettes.light.primary).toBe('#1E8C6E');
    expect(palettes.dark.primary).toBe('#34B48F');
    expect(palettes.light.deep).toBe('#15181D');
    expect(palettes.light.accent).toBe('#9ED9C3');
    expect(palettes.light.highlight).toBe('#F3E08A');
  });
});
