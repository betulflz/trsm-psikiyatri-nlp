/** "şema://ana-makine[:port]" biçimindeki sunucu kaynağı; okunamıyorsa null. */
function origin(url: string): string | null {
  const match = /^([a-z][a-z0-9+.-]*):\/\/([^/?#\s]+)/i.exec(url.trim());
  return match ? `${match[1].toLowerCase()}://${match[2].toLowerCase()}` : null;
}

/** Oturum token'ının yalnızca aynı sunucuya gitmesi için: iki adres aynı kaynağa mı çıkıyor? */
export function sameServer(a: string, b: string): boolean {
  const left = origin(a);
  const right = origin(b);
  return left !== null && left === right;
}

/** Kullanıcının yazdığı adresi "şema://ana-makine[:port]" biçimine getirir; geçersizse null. */
export function normalizeServerUrl(input: string): string | null {
  const trimmed = input.trim();
  if (!trimmed || /\s/.test(trimmed)) return null;
  const withScheme = /^[a-z][a-z0-9+.-]*:\/\//i.test(trimmed) ? trimmed : `http://${trimmed}`;
  const match = /^(https?):\/\/([^/?#]+)/i.exec(withScheme);
  if (!match || !/^[^:]+(:\d{1,5})?$/.test(match[2])) return null;
  return `${match[1].toLowerCase()}://${match[2].toLowerCase()}`;
}
